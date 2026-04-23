-- Omni Data Hub — Star Schema
-- Runs once on first postgres boot via docker-entrypoint-initdb.d

-- ── Dimension Tables ──

CREATE TABLE IF NOT EXISTS dim_product (
    sku_code       VARCHAR(20) PRIMARaY KEY,
    ean_barcode    BIGINT,
    product_name   TEXT,
    brand          VARCHAR(50),
    category       VARCHAR(50),
    sub_category   VARCHAR(50),
    size           VARCHAR(20),
    color          VARCHAR(30),
    fabric         VARCHAR(30),
    mrp            NUMERIC(10,2),
    hsn_code       INT,
    gst_pct        INT
);

CREATE TABLE IF NOT EXISTS dim_store (
    store_code  VARCHAR(20) PRIMARY KEY,
    store_name  TEXT,
    city        VARCHAR(50),
    state       VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS dim_hub (
    hub_id     VARCHAR(20) PRIMARY KEY,
    hub_name   TEXT,
    pincode    VARCHAR(10),
    latitude   NUMERIC(9,6),
    longitude  NUMERIC(9,6)
);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id   VARCHAR(20) PRIMARY KEY,
    customer_name TEXT,
    phone         VARCHAR(30),
    email         VARCHAR(100),
    city          VARCHAR(50),
    state         VARCHAR(10),
    loyalty_tier  VARCHAR(20),
    join_date     DATE
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key       DATE PRIMARY KEY,
    year           INT,
    month          INT,
    day            INT,
    quarter        INT,
    day_of_week    INT,
    month_name     VARCHAR(10),
    is_weekend     BOOLEAN
);

-- ── Fact Table ──

CREATE TABLE IF NOT EXISTS sales_fact (
    id                BIGSERIAL PRIMARY KEY,
    franchise_id      CHAR(1) NOT NULL,          -- A or B
    transaction_date  TIMESTAMP NOT NULL,
    sku_code          VARCHAR(20) REFERENCES dim_product(sku_code),
    store_or_hub_id   VARCHAR(20),               -- store_code (A) or hub_id (B)
    quantity          INT,
    selling_price     NUMERIC(10,2),
    customer_id       VARCHAR(20),               -- NULL for Franchise B / walk-ins
    status            VARCHAR(20),               -- SALE/RETURN (A) or DELIVERED/RETURNED/CANCELLED (B)
    source_file       TEXT,
    loaded_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sf_franchise ON sales_fact(franchise_id);
CREATE INDEX IF NOT EXISTS idx_sf_date ON sales_fact(transaction_date);
CREATE INDEX IF NOT EXISTS idx_sf_sku ON sales_fact(sku_code);

-- ── Error Log (quarantined rows) ──

CREATE TABLE IF NOT EXISTS error_log (
    id              BIGSERIAL PRIMARY KEY,
    franchise_id    CHAR(1) NOT NULL,
    rule_code       VARCHAR(10) NOT NULL,        -- A1, A2, B1, B4, etc.
    raw_row         JSONB,
    source_file     TEXT,
    detected_at     TIMESTAMP DEFAULT NOW()
);
