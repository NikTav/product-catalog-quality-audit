-- Project: Product Catalog Quality Audit
-- Purpose: Summarize validation findings by issue type and severity.

SELECT
    issue_type,
    severity,
    COUNT(*) AS finding_count,

    ROUND(
        100.0 * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        1
    ) AS pct_of_all_findings

FROM validation_issues

GROUP BY
    issue_type,
    severity

ORDER BY
    finding_count DESC,
    issue_type;