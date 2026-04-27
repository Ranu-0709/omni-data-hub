# Pipeline Runbook

Operational guide for monitoring, troubleshooting, and manual intervention.

## Monitoring

### Airflow UI

Access at `http://localhost:8080` (or your GCP server IP).

- **DAG:** `daily_load_job`
- **Green** = all tasks succeeded
- **Red** = at least one task failed (check task logs)
- **Yellow** = running or retrying

### Quick Health Check (SQL)

```sql
-- Today's load
SELECT franchise_id, COUNT(*) AS rows_loaded
FROM sales_fact
WHERE loaded_at::date = CURRENT_DATE
GROUP BY franchise_id;

-- Today's quarantine
SELECT franchise_id, rule_code, COUNT(*) AS flagged
FROM error_log
WHERE detected_at::date = CURRENT_DATE
GROUP BY franchise_id, rule_code
ORDER BY flagged DESC;

-- Total warehouse size
SELECT
  (SELECT COUNT(*) FROM sales_fact) AS total_facts,
  (SELECT COUNT(*) FROM error_log) AS total_errors;
```

## Quarantine Rules Reference

### Franchise A

| Rule | Condition | Typical Cause |
|------|-----------|---------------|
| A1 | `unit_price` is NaN or ≤ 0 | Injected error (~0.17% of rows) |
| A2 | `abs(quantity)` > 100 | qty = −500 injected error |
| A3 | `transaction_timestamp` in future | Year 2030 injected error |
| A4 | `sku_code` not in product master | Orphan SKU / typo |

### Franchise B

| Rule | Condition | Typical Cause |
|------|-----------|---------------|
| B1 | `mrp_price` ≤ 0 | Zero MRP injected error |
| B2 | `discount_applied` < 0 or > `mrp_price` | −1000 discount injected error |
| B3 | `delivery_timestamp` in future | Timestamp error |
| B4 | Duplicate `order_uuid` in file | Duplicated UUID injected error |
| B5 | `item_barcode` not in active mapping | Inactive/unknown barcode |

## Troubleshooting

### Task `load_dimensions` fails

1. Check Postgres is running: `docker ps | grep omni_db`
2. Verify `.env` credentials match `docker-compose.yml`
3. Confirm landing-zone files exist:
   ```
   ls data_generator/storage/landing_zone/master_company/
   ```
4. If tables don't exist, re-run init: `docker-compose down -v && docker-compose up -d`

### Task `process_franchise_a` or `process_franchise_b` fails

1. Check Airflow task logs for the specific file that failed
2. Common causes:
   - File encoding issue → ensure UTF-8 BOM (`utf-8-sig`)
   - Schema mismatch → compare CSV/PSV headers against expected columns
   - Disk full → check container disk usage
3. Fix the file, then re-trigger the task from Airflow UI (it will skip already-loaded files)

### High quarantine rate (> 1%)

```sql
-- Inspect quarantined rows for a specific rule
SELECT raw_row, source_file
FROM error_log
WHERE rule_code = 'B2'
ORDER BY detected_at DESC
LIMIT 20;
```

If the error rate is abnormally high, the source file may be corrupted. Check with the franchise data team.

## Manual Re-processing

To re-process a specific file that was already loaded:

```sql
-- 1. Remove existing rows
DELETE FROM sales_fact WHERE source_file = 'sales_monthly_2025_04.csv';
DELETE FROM error_log WHERE source_file = 'sales_monthly_2025_04.csv';

-- 2. Re-run the ETL (it will pick up the file again)
```

Then trigger the DAG manually from Airflow UI or run:

```bash
python pipeline/scripts/etl_processor.py
```

## Full Reset

```bash
# Destroy DB volume and recreate from init.sql
docker-compose down -v
docker-compose up -d

# Re-run ETL
python pipeline/scripts/etl_processor.py
```
