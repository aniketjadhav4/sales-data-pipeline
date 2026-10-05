-- 1. Revenue by year and quarter
SELECT d.year, d.quarter, COUNT(*) AS orders, ROUND(SUM(f.net_revenue),2) AS net_revenue
FROM fact_sales f JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.quarter ORDER BY d.year, d.quarter;

-- 2. Revenue and share by product category
SELECT p.category,
       ROUND(SUM(f.net_revenue),2) AS net_revenue,
       ROUND(100.0 * SUM(f.net_revenue) / (SELECT SUM(net_revenue) FROM fact_sales), 1) AS revenue_share_pct
FROM fact_sales f JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.category ORDER BY net_revenue DESC;

-- 3. Top 10 customers (window function rank)
SELECT * FROM (
  SELECT c.customer_name, c.segment, ROUND(SUM(f.net_revenue),2) AS net_revenue,
         RANK() OVER (ORDER BY SUM(f.net_revenue) DESC) AS revenue_rank
  FROM fact_sales f JOIN dim_customer c ON f.customer_key = c.customer_key
  GROUP BY c.customer_key
) WHERE revenue_rank <= 10;

-- 4. Month-over-month revenue growth (CTE + LAG)
WITH monthly AS (
  SELECT d.year, d.month, SUM(f.net_revenue) AS rev
  FROM fact_sales f JOIN dim_date d ON f.date_key = d.date_key
  GROUP BY d.year, d.month
)
SELECT year, month, ROUND(rev,2) AS net_revenue,
       ROUND(100.0 * (rev - LAG(rev) OVER (ORDER BY year, month)) / LAG(rev) OVER (ORDER BY year, month), 1) AS mom_growth_pct
FROM monthly ORDER BY year, month;

-- 5. Discount impact by segment
SELECT c.segment, ROUND(SUM(f.gross_amount),2) AS gross, ROUND(SUM(f.discount_amount),2) AS discount,
       ROUND(100.0 * SUM(f.discount_amount) / SUM(f.gross_amount), 2) AS discount_pct_of_gross
FROM fact_sales f JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.segment;
