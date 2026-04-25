"""
ETL Processor — Omni Data Hub
Loads landing-zone files → validates (quarantine) → enriches → writes to Postgres.

Called by the Airflow DAG or run standalone:
    python pipeline/scripts/etl_processor.py
"""

import os
import glob
import json
import logging
from datetime import datetime

import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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
    """Insert-or-skip: only insert rows whose key doesn't already exist."""
    existing = pd.read_sql(f"SELECT {key} FROM {table}", engine)
    new = df[~df[key].isin(existing[key])]
    if len(new):
        new.to_sql(table, engine, if_exists="append", index=False, method="multi")
    log.info(f"  {table}: {len(new)} new / {len(df)} total")


def quarantine(df: pd.DataFrame, mask: pd.Series, rule: str, franchise: str, source: str, engine):
    """Move flagged rows to error_log and return the clean subset."""
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
    df = pd.read_csv(path, encoding="utf-8-sig")
    cols = ["sku_code", "ean_barcode", "product_name", "brand", "category",
            "sub_category", "size", "color", "fabric", "mrp", "hsn_code", "gst_pct"]
    upsert_df(df[cols], "dim_product", "sku_code", engine)


def load_dim_customer(engine):
    path = os.path.join(LANDING, "master_company", "customer_master.csv")
    df = pd.read_csv(path, encoding="utf-8-sig")
    upsert_df(df, "dim_customer", "customer_id", engine)


def load_dim_store(engine):
    path = os.path.join(LANDING, "franchise_a", "storemaster_monthly_refresh.csv")
    df = pd.read_csv(path, encoding="utf-8-sig")
    upsert_df(df, "dim_store", "store_code", engine)


def load_dim_hub(engine):
    path = os.path.join(LANDING, "franchise_b", "hubmaster_weekly_refresh.psv")
    df = pd.read_csv(path, sep="|", encoding="utf-8-sig")
    upsert_df(df, "dim_hub", "hub_id", engine)


def load_dim_date(engine):
    """Populate calendar dimension for FY 25-26 + buffer."""
    dates = pd.date_range("2025-01-01", "2027-03-31")
    df = pd.DataFrame({
        "date_key": dates,
        "year": dates.year,
        "month": dates.month,
        "day": dates.day,
        "quarter": dates.quarter,
        "day_of_week": dates.dayofweek,
        "month_name": dates.strftime("%B"),
        "is_weekend": dates.dayofweek >= 5,
    })
    upsert_df(df, "dim_date", "date_key", engine)


# ── Franchise A ETL ─────────────────────────────

def _already_loaded(source_file: str, engine) -> bool:
    result = engine.execute(
        text("SELECT 1 FROM sales_fact WHERE source_file = :f LIMIT 1"),
        {"f": source_file},
    )
    return result.fetchone() is not None


def process_franchise_a(engine):
    log.info("=== Franchise A ===")
    valid_skus = set(pd.read_sql("SELECT sku_code FROM dim_product", engine)["sku_code"])
    now = pd.Timestamp.now()

    files = sorted(glob.glob(os.path.join(LANDING, "franchise_a", "sales_*.csv")))
    for fpath in files:
        fname = os.path.basename(fpath)
        with engine.connect() as conn:
            if conn.execute(text("SELECT 1 FROM sales_fact WHERE source_file = :f LIMIT 1"), {"f": fname}).fetchone():
                log.info(f"  SKIP (already loaded): {fname}")
                continue

        df = pd.read_csv(fpath, encoding="utf-8-sig")
        df["transaction_timestamp"] = pd.to_datetime(df["transaction_timestamp"])
        initial = len(df)

        # Quarantine
        df = quarantine(df, df["unit_price"].isna() | (df["unit_price"] <= 0), "A1", "A", fname, engine)
        df = quarantine(df, df["quantity"].abs() > 100, "A2", "A", fname, engine)
        df = quarantine(df, df["transaction_timestamp"] > now, "A3", "A", fname, engine)
        df = quarantine(df, ~df["sku_code"].isin(valid_skus), "A4", "A", fname, engine)

        # Map to fact schema
        fact = pd.DataFrame({
            "franchise_id": "A",
            "transaction_date": df["transaction_timestamp"],
            "sku_code": df["sku_code"],
            "store_or_hub_id": df["store_code"],
            "quantity": df["quantity"],
            "selling_price": df["unit_price"],
            "customer_id": df["customer_id"].replace("", None),
            "status": df["transaction_type"],
            "source_file": fname,
        })
        fact.to_sql("sales_fact", engine, if_exists="append", index=False, method="multi")
        log.info(f"  {fname}: {len(fact)} loaded / {initial - len(fact)} quarantined")


