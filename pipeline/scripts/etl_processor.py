"""
ETL Processor — Omni Data Hub
Loads landing-zone files → validates → enriches → writes to Postgres.
Compatible with SQLAlchemy 1.4 (Required for Airflow 2.6.0).
"""

import os
import glob
import json
import logging
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ── Config ──────────────────────────────────────

load_dotenv()

DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)

LANDING = os.getenv("LANDING_ZONE_PATH", "./data_generator/storage/landing_zone")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Helpers ─────────────────────────────────────

def get_engine():
    return create_engine(DB_URL, pool_pre_ping=True)

def upsert_df(df: pd.DataFrame, table: str, key: str, engine):
    """SQLAlchemy 1.4 compatible upsert."""
    try:
        # In SQLAlchemy 1.4, pandas can use the engine directly for both
        existing = pd.read_sql(f"SELECT {key} FROM {table}", engine)
    except Exception:
        # If table doesn't exist, treat as empty
        existing = pd.DataFrame(columns=[key])

    new = df[~df[key].isin(existing[key])]
    
    if len(new):
        # engine is accepted here in 1.4 and older pandas
        new.to_sql(table, engine, if_exists="append", index=False, method="multi")
        
    log.info(f"  {table}: {len(new)} new / {len(df)} total")

def quarantine(df: pd.DataFrame, mask: pd.Series, rule: str, franchise: str, source: str, engine):
    """Flag bad rows and write to error_log."""
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

# ── Dimension Loaders ───────────────────────────

def load_dim_product(engine):
    path = os.path.join(LANDING, "master_company", "product_master.csv")
    if not os.path.exists(path):
        log.warning(f"File not found: {path}")
        return
    df = pd.read_csv(path, encoding="utf-8-sig")
    cols = ["sku_code", "ean_barcode", "product_name", "brand", "category",
            "sub_category", "size", "color", "fabric", "mrp", "hsn_code", "gst_pct"]
    upsert_df(df[cols], "dim_product", "sku_code", engine)

# ── Main ────────────────────────────────────────

def run():
    engine = get_engine()
    log.info("Starting ETL Process (SQLAlchemy 1.4 Mode)...")
    
    log.info("Loading dimensions...")
    load_dim_product(engine)
    # Add other loaders here (load_dim_customer, etc.) as needed
    
    log.info("ETL Cycle Complete.")

if __name__ == "__main__":
    run()