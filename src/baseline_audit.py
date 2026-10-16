
import json
from pathlib import Path

import pandas as pd


# 1. Locate project folders
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


# 2. Define presence-only checks
def has_value(value):
    """Return True when a field contains a non-empty value."""
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (list, dict)):
        return len(value) > 0

    return True


def audit_product(product, source_category, source_file):
    """Calculate a baseline completeness score for one record."""

    nutrition = product.get("nutriments") or {}

    # Energy can be reported in kJ or kcal per 100 g.
    has_energy = (
        has_value(nutrition.get("energy-kj_100g"))
        or has_value(nutrition.get("energy-kcal_100g"))
    )

    has_protein = has_value(nutrition.get("proteins_100g"))
    has_fat = has_value(nutrition.get("fat_100g"))
    has_carbohydrates = has_value(
        nutrition.get("carbohydrates_100g")
    )

    # Baseline checks do not yet validate whether values are correct.
    checks = {
        "name_present": has_value(product.get("product_name")),
        "brand_present": has_value(product.get("brands")),
        "ingredients_present": has_value(
            product.get("ingredients_text")
        ),
        "allergen_or_label_info_present": (
            has_value(product.get("allergens"))
            or has_value(product.get("labels_tags"))
        ),
        "core_nutrition_present": all([
            has_energy,
            has_protein,
            has_fat,
            has_carbohydrates,
        ]),
    }

    score = sum(checks.values()) / len(checks) * 100

    missing_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    missing_nutrition = []
    if not has_energy:
        missing_nutrition.append("energy")
    if not has_protein:
        missing_nutrition.append("protein")
    if not has_fat:
        missing_nutrition.append("fat")
    if not has_carbohydrates:
        missing_nutrition.append("carbohydrates")

    return {
        "barcode": str(product.get("code") or ""),
        "source_category": source_category,
        "source_file": source_file,
        "product_name": product.get("product_name"),
        "brands": product.get("brands"),
        "ingredients_text": product.get("ingredients_text"),
        "allergens": product.get("allergens"),
        "labels_tags": product.get("labels_tags"),
        "main_category": product.get("main_category"),
        "categories_tags": product.get("categories_tags"),
        "category_tags_present": has_value(
           product.get("categories_tags")
        ),
        **checks,
        "baseline_completeness_score": round(score, 1),
        "missing_checks": "; ".join(missing_checks),
        "missing_nutrition_fields": "; ".join(missing_nutrition),
        "main_category_present": has_value(
            product.get("main_category")
        ),
    }


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(RAW_DIR.glob("*_page_*.json"))

    if not raw_files:
        raise FileNotFoundError(
            f"No category page JSON files found in {RAW_DIR}"
        )

    audit_records = []

    # 3. Load and audit every raw API record.
    for file_path in raw_files:
        source_category = file_path.name.rsplit("_page_", 1)[0]

        with file_path.open("r", encoding="utf-8") as file:
            response_data = json.load(file)

        for product in response_data.get("products", []):
            audit_records.append(
                audit_product(
                    product,
                    source_category,
                    file_path.name,
                )
            )

    if not audit_records:
        raise ValueError("The JSON files contained no product records.")

    # 4. Save record-level results without changing the raw JSON.
    df = pd.DataFrame(audit_records)

    records_output = (
        PROCESSED_DIR / "baseline_audit_records.csv"
    )
    df.to_csv(records_output, index=False, encoding="utf-8-sig")

    # 5. Summarize completeness by category search.
    check_columns = [
        "name_present",
        "brand_present",
        "ingredients_present",
        "allergen_or_label_info_present",
        "core_nutrition_present",
    ]

    summary = (
        df.groupby("source_category")
        .agg(
            records=("barcode", "size"),
            unique_barcodes=("barcode", "nunique"),
            average_completeness_score=(
                "baseline_completeness_score", "mean"
            ),
            main_category_field_missing_pct=(
                "main_category_present",
                lambda values: (1 - values.mean()) * 100,
            ),
            category_tags_present_pct=(
                "category_tags_present",
                lambda values: values.mean() * 100,
            ),
        )
        .reset_index()
    )

    # Express each check's pass rate as a percentage.
    for column in check_columns:
        pass_rates = (
            df.groupby("source_category")[column].mean() * 100
        )
        summary[f"{column}_pct"] = (
            summary["source_category"].map(pass_rates)
        )

    summary["average_completeness_score"] = (
        summary["average_completeness_score"].round(1)
    )
    summary["main_category_field_missing_pct"] = (
        summary["main_category_field_missing_pct"].round(1)
    )
    summary["category_tags_present_pct"] = (
        summary["category_tags_present_pct"].round(1)
)
    summary_output = (
        PROCESSED_DIR / "baseline_audit_summary.csv"
    )
    summary.to_csv(summary_output, index=False, encoding="utf-8-sig")

    # 6. Print a concise report.
    valid_barcodes = df.loc[
        df["barcode"].str.strip().ne(""), "barcode"
    ]

    print("\nBASELINE COMPLETENESS AUDIT")
    print("=" * 35)
    print(f"Raw category records audited: {len(df)}")
    print(f"Unique barcodes: {valid_barcodes.nunique()}")
    print(
        "Repeated barcode occurrences: "
        f"{len(valid_barcodes) - valid_barcodes.nunique()}"
    )

    print("\nCompleteness by category:")
    print(summary.to_string(index=False))

    print("\nFiles saved:")
    print(records_output)
    print(summary_output)

    print(
        "\nScope: This baseline audit measures information presence only; "
    "it does not verify accuracy or validity."
    )


if __name__ == "__main__":
    main()
