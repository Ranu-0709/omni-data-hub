"""
ETL Processor — Omni Data Hub (Local & Cloud Edition)
Updated: June 2026
Supports both local file system and GCS storage
"""

import os
import io
import json
import logging
import glob
import pandas as pd
from sqlalchemy import create_engine, text
try:
    from airflow.providers.google.cloud.hooks.gcs import GCSHook
    HAS_GCS = True
except ImportError:
    HAS_GCS = False

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

# ── Local File Dimension Loaders ─────────────────

def load_dim_product_local(engine, landing_zone_path):
    """Load product dimension from local master_company CSV."""
    file_path = os.path.join(landing_zone_path, "master_company", "product_master.csv")
    if not os.path.exists(file_path):
        log.warning(f"Product master file not found: {file_path}")
        return
    
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    cols = ["sku_code", "product_name", "brand", "category", "mrp"]
    # Only keep columns that exist in the file
    cols = [c for c in cols if c in df.columns]
    upsert_df(df[cols], "dim_product", "sku_code", engine)

def load_dim_customer_local(engine, landing_zone_path):
    """Load customer dimension from local master_company CSV."""
    file_path = os.path.join(landing_zone_path, "master_company", "customer_master.csv")
    if not os.path.exists(file_path):
        log.warning(f"Customer master file not found: {file_path}")
        return
    
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    upsert_df(df, "dim_customer", "customer_id", engine)

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
        # 1. Download and read the barcode-to-SKU mapping file from GCS
        mapping_content = hook.download(bucket_name=bucket_name, object_name="franchise_b/barcode_sku_mapping.psv")
        mapping_df = pd.read_csv(io.BytesIO(mapping_content), sep="|", encoding="utf-8-sig")
        
        # Keep only the columns we need for translation
        mapping_lookup = mapping_df[["item_barcode", "sku_code"]].drop_duplicates()

        # 2. Merge the incoming sales dataframe with the lookup map
        # This appends the true 'sku_code' column onto Franchise B's data dynamically!
        df = df.merge(mapping_lookup, on="item_barcode", how="left")

        # 3. Handle data cleanups and formatting
        df["mrp_price"] = pd.to_numeric(df["mrp_price"], errors='coerce')
        df["units_sold"] = pd.to_numeric(df["units_sold"], errors='coerce')
        df["delivery_timestamp"] = pd.to_datetime(df["delivery_timestamp"], errors='coerce')
        
        discount = pd.to_numeric(df.get("discount_applied", 0), errors='coerce').fillna(0)
        df["net_price"] = df["mrp_price"] - discount

        # 4. Map securely to the target star schema
        fact = pd.DataFrame({
            "franchise_id": franchise_id,
            "transaction_date": df["delivery_timestamp"],
            "sku_code": df["sku_code"],  # <--- Safe now! It was added via the merge.
            "store_or_hub_id": df["hub_id"],
            "quantity": df["units_sold"],
            "selling_price": df["net_price"],
            "customer_id": None,  # Quick-commerce transactions don't pass a loyalty master id here
            "status": df.get("status", "DELIVERED"),
            "source_file": fname
        })

    # 5. Final Load to Star Schema
    if not fact.empty:
        fact.to_sql("sales_fact", engine, if_exists="append", index=False, method="multi")
        log.info(f"  {fname}: {len(fact)} loaded / {initial_count - len(fact)} quarantined")
    else:
        log.warning(f"  {fname}: No valid records to load.")

# ── Local File Processor ─────────────────────────

