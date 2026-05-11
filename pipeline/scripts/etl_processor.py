"""
ETL Processor — Omni Data Hub (GCS Cloud Edition)
Updated: May 2026
Matched to Bucket: omni-data-hub-landing-zone-ranu
"""

import os
import io
import json
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from airflow.providers.google.cloud.hooks.gcs import GCSHook

# ── Config ──────────────────────────────────────

# Ensure these match your docker-compose.yml environment variables
DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}"
    f"@{os.getenv('POSTGRES_HOST', 'database')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'omni_dw')}"
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

    new = df[~df[key].isin(existing[key])].drop_duplicates(subset=[key])
    
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
    # Path updated to common master data location
    content = hook.download(bucket_name=bucket_name, object_name="master_company/product_master.csv")
    df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    cols = ["sku_code", "product_name", "brand", "category", "mrp"]
    # Only keep columns that exist in your schema
    upsert_df(df[cols], "dim_product", "sku_code", engine)

def load_dim_customer_gcs(engine, bucket_name):
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    content = hook.download(bucket_name=bucket_name, object_name="master_company/customer_master.csv")
    df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    upsert_df(df, "dim_customer", "customer_id", engine)

# ── Unified GCS Franchise Processor ──────────────

def process_gcs_file(engine, bucket_name, object_name, franchise_id):
    """
    Core Logic: Streams file from GCS, handles franchise-specific mappings,
    and loads to the star-schema sales_fact table.
    """
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    fname = os.path.basename(object_name)
    
    content = hook.download(bucket_name=bucket_name, object_name=object_name)
    
    # Auto-detect separator for .psv vs .csv
    sep = "|" if object_name.lower().endswith('.psv') else ","
    df = pd.read_csv(io.BytesIO(content), sep=sep, encoding="utf-8-sig")
    initial_count = len(df)

    if franchise_id == "franchise-1":
        # Franchise 1: Uses unit_price and transaction_timestamp
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors='coerce')
        df["quantity"] = pd.to_numeric(df["quantity"], errors='coerce')
        df["transaction_timestamp"] = pd.to_datetime(df["transaction_timestamp"], errors='coerce')
        
        # Validation
        df = quarantine(df, df["unit_price"].isna() | (df["unit_price"] <= 0), "F1_VAL", franchise_id, fname, engine)
        
        fact = pd.DataFrame({
            "franchise_id": franchise_id,
            "transaction_date": df["transaction_timestamp"],
            "sku_code": df["sku_code"],
            "store_or_hub_id": df["store_code"],
            "quantity": df["quantity"],
            "selling_price": df["unit_price"],
            "customer_id": df.get("customer_id"),
            "status": df.get("transaction_type", "COMPLETED"),
            "source_file": fname
        })

    elif franchise_id == "franchise-2":
        # Franchise 2: Matches the PSV files we saw (mrp_price, units_sold)
        df["mrp_price"] = pd.to_numeric(df["mrp_price"], errors='coerce')
        df["units_sold"] = pd.to_numeric(df["units_sold"], errors='coerce')
        df["delivery_timestamp"] = pd.to_datetime(df["delivery_timestamp"], errors='coerce')
        
        # Calculate Net Price
        discount = pd.to_numeric(df.get("discount_applied", 0), errors='coerce').fillna(0)
        df["net_price"] = df["mrp_price"] - discount

        fact = pd.DataFrame({
            "franchise_id": franchise_id,
            "transaction_date": df["delivery_timestamp"],
            "sku_code": df["sku_code"],
            "store_or_hub_id": df["hub_id"],
            "quantity": df["units_sold"],
            "selling_price": df["net_price"],
            "customer_id": df.get("customer_id"),
            "status": df.get("status", "DELIVERED"),
            "source_file": fname
        })

    # 5. Final Load to Star Schema
    if not fact.empty:
        fact.to_sql("sales_fact", engine, if_exists="append", index=False, method="multi")
        log.info(f"  {fname}: {len(fact)} loaded / {initial_count - len(fact)} quarantined")
    else:
        log.warning(f"  {fname}: No valid records to load.")