# ── Franchise B ETL ─────────────────────────────

def process_franchise_b(engine):
    log.info("=== Franchise B ===")

    # Load barcode mapping
    map_path = os.path.join(LANDING, "franchise_b", "barcode_sku_mapping.psv")
    bmap = pd.read_csv(map_path, sep="|", encoding="utf-8-sig")
    active_barcodes = set(bmap.loc[bmap["is_active"] == 1, "item_barcode"])
    barcode_to_sku = bmap.loc[bmap["is_active"] == 1].drop_duplicates("item_barcode").set_index("item_barcode")["sku_code"]

    now = pd.Timestamp.now()

    files = sorted(glob.glob(os.path.join(LANDING, "franchise_b", "sales_*.psv")))
    for fpath in files:
        fname = os.path.basename(fpath)
        with engine.connect() as conn:
            if conn.execute(text("SELECT 1 FROM sales_fact WHERE source_file = :f LIMIT 1"), {"f": fname}).fetchone():
                log.info(f"  SKIP (already loaded): {fname}")
                continue

        df = pd.read_csv(fpath, sep="|", encoding="utf-8-sig")
        df["delivery_timestamp"] = pd.to_datetime(df["delivery_timestamp"])
        initial = len(df)

        # Quarantine
        df = quarantine(df, df["mrp_price"] <= 0, "B1", "B", fname, engine)
        df = quarantine(df, (df["discount_applied"] < 0) | (df["discount_applied"] > df["mrp_price"]), "B2", "B", fname, engine)
        df = quarantine(df, df["delivery_timestamp"] > now, "B3", "B", fname, engine)
        df = quarantine(df, df.duplicated(subset="order_uuid", keep=False), "B4", "B", fname, engine)
        df = quarantine(df, ~df["item_barcode"].isin(active_barcodes), "B5", "B", fname, engine)

        # Barcode → SKU mapping
        df["sku_code"] = df["item_barcode"].map(barcode_to_sku)

        # Net price
        df["net_price"] = df["mrp_price"] - df["discount_applied"]

        # Map to fact schema
        fact = pd.DataFrame({
            "franchise_id": "B",
            "transaction_date": df["delivery_timestamp"],
            "sku_code": df["sku_code"],
            "store_or_hub_id": df["hub_id"],
            "quantity": df["units_sold"],
            "selling_price": df["net_price"],
            "customer_id": None,
            "status": df["status"],
            "source_file": fname,
        })
        fact.to_sql("sales_fact", engine, if_exists="append", index=False, method="multi")
        log.info(f"  {fname}: {len(fact)} loaded / {initial - len(fact)} quarantined")


# ── Main ────────────────────────────────────────

def run():
    engine = get_engine()
    log.info("Loading dimensions...")
    load_dim_product(engine)
    load_dim_customer(engine)
    load_dim_store(engine)
    load_dim_hub(engine)
    load_dim_date(engine)

    log.info("Processing sales...")
    process_franchise_a(engine)
    process_franchise_b(engine)

    # Summary
    with engine.connect() as conn:
        fact_count = conn.execute(text("SELECT COUNT(*) FROM sales_fact")).scalar()
        err_count = conn.execute(text("SELECT COUNT(*) FROM error_log")).scalar()
    log.info(f"=== Done. sales_fact={fact_count:,}  error_log={err_count:,} ===")


if __name__ == "__main__":
    run()
