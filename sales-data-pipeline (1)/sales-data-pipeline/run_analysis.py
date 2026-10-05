"""Run sql/analysis_queries.sql against the warehouse and save each result as CSV."""
import sqlite3
from pathlib import Path
import pandas as pd

queries = [q.strip() for q in Path("sql/analysis_queries.sql").read_text().split(";") if "SELECT" in q or "WITH" in q]
names = ["revenue_by_quarter", "revenue_by_category", "top10_customers", "mom_growth", "discount_by_segment"]
out = Path("powerbi_exports"); out.mkdir(exist_ok=True)
with sqlite3.connect("warehouse/sales_dw.db") as con:
    for name, q in zip(names, queries):
        df = pd.read_sql_query(q, con)
        df.to_csv(out / f"analysis_{name}.csv", index=False)
        print(f"\n== {name} ==\n{df.head(10).to_string(index=False)}")
