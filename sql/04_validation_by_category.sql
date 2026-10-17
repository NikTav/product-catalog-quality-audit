-- Project: Product Catalog Quality Audit
-- Purpose: Compare validation findings across categories.

SELECT
    p.source_category,
    COUNT(DISTINCT p.barcode) AS total_products,

    COUNT(DISTINCT v.barcode) AS products_with_findings,

    ROUND(
        100.0 * COUNT(DISTINCT v.barcode)
        / NULLIF(COUNT(DISTINCT p.barcode), 0),
        1
    ) AS pct_products_with_findings,

    COUNT(v.issue_type) AS total_findings,

    COUNT(v.issue_type) FILTER (
        WHERE v.severity = 'High'
    ) AS high_severity_findings

FROM products AS p

LEFT JOIN validation_issues AS v
    ON p.barcode = v.barcode
    AND p.source_category = v.source_category

GROUP BY p.source_category

ORDER BY
    high_severity_findings DESC,
    total_findings DESC;