import sys
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.decorators import task

# Add scripts folder to path so we can import our engine and loaders
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from etl_processor import (
    get_engine,
    load_dim_product_local,
    load_dim_customer_local,
    process_local_file,
    log,
)
from sqlalchemy import text

# ── Configuration ────────────────────────────────
# Storage is mounted as volume in docker-compose at /opt/airflow/storage
LANDING_ZONE_PATH = "/opt/airflow/storage/landing_zone"
# Add your franchise folder names here
FRANCHISES = ['franchise_a', 'franchise_b']

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# ── Task Callables ──────────────────────────────

def _load_dimensions(**ctx):
    """Refreshes dimension tables from master data in local storage."""
    engine = get_engine()
    load_dim_product_local(engine, LANDING_ZONE_PATH)
    load_dim_customer_local(engine, LANDING_ZONE_PATH)
    log.info("Dimension tables refreshed from local storage.")

@task
def process_local_franchise(franchise_id):
    """
    Dynamically maps across franchises, listing and processing 
    files from local landing_zone folders.
    """
    engine = get_engine()
    
    # Path inside your landing zone: landing_zone/franchise_a/, etc.
    prefix = os.path.join(LANDING_ZONE_PATH, franchise_id)
    
    if not os.path.exists(prefix):
        log.info(f"Directory not found for {franchise_id}: {prefix}")
        return

    files = [f for f in os.listdir(prefix) if f.endswith(('.csv', '.psv'))]
    
    if not files:
        log.info(f"No new files found for {franchise_id}.")
        return

    for file_name in files:
        file_path = os.path.join(prefix, file_name)
        
        # 1. Idempotency Check: Don't reload if the filename is in sales_fact
        with engine.connect() as conn:
            check_sql = text("SELECT 1 FROM sales_fact WHERE source_file = :f LIMIT 1")
            already_loaded = conn.execute(check_sql, {"f": file_name}).fetchone()
            
            if already_loaded:
                log.info(f"Skip already loaded: {file_name}")
                continue

        # 2. Process the file (now reading from local filesystem)
        process_local_file(engine, file_path, file_name, franchise_id)

def _log_summary(**ctx):
    """Final summary log of the data warehouse state."""
    engine = get_engine()
    with engine.connect() as conn:
        facts = conn.execute(text("SELECT COUNT(*) FROM sales_fact")).scalar()
    log.info(f"ETL Cycle Complete. Total facts in warehouse: {facts:,}")

# ── DAG Definition ──────────────────────────────

with DAG(
    dag_id="daily_load_job",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 2 * * *", # 07:30 IST
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["omni-data-hub-landing-zone-ranu", "gcs-cloud"],
) as dag:

    # Task 1: Update Dimension Tables
    t_dims = PythonOperator(
        task_id="load_dimensions",
        python_callable=_load_dimensions,
    )

    # Task 2: Process Franchises (Dynamic Task Mapping)
    # This creates parallel sub-tasks for each franchise in the list
    t_process = process_local_franchise.expand(franchise_id=FRANCHISES)

    # Task 3: Final Log
    t_summary = PythonOperator(
        task_id="log_summary",
        python_callable=_log_summary,
    )

    # Flow: Dimensions -> [Franchise A, Franchise B, ...] -> Summary
    t_dims >> t_process >> t_summary