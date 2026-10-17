import json
import math
from collections import Counter
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. PROJECT SETTINGS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PLACEHOLDERS = {
    "n/a",
    "na",
    "not available",
    "unknown",
    "none",
    "null",
    "-",
}

# Nutrient API field: (output column, plausible maximum per 100 g)
NUTRIENTS = {
    "energy-kj_100g": ("energy_kj_100g", 4000),
    "energy-kcal_100g": ("energy_kcal_100g", 1000),
    "proteins_100g": ("proteins_100g", 100),
    "fat_100g": ("fat_100g", 100),
    "carbohydrates_100g": ("carbohydrates_100g", 100),
    "sugars_100g": ("sugars_100g", 100),
    "salt_100g": ("salt_100g", 100),
}

ISSUE_COLUMNS = [
    "source_category",
    "source_file",
    "barcode",
    "product_name",
    "field",
    "issue_type",
    "severity",
    "observed_value",
    "recommended_action",
]


# --------------------------------------------------
# 2. NORMALIZATION HELPERS
# --------------------------------------------------

def clean_text(value):
    """Trim whitespace and normalize obvious placeholders."""

    if value is None:
        return None

    if isinstance(value, (list, tuple)):
        value = "; ".join(
            str(item).strip()
            for item in value
            if str(item).strip()
        )
    elif not isinstance(value, str):
        value = str(value)

    value = " ".join(value.split())

    if not value or value.casefold() in PLACEHOLDERS:
        return None

    return value


def is_placeholder(value):
    """Identify explicit placeholder strings."""

    return (
        isinstance(value, str)
        and value.strip().casefold() in PLACEHOLDERS
    )


def parse_number(value):
    """Convert a numeric value safely; return None if invalid."""

    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, str) and not value.strip():
        return None

    try:
        number = float(value)
    except (ValueError, TypeError):
        return None

    if not math.isfinite(number):
        return None

    return number


def add_issue(
    issues,
    source_category,
    source_file,
    barcode,
    product_name,
    field,
    issue_type,
    severity,
    observed_value,
    recommended_action,
):
    """Add one finding to the issue report."""

    issues.append({
        "source_category": source_category,
        "source_file": source_file,
        "barcode": barcode,
        "product_name": product_name,
        "field": field,
        "issue_type": issue_type,
        "severity": severity,
        "observed_value": str(observed_value)[:300],
        "recommended_action": recommended_action,
    })


# --------------------------------------------------
# 3. READ AND NORMALIZE THE RAW RECORDS
# --------------------------------------------------

