-- Star schema: one fact table, three dimensions
CREATE TABLE dim_customer (
    customer_key  INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    segment       TEXT,
    region        TEXT,
    city          TEXT
);
CREATE TABLE dim_product (
    product_key   INTEGER PRIMARY KEY,
    product_name  TEXT NOT NULL,
    category      TEXT,
    list_price    REAL
);
CREATE TABLE dim_date (
    date_key    INTEGER PRIMARY KEY,   -- YYYYMMDD
    full_date   TEXT NOT NULL,
    year        INTEGER,
    quarter     INTEGER,
    month       INTEGER,
    month_name  TEXT,
    day_of_week TEXT
);
CREATE TABLE fact_sales (
    order_id        INTEGER PRIMARY KEY,
    date_key        INTEGER NOT NULL REFERENCES dim_date(date_key),
    customer_key    INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    product_key     INTEGER NOT NULL REFERENCES dim_product(product_key),
    sales_region    TEXT,
    quantity        INTEGER,
    unit_price      REAL,
    discount_pct    REAL,
    gross_amount    REAL,
    discount_amount REAL,
    net_revenue     REAL
);
CREATE INDEX idx_fact_date     ON fact_sales(date_key);
CREATE INDEX idx_fact_customer ON fact_sales(customer_key);
CREATE INDEX idx_fact_product  ON fact_sales(product_key);
