"""
ETL Processor — Omni Data Hub (GCS Cloud Edition)
Streams data from GCS -> Validates -> Enriches -> Writes to Postgres.
Compatible with SQLAlchemy 1.4 and Airflow 2.6.0.
"""

import os
import io
import json
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from airflow.providers.google.cloud.hooks.gcs import GCSHook

# ── Config ──────────────────────────────────────

# Database URL using environment variables for security
DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Helpers ─────────────────────────────────────

def get_engine():
    """Returns a SQLAlchemy engine with connection pooling."""
    return create_engine(DB_URL, pool_pre_ping=True)

def upsert_df(df: pd.DataFrame, table: str, key: str, engine):
    """SQLAlchemy 1.4 compatible upsert to prevent duplicates in dimensions."""
    try:
        existing = pd.read_sql(f"SELECT {key} FROM {table}", engine)
    except Exception:
        existing = pd.DataFrame(columns=[key])

    new = df[~df[key].isin(existing[key])]
    
    if len(new):
        new.to_sql(table, engine, if_exists="append", index=False, method="multi")
        
    log.info(f"  {table}: {len(new)} new records added.")

def quarantine(df: pd.DataFrame, mask: pd.Series, rule: str, franchise: str, source: str, engine):
    """Flag bad rows and write to error_log in the database."""
    bad = df[mask]
    if len(bad):
        errors = pd.DataFrame({
            "franchise_id": franchise,
            "rule_code": rule,
            "raw_row": bad.apply(lambda r: json.dumps(r.to_dict(), default=str), axis=1),
            "source_file": source,
        })
        errors.to_sql("error_log", engine, if_exists="append", index=False, method="multi")
    return df[~mask]

# ── GCS Dimension Loaders ────────────────────────

def load_dim_product_gcs(engine, bucket_name):
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    content = hook.download(bucket_name=bucket_name, object_name="master_company/product_master.csv")
    df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    cols = ["sku_code", "ean_barcode", "product_name", "brand", "category",
            "sub_category", "size", "color", "fabric", "mrp", "hsn_code", "gst_pct"]
    upsert_df(df[cols], "dim_product", "sku_code", engine)

def load_dim_customer_gcs(engine, bucket_name):
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    content = hook.download(bucket_name=bucket_name, object_name="master_company/customer_master.csv")
    df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    upsert_df(df, "dim_customer", "customer_id", engine)

# ── Unified GCS Franchise Processor ──────────────

def process_gcs_file(engine, bucket_name, object_name, franchise_id):
    """
    Core Logic: Streams a file from GCS, cleans data types, 
    applies business rules, and loads to the sales_fact table.
    """
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    fname = os.path.basename(object_name)
    
    # 1. Download to memory buffer
    content = hook.download(bucket_name=bucket_name, object_name=object_name)
    
    # 2. Load into Pandas (Handle CSV or PSV based on extension)
    sep = "|" if object_name.endswith('.psv') else ","
    df = pd.read_csv(io.BytesIO(content), sep=sep, encoding="utf-8-sig")
    initial_count = len(df)

    # 3. Numeric & Date Conversion
    if franchise_id == "A":
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors='coerce')
        df["quantity"] = pd.to_numeric(df["quantity"], errors='coerce')
        df["transaction_timestamp"] = pd.to_datetime(df["transaction_timestamp"], errors='coerce')
    else:
        df["mrp_price"] = pd.to_numeric(df["mrp_price"], errors='coerce')
        df["units_sold"] = pd.to_numeric(df["units_sold"], errors='coerce')
        df["delivery_timestamp"] = pd.to_datetime(df["delivery_timestamp"], errors='coerce')

    # 4. Quarantine Logic (Example for Franchise A)
    if franchise_id == "A":
        df = quarantine(df, df["unit_price"].isna() | (df["unit_price"] <= 0), "A1", "A", fname, engine)
        df = quarantine(df, df["transaction_timestamp"].isna(), "A0", "A", fname, engine)
        
        fact = pd.DataFrame({
            "franchise_id": "A",
            "transaction_date": df["transaction_timestamp"],
            "sku_code": df["sku_code"],
            "store_or_hub_id": df["store_code"],
            "quantity": df["quantity"],
            "selling_price": df["unit_price"],
            "customer_id": df["customer_id"],
            "status": df["transaction_type"],
            "source_file": fname
        })
    else:
        # Business logic for Franchise B
        df["net_price"] = df["mrp_price"] - pd.to_numeric(df.get("discount_applied", 0), errors='coerce')
        fact = pd.DataFrame({
            "franchise_id": "B",
            "transaction_date": df["delivery_timestamp"],
            "sku_code": df.get("sku_code"), # Assumes mapping was done or barcode is sku
            "store_or_hub_id": df["hub_id"],
            "quantity": df["units_sold"],
            "selling_price": df["net_price"],
            "customer_id": None,
            "status": df["status"],
            "source_file": fname
        })

    # 5. Final Load
    fact.to_sql("sales_fact", engine, if_exists="append", index=False, method="multi")
    log.info(f"  {fname}: {len(fact)} loaded / {initial_count - len(fact)} quarantined")