def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(RAW_DIR.glob("*_page_*.json"))

    if not raw_files:
        raise FileNotFoundError(
            f"No category JSON files found in {RAW_DIR}"
        )

    records = []
    issues = []

    for file_path in raw_files:
        source_category = file_path.name.rsplit("_page_", 1)[0]

        with file_path.open("r", encoding="utf-8") as file:
            response_data = json.load(file)

        for product in response_data.get("products", []):
            barcode = str(product.get("code") or "").strip()
            name = clean_text(product.get("product_name"))
            brand = clean_text(product.get("brands"))
            quantity = clean_text(product.get("quantity"))
            ingredients = clean_text(
                product.get("ingredients_text")
            )
            allergens = clean_text(product.get("allergens"))
            labels = clean_text(product.get("labels_tags"))
            categories = clean_text(product.get("categories_tags"))
            main_category = clean_text(
                product.get("main_category")
            )

            # Preserve cleaned fields in a separate dataset.
            record = {
                "barcode": barcode,
                "source_category": source_category,
                "source_file": file_path.name,
                "product_name": name,
                "brands": brand,
                "quantity": quantity,
                "ingredients_text": ingredients,
                "allergens": allergens,
                "labels_tags": labels,
                "categories_tags": categories,
                "main_category": main_category,
            }

            # Check important text fields.
            text_fields = [
                (
                    "product_name",
                    product.get("product_name"),
                    name,
                    "High",
                ),
                ("brands", product.get("brands"), brand, "Medium"),
                (
                    "quantity",
                    product.get("quantity"),
                    quantity,
                    "Low",
                ),
                (
                    "ingredients_text",
                    product.get("ingredients_text"),
                    ingredients,
                    "Medium",
                ),
                (
                    "allergens",
                    product.get("allergens"),
                    allergens,
                    "Medium",
                ),
                (
                    "categories_tags",
                    product.get("categories_tags"),
                    categories,
                    "Medium",
                ),
            ]

            for field, raw_value, cleaned_value, severity in text_fields:
                if is_placeholder(raw_value):
                    add_issue(
                        issues,
                        source_category,
                        file_path.name,
                        barcode,
                        name,
                        field,
                        "placeholder_value",
                        severity,
                        raw_value,
                        "Verify the information or retain it as missing.",
                    )

                elif cleaned_value is None:
                    if field == "allergens":
                        action = (
                            "Check the source or product packaging. "
                            "A blank field does not mean allergen-free."
                        )
                    else:
                        action = (
                            "Check the source and supply the information "
                            "if it can be verified."
                        )

                    add_issue(
                        issues,
                        source_category,
                        file_path.name,
                        barcode,
                        name,
                        field,
                        "missing_value",
                        severity,
                        raw_value,
                        action,
                    )

            # Flatten and validate nutrition fields.
            nutrition = product.get("nutriments") or {}
            parsed_nutrients = {}
            raw_nutrients = {}

            for api_key, (output_column, maximum) in NUTRIENTS.items():
                raw_value = nutrition.get(api_key)
                raw_nutrients[api_key] = raw_value
                number = parse_number(raw_value)
                parsed_nutrients[api_key] = number

                record[output_column] = number

                is_empty = (
                    raw_value is None
                    or (
                        isinstance(raw_value, str)
                        and not raw_value.strip()
                    )
                )

                if is_empty:
                    continue

                if number is None:
                    add_issue(
                        issues,
                        source_category,
                        file_path.name,
                        barcode,
                        name,
                        api_key,
                        "non_numeric_nutrition_value",
                        "High",
                        raw_value,
                        "Verify the original value before using it.",
                    )

                elif number < 0 or number > maximum:
                    add_issue(
                        issues,
                        source_category,
                        file_path.name,
                        barcode,
                        name,
                        api_key,
                        "nutrition_value_out_of_range",
                        "High",
                        raw_value,
                        (
                            f"Check the value and unit. Values outside "
                            f"0–{maximum} per 100 g need investigation."
                        ),
                    )

            # Core nutrition completeness: energy, protein, fat,
            # and carbohydrates.
            energy_present = any(
                raw_nutrients[key] is not None
                and str(raw_nutrients[key]).strip() != ""
                for key in (
                    "energy-kj_100g",
                    "energy-kcal_100g",
                )
            )

            if not energy_present:
                add_issue(
                    issues,
                    source_category,
                    file_path.name,
                    barcode,
                    name,
                    "energy",
                    "missing_nutrition_value",
                    "Medium",
                    "",
                    "Check whether energy information is available.",
                )

            for key in (
                "proteins_100g",
                "fat_100g",
                "carbohydrates_100g",
            ):
                raw_value = raw_nutrients[key]

                if (
                    raw_value is None
                    or (
                        isinstance(raw_value, str)
                        and not raw_value.strip()
                    )
                ):
                    add_issue(
                        issues,
                        source_category,
                        file_path.name,
                        barcode,
                        name,
                        key,
                        "missing_nutrition_value",
                        "Medium",
                        "",
                        "Check the source for the missing nutrition value.",
                    )
            
             
            # Check whether reported kcal and kJ values agree.
            kcal = parsed_nutrients["energy-kcal_100g"]
            kj = parsed_nutrients["energy-kj_100g"]

            if (
                kcal is not None
                and kj is not None
                and kcal > 0
                and kj > 0
            ):
                expected_kcal = kj / 4.184

                absolute_difference = abs(kcal - expected_kcal)
                relative_difference = (
                    absolute_difference / expected_kcal
                )

                # Flag substantial disagreements, not negligible differences.
                if relative_difference > 0.20 and absolute_difference > 5:
                    add_issue(
                        issues,
                        source_category,
                        file_path.name,
                        barcode,
                        name,
                        "energy-kcal_100g",
                        "energy_unit_inconsistency",
                        "High",
                        (
                            f"Reported kcal={kcal}; reported kJ={kj}; "
                            f"kJ-converted kcal={expected_kcal:.1f}"
                        ),
                        (
                            "Verify both energy values against the original "
                            "nutrition label. Do not overwrite automatically."
                        ),
                    )

                   
            # Sugars should generally not exceed carbohydrates.
            sugars = parsed_nutrients["sugars_100g"]
            carbohydrates = parsed_nutrients["carbohydrates_100g"]

            if (
                sugars is not None
                and carbohydrates is not None
                and sugars > carbohydrates + 1
            ):
                add_issue(
                    issues,
                    source_category,
                    file_path.name,
                    barcode,
                    name,
                    "sugars_100g",
                    "nutrition_consistency_check",
                    "Medium",
                    f"Sugars={sugars}; carbohydrates={carbohydrates}",
                    "Check both values against the product source.",
                )

            records.append(record)

    # --------------------------------------------------
    # 4. IDENTIFY REPEATED BARCODE CANDIDATES
    # --------------------------------------------------

    barcode_groups = {}

    for record in records:
        if record["barcode"]:
            barcode_groups.setdefault(
                record["barcode"], []
            ).append(record)

    repeated_barcodes = {
        barcode: group
        for barcode, group in barcode_groups.items()
        if len(group) > 1
    }

    for barcode, group in repeated_barcodes.items():
        categories = sorted({
            item["source_category"] for item in group
        })
        files = sorted({
            item["source_file"] for item in group
        })

        cross_category = len(categories) > 1

        add_issue(
            issues,
            "; ".join(categories),
            "; ".join(files),
            barcode,
            group[0]["product_name"],
            "barcode",
            (
                "cross_category_overlap"
                if cross_category
                else "repeated_barcode_in_same_category"
            ),
            "Low" if cross_category else "Medium",
            f"{len(group)} records; categories: {', '.join(categories)}",
            (
                "Review category membership. Do not delete automatically."
                if cross_category
                else "Check whether the records are repeated within one category."
            ),
        )

    # Add row-level review indicators.
    issues_by_record = Counter(
        (issue["source_file"], issue["barcode"])
        for issue in issues
        if issue["source_file"] in {r["source_file"] for r in records}
    )

    repeated_codes = set(repeated_barcodes)

    for record in records:
        record["repeated_barcode_in_sample"] = (
            record["barcode"] in repeated_codes
        )
        record["validation_issue_count"] = issues_by_record[
            (record["source_file"], record["barcode"])
        ]
        record["needs_review"] = (
            record["validation_issue_count"] > 0
            or record["repeated_barcode_in_sample"]
        )

    # --------------------------------------------------
    # 5. EXPORT RESULTS
    # --------------------------------------------------

    products_df = pd.DataFrame(records)
    issues_df = pd.DataFrame(issues, columns=ISSUE_COLUMNS)

    products_path = PROCESSED_DIR / "normalized_products.csv"
    issues_path = PROCESSED_DIR / "validation_issues.csv"
    summary_path = PROCESSED_DIR / "validation_summary.csv"

    products_df.to_csv(
        products_path, index=False, encoding="utf-8-sig"
    )
    issues_df.to_csv(
        issues_path, index=False, encoding="utf-8-sig"
    )

    if issues_df.empty:
        summary_df = pd.DataFrame(
            columns=[
                "source_category",
                "issue_type",
                "severity",
                "issue_count",
            ]
        )
    else:
        summary_df = (
            issues_df.groupby(
                ["source_category", "issue_type", "severity"]
            )
            .size()
            .reset_index(name="issue_count")
            .sort_values(
                ["source_category", "issue_count"],
                ascending=[True, False],
            )
        )

    summary_df.to_csv(
        summary_path, index=False, encoding="utf-8-sig"
    )

    print("\nPRODUCT VALIDATION REPORT")
    print("=" * 35)
    print(f"Records processed: {len(products_df)}")
    print(f"Unique barcodes: {products_df['barcode'].nunique()}")
    print(f"Repeated barcode groups: {len(repeated_barcodes)}")
    print(f"Total issue findings: {len(issues_df)}")
    print(
        "Records needing review: "
        f"{products_df['needs_review'].sum()}"
    )

    print("\nMost common findings:")
    if issues_df.empty:
        print("No issues detected by the current rules.")
    else:
        print(
            issues_df["issue_type"]
            .value_counts()
            .head(10)
            .to_string()
        )

    print("\nFiles saved:")
    print(products_path)
    print(issues_path)
    print(summary_path)

    print(
        "\nScope: These rules flag potential issues for review; "
        "they do not prove that every flagged value is incorrect."
    )


if __name__ == "__main__":
    main()