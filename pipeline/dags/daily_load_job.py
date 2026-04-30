import sys
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.decorators import task

# Add scripts folder to path so we can import our engine and loaders
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from etl_processor import (
    get_engine,
    load_dim_product_gcs,
    load_dim_customer_gcs,
    process_gcs_file,
    log,
)
from sqlalchemy import text

# ── Configuration ────────────────────────────────
BUCKET_NAME = "omni-franchise-data-hub"
# Add your franchise folder names here
FRANCHISES = ['franchise_A', 'franchise_B']

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# ── Task Callables ──────────────────────────────

def _load_dimensions(**ctx):
    """Refreshes dimension tables from master data in GCS."""
    engine = get_engine()
    # Note: We now pass the BUCKET_NAME to our new GCS-aware loaders
    load_dim_product_gcs(engine, BUCKET_NAME)
    load_dim_customer_gcs(engine, BUCKET_NAME)
    log.info("Dimension tables refreshed from GCS.")

@task
def process_gcs_franchise(franchise_id):
    """
    Dynamically maps across franchises, listing and processing 
    files from GCS landed/ folders.
    """
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    engine = get_engine()
    
    # Path inside your bucket: landed/franchise_A/, etc.
    prefix = f'landed/{franchise_id}/'
    files = hook.list(bucket_name=BUCKET_NAME, prefix=prefix)
    
    if not files:
        log.info(f"No new files found for {franchise_id}.")
        return

    for file_name in files:
        # We only want data files, not folder markers
        if file_name.endswith(('.csv', '.psv')):
            # 1. Idempotency Check: Don't reload if the filename is in sales_fact
            with engine.connect() as conn:
                check_sql = text("SELECT 1 FROM sales_fact WHERE source_file = :f LIMIT 1")
                already_loaded = conn.execute(check_sql, {"f": os.path.basename(file_name)}).fetchone()
                
                if already_loaded:
                    log.info(f"Skip already loaded: {file_name}")
                    continue

            # 2. Process the file (now streaming from GCS to memory)
            process_gcs_file(engine, BUCKET_NAME, file_name, franchise_id)
            
            # 3. Archive: Move to 'archived/' and delete from 'landed/'
            archive_name = file_name.replace('landed/', 'archived/')
            hook.copy(source_bucket=BUCKET_NAME, source_object=file_name, 
                      destination_object=archive_name)
            hook.delete(bucket_name=BUCKET_NAME, object_name=file_name)

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
    tags=["omni-data-hub", "gcs-cloud"],
) as dag:

    # Task 1: Update Dimension Tables
    t_dims = PythonOperator(
        task_id="load_dimensions",
        python_callable=_load_dimensions,
    )

    # Task 2: Process Franchises (Dynamic Task Mapping)
    # This creates parallel sub-tasks for each franchise in the list
    t_process = process_gcs_franchise.expand(franchise_id=FRANCHISES)

    # Task 3: Final Log
    t_summary = PythonOperator(
        task_id="log_summary",
        python_callable=_log_summary,
    )

    # Flow: Dimensions -> [Franchise A, Franchise B, ...] -> Summary
    t_dims >> t_process >> t_summary