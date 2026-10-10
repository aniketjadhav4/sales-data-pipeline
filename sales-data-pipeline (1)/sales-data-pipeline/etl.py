"""Extract -> Transform -> Validate -> Load -> Reconcile.

Reads raw CSVs, cleans and validates them, rejects bad rows (with a reason),
loads a star schema into SQLite, reconciles counts and revenue, and writes a
run summary JSON plus CSV exports for Power BI.
"""
import json
import logging
import sqlite3
from pathlib import Path

import pandas as pd

RAW, REJ, WH, REP, EXP = (Path(p) for p in ("data/raw", "data/rejected", "warehouse", "reports", "powerbi_exports"))
DB = WH / "sales_dw.db"
VALID_REGIONS = {"North", "South", "East", "West"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("etl")


# ------------------------------------------------------------------ EXTRACT
def extract():
    customers = pd.read_csv(RAW / "customers.csv")
    products = pd.read_csv(RAW / "products.csv")
    orders = pd.read_csv(RAW / "orders.csv")
    log.info("Extracted: customers=%d products=%d orders=%d", len(customers), len(products), len(orders))
    return customers, products, orders


# ---------------------------------------------------------------- TRANSFORM
def transform(customers, products, orders):
    stats = {"source_order_rows": len(orders)}
    rejected = []

    # 1) exact duplicates
    dup_mask = orders.duplicated(keep="first")
    stats["duplicate_rows_removed"] = int(dup_mask.sum())
    orders = orders[~dup_mask].copy()

    # 2) standardise text
    orders["region"] = orders["region"].astype("string").str.strip().str.title()
    stats["region_standardised_rows"] = int(orders["region"].isin(VALID_REGIONS).sum())
    stats["region_missing_filled_unknown"] = int(orders["region"].isna().sum())
    orders["region"] = orders["region"].fillna("Unknown")

    # 3) parse dates (invalid -> NaT)
    orders["order_date"] = pd.to_datetime(orders["order_date"], format="%Y-%m-%d", errors="coerce")

    
    # 4) validation rules -> reject with reason
    numeric_price = pd.to_numeric(orders["unit_price"], errors="coerce")
    numeric_discount = pd.to_numeric(orders["discount_pct"], errors="coerce")
    numeric_quantity = pd.to_numeric(orders["quantity"], errors="coerce")

    rules = {
        "duplicate_order_id": orders.duplicated(subset="order_id", keep="first"),
        "missing_customer_id": orders["customer_id"].isna(),
        "invalid_order_date": orders["order_date"].isna(),
        "invalid_quantity": numeric_quantity.isna() | (numeric_quantity <= 0),
        "invalid_unit_price": numeric_price.isna() | (numeric_price < 0),
        "invalid_discount_pct": (
            numeric_discount.isna()
            | ~numeric_discount.between(0, 100)
        ),
        "orphan_product_id": ~orders["product_id"].isin(products["product_id"]),
        "orphan_customer_id": (
            orders["customer_id"].notna()
            & ~orders["customer_id"].isin(customers["customer_id"])
        ),
    }

    # Use validated numeric values in later calculations
    orders["quantity"] = numeric_quantity
    orders["unit_price"] = numeric_price
    orders["discount_pct"] = numeric_discount


    # 5) derive measures
    clean["customer_id"] = clean["customer_id"].astype(int)
    clean["gross_amount"] = (clean["quantity"] * clean["unit_price"]).round(2)
    clean["discount_amount"] = (clean["gross_amount"] * clean["discount_pct"] / 100).round(2)
    clean["net_revenue"] = (clean["gross_amount"] - clean["discount_amount"]).round(2)

    stats.update(rows_after_dedup=int(len(orders)), rows_rejected=int(bad.sum()), rows_clean=int(len(clean)))
    log.info("Transform: dedup removed=%d, rejected=%d, clean=%d",
             stats["duplicate_rows_removed"], stats["rows_rejected"], stats["rows_clean"])
    return clean, rejected_df, stats


# --------------------------------------------------------------------- LOAD
def build_dim_date(dates):
    d = pd.DataFrame({"full_date": pd.date_range(dates.min(), dates.max(), freq="D")})
    d["date_key"] = d["full_date"].dt.strftime("%Y%m%d").astype(int)
    d["year"], d["quarter"], d["month"] = d["full_date"].dt.year, d["full_date"].dt.quarter, d["full_date"].dt.month
    d["month_name"], d["day_of_week"] = d["full_date"].dt.month_name(), d["full_date"].dt.day_name()
    d["full_date"] = d["full_date"].dt.strftime("%Y-%m-%d")
    return d[["date_key", "full_date", "year", "quarter", "month", "month_name", "day_of_week"]]


def load(customers, products, clean):
    WH.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    dim_customer = customers.rename(columns={"customer_id": "customer_key"})
    dim_product = products.rename(columns={"product_id": "product_key", "unit_price": "list_price"})
    dim_date = build_dim_date(clean["order_date"])
    fact = pd.DataFrame({
        "order_id": clean["order_id"],
        "date_key": clean["order_date"].dt.strftime("%Y%m%d").astype(int),
        "customer_key": clean["customer_id"],
        "product_key": clean["product_id"].astype(int),
        "sales_region": clean["region"],
        "quantity": clean["quantity"],
        "unit_price": clean["unit_price"],
        "discount_pct": clean["discount_pct"],
        "gross_amount": clean["gross_amount"],
        "discount_amount": clean["discount_amount"],
        "net_revenue": clean["net_revenue"],
    })
    
with sqlite3.connect(DB) as con:
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((Path("sql") / "schema.sql").read_text())

        for name, df in [("dim_customer", dim_customer), ("dim_product", dim_product),
                         ("dim_date", dim_date), ("fact_sales", fact)]:
            df.to_sql(name, con, if_exists="append", index=False)
    log.info("Loaded star schema into %s", DB)
    return {"dim_customer": dim_customer, "dim_product": dim_product, "dim_date": dim_date, "fact_sales": fact}


# ---------------------------------------------------------------- RECONCILE
def reconcile(stats, tables):
    with sqlite3.connect(DB) as con:
        db_rows = con.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
        db_rev = con.execute("SELECT ROUND(SUM(net_revenue),2) FROM fact_sales").fetchone()[0]
        orphans = con.execute("""SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_customer c ON f.customer_key=c.customer_key
            LEFT JOIN dim_product p ON f.product_key=p.product_key
            LEFT JOIN dim_date d ON f.date_key=d.date_key
            WHERE c.customer_key IS NULL OR p.product_key IS NULL OR d.date_key IS NULL""").fetchone()[0]
    src_rev = round(float(tables["fact_sales"]["net_revenue"].sum()), 2)
    checks = {
        "rows_balance (source = dup + rejected + loaded)":
            stats["source_order_rows"] == stats["duplicate_rows_removed"] + stats["rows_rejected"] + db_rows,
        "loaded_rows_match_clean_rows": db_rows == stats["rows_clean"],
        "revenue_matches_between_pipeline_and_warehouse": abs(db_rev - src_rev) < 0.01,
        "no_orphan_foreign_keys_in_fact": orphans == 0,
    }
    for k, v in checks.items():
        log.info("Reconciliation | %-55s %s", k, "PASS" if v else "FAIL")
    stats.update(warehouse_rows=int(db_rows), warehouse_net_revenue=float(db_rev),
                 reconciliation={k: bool(v) for k, v in checks.items()})
    if not all(checks.values()):
        raise RuntimeError("Reconciliation failed - see log")


def export(tables, rejected):
    EXP.mkdir(exist_ok=True)
    REJ.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(EXP / f"{name}.csv", index=False)
    rejected.to_csv(REJ / "rejected_orders.csv", index=False)


def main():
    customers, products, orders = extract()
    clean, rejected, stats = transform(customers, products, orders)
    tables = load(customers, products, clean)
    reconcile(stats, tables)
    export(tables, rejected)
    REP.mkdir(exist_ok=True)
    (REP / "etl_run_summary.json").write_text(json.dumps(stats, indent=2))
    log.info("Done. Summary written to reports/etl_run_summary.json")


if __name__ == "__main__":
    main()