def process_local_file(engine, file_path, file_name, franchise_id):
    """
    Core Logic: Reads file from local filesystem, handles franchise-specific mappings,
    and loads to the star-schema sales_fact table.
    """
    if not os.path.exists(file_path):
        log.warning(f"File not found: {file_path}")
        return
    
    # Skip non-sales files (masters, mappings, etc.)
    if file_name.endswith("_master.csv") or file_name.endswith("_master.psv") or \
       file_name.endswith("_mapping.psv") or file_name.endswith("_refresh.csv") or \
       file_name.endswith("_refresh.psv"):
        log.info(f"  Skipping master/mapping file: {file_name}")
        return
    
    # Auto-detect separator for .psv vs .csv
    sep = "|" if file_name.lower().endswith('.psv') else ","
    df = pd.read_csv(file_path, sep=sep, encoding="utf-8-sig")
    initial_count = len(df)
    log.info(f"  Processing {file_name}: {initial_count} rows, columns: {list(df.columns)}")

    if franchise_id == "franchise_a":
        # Franchise A: Uses unit_price and transaction_timestamp
        # Make numeric conversions safe
        if "unit_price" not in df.columns:
            log.error(f"  Column 'unit_price' not found in {file_name}. Available: {list(df.columns)}")
            return
        
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors='coerce')
        df["quantity"] = pd.to_numeric(df.get("quantity", 0), errors='coerce')
        df["transaction_timestamp"] = pd.to_datetime(df.get("transaction_timestamp"), errors='coerce')
        
        # Validation - quarantine rows with bad unit_price
        bad_price_mask = df["unit_price"].isna() | (df["unit_price"] <= 0)
        df = quarantine(df, bad_price_mask, "F1_VAL", franchise_id, file_name, engine)
        
        fact = pd.DataFrame({
            "franchise_id": franchise_id,
            "transaction_date": df.get("transaction_timestamp"),
            "sku_code": df.get("sku_code"),
            "store_or_hub_id": df.get("store_code"),
            "quantity": df.get("quantity"),
            "selling_price": df.get("unit_price"),
            "customer_id": df.get("customer_id"),
            "status": df.get("transaction_type", "COMPLETED"),
            "source_file": file_name
        })

    elif franchise_id == "franchise_b":
        # 1. Read the barcode-to-SKU mapping file from local landing zone (franchise_b folder)
        mapping_file = os.path.join(os.path.dirname(file_path), "barcode_sku_mapping.psv")
        if not os.path.exists(mapping_file):
            log.warning(f"Barcode mapping file not found: {mapping_file}")
            return
        
        mapping_df = pd.read_csv(mapping_file, sep="|", encoding="utf-8-sig")
        
        # Keep only the columns we need for translation
        mapping_lookup = mapping_df[["item_barcode", "sku_code"]].drop_duplicates()
        
        # Ensure barcode column types match before merging
        if "item_barcode" in df.columns:
            df["item_barcode"] = df["item_barcode"].astype(str)
            mapping_lookup["item_barcode"] = mapping_lookup["item_barcode"].astype(str)

        # 2. Merge the incoming sales dataframe with the lookup map
        if "item_barcode" in df.columns:
            df = df.merge(mapping_lookup, on="item_barcode", how="left")

        # 3. Handle data cleanups and formatting
        df["mrp_price"] = pd.to_numeric(df.get("mrp_price", 0), errors='coerce')
        df["units_sold"] = pd.to_numeric(df.get("units_sold", 0), errors='coerce')
        df["delivery_timestamp"] = pd.to_datetime(df.get("delivery_timestamp"), errors='coerce')
        
        discount = pd.to_numeric(df.get("discount_applied", 0), errors='coerce').fillna(0)
        df["net_price"] = df["mrp_price"] - discount

        # 4. Map to the target star schema
        fact = pd.DataFrame({
            "franchise_id": franchise_id,
            "transaction_date": df.get("delivery_timestamp"),
            "sku_code": df.get("sku_code"),
            "store_or_hub_id": df.get("hub_id"),
            "quantity": df.get("units_sold"),
            "selling_price": df.get("net_price"),
            "customer_id": None,
            "status": df.get("status", "DELIVERED"),
            "source_file": file_name
        })
    else:
        log.error(f"Unknown franchise_id: {franchise_id}")
        return

    # 5. Final Load to Star Schema
    if not fact.empty and len(fact) > 0:
        # Only insert rows that have valid timestamp and sku_code
        fact = fact.dropna(subset=["transaction_date", "sku_code"])
        if len(fact) > 0:
            fact.to_sql("sales_fact", engine, if_exists="append", index=False, method="multi")
            log.info(f"  {file_name}: {len(fact)} loaded / {initial_count - len(fact)} quarantined/filtered")
        else:
            log.warning(f"  {file_name}: No valid records after filtering")
    else:
        log.warning(f"  {file_name}: No records to load")