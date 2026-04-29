"""
Airflow DAG — Daily Load Job
Runs the ETL processor to ingest landing-zone files into the Postgres warehouse.

Schedule: daily at 02:00 UTC (07:30 IST)
Tasks:
  load_dimensions → process_franchise_a ─┐
                  → process_franchise_b ─┤→ log_summary
"""

import sys
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Make etl_processor importable (mounted at /opt/airflow/scripts in Docker)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from etl_processor import (
    get_engine,
    load_dim_product,
    load_dim_customer,
    load_dim_store,
    load_dim_hub,
    load_dim_date,
    process_franchise_a,
    process_franchise_b,
    log,
)
from sqlalchemy import text

# ── DAG Config ──────────────────────────────────

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


# ── Task Callables ──────────────────────────────

def _load_dimensions(**ctx):
    engine = get_engine()
    load_dim_product(engine)
    load_dim_customer(engine)
    load_dim_store(engine)
    load_dim_hub(engine)
    load_dim_date(engine)
    log.info("All dimensions loaded.")


def _process_franchise_a(**ctx):
    process_franchise_a(get_engine())


def _process_franchise_b(**ctx):
    process_franchise_b(get_engine())


def _log_summary(**ctx):
    engine = get_engine()
    with engine.connect() as conn:
        facts = conn.execute(text("SELECT COUNT(*) FROM sales_fact")).scalar()
        errors = conn.execute(text("SELECT COUNT(*) FROM error_log")).scalar()
        today_facts = conn.execute(
            text("SELECT COUNT(*) FROM sales_fact WHERE loaded_at::date = CURRENT_DATE")
        ).scalar()
        today_errors = conn.execute(
            text("SELECT COUNT(*) FROM error_log WHERE detected_at::date = CURRENT_DATE")
        ).scalar()
    log.info(f"Today: {today_facts:,} loaded, {today_errors:,} quarantined")
    log.info(f"Total: {facts:,} facts, {errors:,} errors")


# ── DAG Definition ──────────────────────────────

with DAG(
    dag_id="daily_load_job",
    default_args=DEFAULT_ARGS,
    description="Ingest landing-zone CSV/PSV files into the Omni Data Hub warehouse",
    schedule_interval="0 2 * * *",  # 02:00 UTC daily
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["omni-data-hub", "etl"],
) as dag:

    t_dims = PythonOperator(
        task_id="load_dimensions",
        python_callable=_load_dimensions,
    )

    t_fa = PythonOperator(
        task_id="process_franchise_a",
        python_callable=_process_franchise_a,
    )

    t_fb = PythonOperator(
        task_id="process_franchise_b",
        python_callable=_process_franchise_b,
    )

    t_summary = PythonOperator(
        task_id="log_summary",
        python_callable=_log_summary,
    )

    # Dimensions first, then both franchises in parallel, then summary
    t_dims >> [t_fa, t_fb] >> t_summary
