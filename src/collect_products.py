
import json
import time
from pathlib import Path
from datetime import datetime, timezone

import requests


# --------------------------------------------------
# 1. COLLECTION SETTINGS
# --------------------------------------------------

API_URL = "https://world.openfoodfacts.net/api/v2/search"

CATEGORIES = {
    "breakfast-cereals": 300,
    "beverages": 300,
    "snacks": 300,
}

PAGE_SIZE = 100
REQUEST_DELAY = 7

FIELDS = (
    "code,product_name,brands,quantity,"
    "categories_tags,main_category,"
    "ingredients_text,allergens,labels_tags,"
    "nutriments"
)

HEADERS = {
    "User-Agent": (
        "ProductCatalogQualityAudit/1.0 "
        "(learning project)"
    )
}


# --------------------------------------------------
# 2. COLLECT PRODUCTS FROM ONE CATEGORY
# --------------------------------------------------

def collect_category(session, category, target):
    collected = []
    page = 1

    while len(collected) < target:
        params = {
            "categories_tags_en": category,
            "page": page,
            "page_size": min(PAGE_SIZE, target - len(collected)),
            "fields": FIELDS,
        }

        print(f"  Requesting page {page}...")

        try:
            response = session.get(
                API_URL,
                params=params,
                headers=HEADERS,
                auth=("off", "off"),
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

        except (requests.RequestException, ValueError) as error:
            print(f"  Collection stopped for {category}: {error}")
            break

        products = data.get("products", [])

        if not products:
            print("  No more products returned.")
            break

        # Save the original response before processing it.
        raw_folder = Path(__file__).resolve().parent.parent
        raw_folder = raw_folder / "data" / "raw"
        raw_folder.mkdir(parents=True, exist_ok=True)

        raw_file = raw_folder / f"{category}_page_{page:03}.json"

        with raw_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        collected.extend(products)

        print(f"  Retrieved {len(products)} products.")

        if len(products) < params["page_size"]:
            break

        page += 1
        time.sleep(REQUEST_DELAY)

    return collected


# --------------------------------------------------
# 3. COLLECT ALL CATEGORIES
# --------------------------------------------------

def main():
    print("Starting product catalog collection...")

    session = requests.Session()
    results = {}

    for index, (category, target) in enumerate(CATEGORIES.items()):
        print(f"\nCategory: {category}")
        products = collect_category(session, category, target)

        results[category] = {
            "target": target,
            "retrieved": len(products),
        }

        print(f"  Total retrieved: {len(products)}")

        if index < len(CATEGORIES) - 1:
            time.sleep(REQUEST_DELAY)

    print("\n--- Collection summary ---")

    for category, summary in results.items():
        print(
            f"{category}: {summary['retrieved']} "
            f"of {summary['target']} requested"
        )

    print("\nRaw API responses are saved in data/raw/.")
    print("Collection finished.")


if __name__ == "__main__":
    main()
