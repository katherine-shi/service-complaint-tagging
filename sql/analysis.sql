-- name: volume_by_category
SELECT t.category,
       COUNT(*)                                             AS complaints,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)   AS share_pct,
       ROUND(100.0 * AVG(t.severity = 'Safety-critical'), 1) AS safety_critical_pct,
       ROUND(100.0 * AVG(t.service_visit), 1)               AS service_visit_pct
FROM tags t
GROUP BY t.category
ORDER BY complaints DESC;

-- name: category_by_model_year
SELECT c.model, c.model_year, t.category, COUNT(*) AS complaints
FROM tags t JOIN complaints c USING (odi_number)
GROUP BY c.model, c.model_year, t.category
ORDER BY c.model, c.model_year, complaints DESC;

-- name: failure_type_mix
SELECT t.failure_type,
       COUNT(*)                                           AS complaints,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM tags t
GROUP BY t.failure_type
ORDER BY complaints DESC;

-- name: out_of_pocket_cost
SELECT t.category,
       COUNT(t.out_of_pocket_usd)          AS complaints_with_cost,
       ROUND(AVG(t.out_of_pocket_usd), 0)  AS avg_usd,
       ROUND(MAX(t.out_of_pocket_usd), 0)  AS max_usd
FROM tags t
WHERE t.out_of_pocket_usd IS NOT NULL
GROUP BY t.category
HAVING COUNT(t.out_of_pocket_usd) >= 3
ORDER BY avg_usd DESC;

-- name: monthly_trend
SELECT SUBSTR(c.date_filed, 1, 7) AS month, COUNT(*) AS complaints
FROM tags t JOIN complaints c USING (odi_number)
WHERE c.date_filed IS NOT NULL
GROUP BY month
ORDER BY month;
