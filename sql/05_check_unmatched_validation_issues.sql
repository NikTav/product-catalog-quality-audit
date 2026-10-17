-- Project: Product Catalog Quality Audit
-- Purpose: Find validation findings that do not match a product record.

SELECT
    v.source_category,
    v.barcode,
    v.product_name,
    v.issue_type,
    v.severity,
    v.recommended_action

FROM validation_issues AS v

LEFT JOIN products AS p
    ON v.barcode = p.barcode
    AND v.source_category = p.source_category

WHERE p.barcode IS NULL

ORDER BY
    v.issue_type,
    v.source_category,
    v.barcode;