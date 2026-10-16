import requests

API_URL = "https://world.openfoodfacts.net/api/v2/search"

params = {
    "categories_tags_en": "breakfast-cereals",
    "page": 1,
    "page_size": 5,
    "fields": (
        "code,product_name,brands,"
        "categories_tags_en,quantity"
    ),
}

headers = {
    "User-Agent": (
        "ProductCatalogQualityAudit/1.0 "
        "(learning project)"
    )
}


def main():
    print("Testing category-based product search...")

    try:
        response = requests.get(
            API_URL,
            params=params,
            headers=headers,
            auth=("off", "off"),
            timeout=30,
        )

        print("HTTP status:", response.status_code)

        if response.status_code != 200:
            print("Response:", response.text[:500])
            return

        data = response.json()
        products = data.get("products", [])

        print("Matching products:", data.get("count"))
        print("Products returned:", len(products))

        for product in products:
            print("-" * 35)
            print("Barcode:", product.get("code"))
            print("Name:", product.get("product_name"))
            print("Brand:", product.get("brands"))

        print("\nCategory search successful!")

    except requests.RequestException as error:
        print("Request failed:", error)


if __name__ == "__main__":
    main()