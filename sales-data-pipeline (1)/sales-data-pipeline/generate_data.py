"""Generate a SYNTHETIC raw sales dataset with realistic data-quality problems.

All data is randomly generated (seeded, so runs are reproducible). It is not real
company data. Dirty records are injected on purpose so the ETL pipeline has
something real to clean, validate and reject.
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
N_CUSTOMERS, N_PRODUCTS, N_ORDERS = 2000, 60, 20000
RAW = Path("data/raw")


def main():
    rng = np.random.default_rng(SEED)
    RAW.mkdir(parents=True, exist_ok=True)

    regions = ["North", "South", "East", "West"]
    segments = ["Consumer", "Corporate", "Small Business"]
    customers = pd.DataFrame({
        "customer_id": np.arange(1, N_CUSTOMERS + 1),
        "customer_name": [f"Customer {i:04d}" for i in range(1, N_CUSTOMERS + 1)],
        "segment": rng.choice(segments, N_CUSTOMERS),
        "region": rng.choice(regions, N_CUSTOMERS),
        "city": rng.choice(["Pune", "Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata", "Hyderabad"], N_CUSTOMERS),
    })

    categories = {"Electronics": (2000, 40000), "Furniture": (1500, 25000), "Stationery": (50, 800), "Apparel": (300, 4000)}
    cat_names = list(categories)
    prod_cat = rng.choice(cat_names, N_PRODUCTS)
    products = pd.DataFrame({
        "product_id": np.arange(1, N_PRODUCTS + 1),
        "product_name": [f"Product {i:03d}" for i in range(1, N_PRODUCTS + 1)],
        "category": prod_cat,
        "unit_price": [round(float(rng.uniform(*categories[c])), 2) for c in prod_cat],
    })

    dates = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 730, N_ORDERS), unit="D")
    pid = rng.integers(1, N_PRODUCTS + 1, N_ORDERS)
    orders = pd.DataFrame({
        "order_id": np.arange(100000, 100000 + N_ORDERS),
        "order_date": dates.strftime("%Y-%m-%d"),
        "customer_id": rng.integers(1, N_CUSTOMERS + 1, N_ORDERS),
        "product_id": pid,
        "quantity": rng.integers(1, 11, N_ORDERS),
        "unit_price": products.set_index("product_id").loc[pid, "unit_price"].values,
        "discount_pct": rng.choice([0, 0, 0, 5, 10, 15], N_ORDERS),
        "region": rng.choice(regions, N_ORDERS),
    })

    # ---- inject data-quality problems ----
    n = len(orders)
    dup = orders.sample(frac=0.015, random_state=1)                       # exact duplicate rows
    orders = pd.concat([orders, dup], ignore_index=True)
    idx = rng.permutation(len(orders))
    k = int(0.01 * n)
    orders.loc[idx[:k], "customer_id"] = np.nan                           # missing customer
    orders.loc[idx[k:2 * k], "product_id"] = 9999                         # orphan product key
    orders.loc[idx[2 * k:3 * k], "quantity"] = rng.choice([0, -1, -3], k) # invalid quantity
    orders.loc[idx[3 * k:4 * k], "order_date"] = "31/02/2024"             # impossible date
    orders.loc[idx[4 * k:6 * k], "region"] = np.nan                       # missing region (recoverable)
    orders.loc[idx[6 * k:8 * k], "region"] = orders.loc[idx[6 * k:8 * k], "region"].str.upper()   # inconsistent case
    orders.loc[idx[8 * k:9 * k], "region"] = " " + orders.loc[idx[8 * k:9 * k], "region"].astype(str) + " "  # stray spaces

    customers.to_csv(RAW / "customers.csv", index=False)
    products.to_csv(RAW / "products.csv", index=False)
    orders.sample(frac=1, random_state=7).to_csv(RAW / "orders.csv", index=False)
    print(f"Generated: customers={len(customers)}, products={len(products)}, order rows={len(orders)}")


if __name__ == "__main__":
    main()
