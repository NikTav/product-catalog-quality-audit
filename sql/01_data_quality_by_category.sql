
-- Project: Product Catalog Quality Audit
-- Purpose: Measure missing information by source category.

SELECT
    source_category,
    COUNT(*) AS total_records,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE NULLIF(BTRIM(product_name), '') IS NULL
        ) / COUNT(*), 1
    ) AS missing_name_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE NULLIF(BTRIM(brands), '') IS NULL
        ) / COUNT(*), 1
    ) AS missing_brand_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE NULLIF(BTRIM(ingredients_text), '') IS NULL
        ) / COUNT(*), 1
    ) AS missing_ingredients_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE NULLIF(BTRIM(allergens), '') IS NULL
              AND NULLIF(BTRIM(labels_tags), '') IS NULL
        ) / COUNT(*), 1
    ) AS missing_allergen_label_info_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE energy_kj_100g IS NULL
               OR energy_kcal_100g IS NULL
               OR proteins_100g IS NULL
               OR fat_100g IS NULL
               OR carbohydrates_100g IS NULL
        ) / COUNT(*), 1
    ) AS missing_core_nutrition_pct

FROM products
GROUP BY source_category
ORDER BY missing_core_nutrition_pct DESC;
