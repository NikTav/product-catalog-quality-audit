
import requests

API_URL = "https://world.openfoodfacts.org/api/v2/search"

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
            timeout=30,
        )

        print("HTTP status:", response.status_code)
        print("Request URL:", response.url)

        if response.status_code != 200:
            print("Response details:", response.text[:500])
            return

        data = response.json()
        products = data.get("products", [])

        print("Matching products reported:", data.get("count"))
        print("Products returned:", len(products))

        for product in products:
            print("-" * 35)
            print("Barcode:", product.get("code"))
            print("Name:", product.get("product_name"))
            print("Brand:", product.get("brands"))

    except requests.RequestException as error:
        print("Request failed:", error)


if __name__ == "__main__":
    main()
