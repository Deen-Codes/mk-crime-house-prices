-- ============================================================================
-- analysis_queries.sql
-- Ten questions about crime and house prices in Milton Keynes, 2025.
--
-- Run against the SQLite database built by scripts/04_build_database.py:
--     sqlite3 data/mk_analysis.db
--     .mode column
--     .headers on
--     .read sql/analysis_queries.sql
--
-- Tables:
--   prices           one row per property sale (cleaned)
--   crimes           crime counts by outcode x month x category
--   outcode_summary  one row per postcode district (the price/crime join)
--   monthly_trends   city-wide monthly medians and crime totals
-- ============================================================================


-- Q1. Where is most expensive, and how much crime happens there?
-- The core question of the project in one query.
SELECT outcode,
       median_price,
       total_crimes,
       violent_crimes,
       crimes_per_sale
FROM   outcode_summary
ORDER  BY median_price DESC;


-- Q2. Median sale price per district, computed from raw sales.
-- SQLite has no MEDIAN() aggregate, so we take the middle row per group
-- with ROW_NUMBER() — a standard window-function pattern.
WITH ranked AS (
    SELECT outcode,
           price,
           ROW_NUMBER() OVER (PARTITION BY outcode ORDER BY price) AS rn,
           COUNT(*)    OVER (PARTITION BY outcode)                 AS n
    FROM   prices
)
SELECT   outcode,
         AVG(price) AS median_price,          -- averages the 1 or 2 middle rows
         MAX(n)     AS sales
FROM     ranked
WHERE    rn IN ((n + 1) / 2, (n + 2) / 2)     -- handles odd and even counts
GROUP BY outcode
ORDER BY median_price DESC;


-- Q3. What does each property type sell for city-wide?
SELECT   property_type_label,
         COUNT(*)                   AS sales,
         MIN(price)                 AS min_price,
         CAST(AVG(price) AS INT)    AS mean_price,
         MAX(price)                 AS max_price
FROM     prices
GROUP BY property_type_label
ORDER BY mean_price DESC;


-- Q4. Top crime categories across Milton Keynes in 2025.
SELECT   category,
         SUM(crime_count)                                    AS total,
         ROUND(100.0 * SUM(crime_count) /
               (SELECT SUM(crime_count) FROM crimes), 1)     AS pct_of_all
FROM     crimes
GROUP BY category
ORDER BY total DESC
LIMIT 10;


-- Q5. Is city-centre crime a different *kind* of crime?
-- Compare the category mix of MK9 (centre) against everywhere else.
SELECT   category,
         SUM(CASE WHEN outcode =  'MK9' THEN crime_count ELSE 0 END) AS mk9,
         SUM(CASE WHEN outcode <> 'MK9' THEN crime_count ELSE 0 END) AS rest_of_mk
FROM     crimes
GROUP BY category
ORDER BY mk9 DESC
LIMIT 6;


-- Q6. Month-by-month: do prices and crime move together across the year?
SELECT   month,
         sales,
         median_price,
         total_crimes
FROM     monthly_trends
ORDER BY month;


-- Q7. The new-build premium, per district.
-- Compares average new-build price to average existing-stock price where a
-- district has at least 5 of each (avoids nonsense from tiny samples).
SELECT   outcode,
         CAST(AVG(CASE WHEN new_build = 1 THEN price END) AS INT) AS avg_new_build,
         CAST(AVG(CASE WHEN new_build = 0 THEN price END) AS INT) AS avg_existing,
         SUM(new_build = 1)                                        AS new_sales,
         SUM(new_build = 0)                                        AS old_sales
FROM     prices
GROUP BY outcode
HAVING   new_sales >= 5 AND old_sales >= 5
ORDER BY avg_new_build - avg_existing DESC;


-- Q8. Rank districts on price and on safety simultaneously.
-- A buyer's shortlist: high price rank = expensive, high crime rank = safer
-- (rank 1 = fewest crimes). Districts good on both float to the top.
SELECT   outcode,
         median_price,
         total_crimes,
         RANK() OVER (ORDER BY median_price DESC) AS price_rank,
         RANK() OVER (ORDER BY total_crimes ASC)  AS safety_rank
FROM     outcode_summary
ORDER BY price_rank + safety_rank;


-- Q9. Month-over-month change in the city-wide median price.
-- LAG() window function: each month compared with the one before it.
SELECT   month,
         median_price,
         median_price - LAG(median_price) OVER (ORDER BY month) AS change_vs_prev_month
FROM     monthly_trends
ORDER BY month;


-- Q10. "Value districts": cheaper than the city median AND less violent
-- crime than the district average — where the data says to look for value.
SELECT   outcode,
         median_price,
         violent_crimes
FROM     outcode_summary
WHERE    median_price   < (SELECT AVG(median_price)   FROM outcode_summary)
  AND    violent_crimes < (SELECT AVG(violent_crimes) FROM outcode_summary)
ORDER BY median_price;
