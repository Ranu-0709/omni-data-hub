# Pipeline — Airflow ETL

## Overview
This folder contains the Apache Airflow DAG and Python ETL scripts that move raw landing-zone files into the PostgreSQL star-schema warehouse.

```
pipeline/
├── dags/
│   └── daily_load_job.py      # Airflow DAG definition
├── scripts/
│   └── etl_processor.py       # Core ETL logic (dimensions + sales)
├── requirements.txt
├── README.md
└── RUNBOOK.md
```

## Architecture

```
Landing Zone (CSV/PSV files)
        │
        ▼
┌──────────────────────────────────────┐
│  Airflow DAG: daily_load_job         │
│                                      │
│  load_dimensions                     │
│       │                              │
│       ├── process_franchise_a        │
│       ├── process_franchise_b        │
│       │                              │
│       └── log_summary                │
└──────────────────────────────────────┘
        │                    │
        ▼                    ▼
   sales_fact           error_log
   (clean rows)      (quarantined rows)
```

## DAG: daily_load_job

| Property | Value |
|----------|-------|
| Schedule | `0 2 * * *` (02:00 UTC / 07:30 IST daily) |
| Catchup | Disabled |
| Retries | 2 (5 min delay) |
| Executor | LocalExecutor |

### Tasks

| Task | Description |
|------|-------------|
| `load_dimensions` | Upserts product, customer, store, hub, and date dimensions |
| `process_franchise_a` | Loads CSV sales → quarantine (A1–A4) → insert into sales_fact |
| `process_franchise_b` | Loads PSV sales → quarantine (B1–B5) → barcode→SKU mapping → insert into sales_fact |
| `log_summary` | Logs today's load count and total warehouse size |

### Dependency Graph

```
load_dimensions → process_franchise_a ─┐
                → process_franchise_b ─┤→ log_summary
```

Franchise A and B run in parallel after dimensions are loaded.

## Setup

### With Docker (recommended)

```bash
# From project root
docker-compose up -d
```

The DAG is auto-detected — Airflow mounts `pipeline/dags/` to `/opt/airflow/dags/`.

### Local Development

```bash
pip install -r pipeline/requirements.txt

# Run ETL standalone (no Airflow needed)
python pipeline/scripts/etl_processor.py
```

## Configuration

All database credentials come from the `.env` file at project root:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=omnihub
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
LANDING_ZONE_PATH=./data_generator/storage/landing_zone
```

See `.env.example` for the template.

## Idempotency

The ETL is safe to re-run:
- Dimension tables use upsert (insert-or-skip on primary key)
- Sales files are tracked by `source_file` column — already-loaded files are skipped
- Quarantined rows are appended to `error_log` with the rule code that flagged them

## Database Tables

| Table | Type | Description |
|-------|------|-------------|
| `dim_product` | Dimension | 10K+ garment SKUs from manufacturer |
| `dim_customer` | Dimension | Loyalty program members |
| `dim_store` | Dimension | Franchise A brick-and-mortar stores |
| `dim_hub` | Dimension | Franchise B quick-commerce hubs |
| `dim_date` | Dimension | Calendar (FY 25-26 + buffer) |
| `sales_fact` | Fact | Unified sales from both franchises |
| `error_log` | Quarantine | Rows that failed validation rules |

Schema DDL: `database/init.sql`
