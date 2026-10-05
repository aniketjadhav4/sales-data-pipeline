# Sales Data Pipeline: ETL + Star-Schema Data Warehouse

An end-to-end ETL project in **Python and SQL** that extracts raw sales files, cleans and validates them, rejects bad records with a reason, loads a **star-schema warehouse**, reconciles the load, and exposes the data for **Power BI**.

> **Data note:** The dataset is **synthetic**. `generate_data.py` creates it with a fixed random seed and injects realistic data-quality problems (duplicates, missing keys, invalid dates and quantities, inconsistent text). No real company data is used. All figures below come from running this pipeline on that synthetic data.

## Architecture

```
generate_data.py  ->  data/raw/*.csv   (customers, products, orders)
                           |
                        etl.py
   EXTRACT -> TRANSFORM (clean, standardise, derive) -> VALIDATE (reject with reason)
           -> LOAD (SQLite star schema) -> RECONCILE (row counts, revenue, FK integrity)
                           |
        warehouse/sales_dw.db   +   data/rejected/rejected_orders.csv
        reports/etl_run_summary.json   +   powerbi_exports/*.csv
```

**Star schema:** `fact_sales` joined to `dim_customer`, `dim_product`, `dim_date` (see `sql/schema.sql`).

## Results from the run (seed = 42)

| Metric | Value |
|---|---|
| Raw order rows extracted | 20,300 |
| Exact duplicate rows removed | 252 |
| Rejected: duplicate `order_id` | 48 |
| Rejected: missing customer_id | 200 |
| Rejected: invalid order date | 200 |
| Rejected: invalid quantity (<= 0) | 200 |
| Rejected: orphan product_id | 200 |
| Missing regions set to "Unknown" | 400 |
| Clean rows loaded to `fact_sales` | 19,208 |
| Net revenue loaded | 995,686,886.75 |
| Reconciliation checks passed | 4 of 4 |

Reconciliation checks: (1) source rows = duplicates + rejected + loaded; (2) loaded rows = clean rows; (3) revenue matches between pipeline and warehouse; (4) no orphan foreign keys in the fact table.

## How to run

```bash
pip install -r requirements.txt
python generate_data.py     # create synthetic raw data
python etl.py               # run the pipeline
python run_analysis.py      # run SQL analysis queries, export results
```

Open `warehouse/sales_dw.db` in DB Browser for SQLite, or use `sql/analysis_queries.sql`.

## SQL analysis (`sql/analysis_queries.sql`)

Revenue by quarter, category share, top 10 customers (window function `RANK`), month-over-month growth (CTE + `LAG`), and discount impact by segment.

## Power BI

1. Get Data -> Text/CSV -> load the four files from `powerbi_exports/` (`fact_sales`, `dim_customer`, `dim_product`, `dim_date`).
2. In Model view, create relationships on `date_key`, `customer_key`, `product_key` (one-to-many, dimension to fact).
3. Build visuals: revenue trend, revenue by category, top customers, discount % by segment.

## Design decisions

- Rejected rows are never silently dropped: each is saved to `data/rejected/rejected_orders.csv` with a `reject_reason`.
- Missing region is recoverable, so it is set to "Unknown" rather than rejecting the whole order.
- When an `order_id` appears more than once with different details, the first occurrence is kept.
- The pipeline raises an error if any reconciliation check fails.

## Possible extensions

Incremental loads, unit tests with pytest, scheduling with Airflow or cron, and loading into a cloud database (Azure SQL, Amazon RDS, BigQuery).

## Tech stack

Python (pandas, numpy), SQL (SQLite), Power BI.
