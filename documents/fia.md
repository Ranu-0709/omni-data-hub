# Fault Impact Analysis (FIA): Omni Data Hub

## 1. Purpose
This document identifies every known failure point in the Omni Data Hub system, assesses the business impact of each, and defines the mitigation and recovery strategy. It covers the full data path — from franchise file uploads through the ETL pipeline, PostgreSQL warehouse, and both frontend dashboards.

## 2. Severity Definitions

| Severity | Label | Meaning |
|----------|-------|---------|
| S1 | Critical | Complete system outage — no data flows, no dashboards |
| S2 | High | Major feature broken — one franchise or one dashboard down |
| S3 | Medium | Degraded experience — stale data, partial errors, slow queries |
| S4 | Low | Minor inconvenience — cosmetic, logging, non-blocking |

## 3. Component Map

```
Franchise A (CSV) ──┐                          ┌── Vercel Frontend (Public)
Franchise B (PSV) ──┤→ Landing Zone → Airflow → PostgreSQL ──┤
Master Company ─────┘     (GCP)       (GCP)      (GCP)       └── GCP Admin Frontend
```

---

## 4. Fault Catalog

### 4.1 Data Source Faults

| ID | Fault | Trigger | Severity | Impact | Mitigation |
|----|-------|---------|----------|--------|------------|
| DS-01 | Franchise A file not uploaded | Store POS system down, manual upload missed | S2 | Missing weekly sales for brick-and-mortar channel; dashboard shows stale Franchise A data | Airflow `log_summary` task reports zero new rows; alert the franchise ops team. ETL is idempotent — file will be picked up on next run after upload. |
| DS-02 | Franchise B file not uploaded | Hub system outage, network failure | S2 | Missing daily sales for quick-commerce channel | Same as DS-01. Daily cadence means gap is noticed within 24 hours. |
| DS-03 | Wrong file format (CSV instead of PSV or vice versa) | Franchise team uploads wrong format | S3 | Pandas read fails on delimiter mismatch; entire file skipped, logged as Airflow task error | ETL catches `ParserError`; file remains in landing zone for re-processing after correction. Add file-format validation as a pre-check. |
| DS-04 | Encoding corruption (not UTF-8 BOM) | Franchise exports from legacy system without BOM | S3 | Hindi (Devanagari) text garbled — product names, store names, customer names display as mojibake | ETL reads with `encoding='utf-8-sig'`; if file is Latin-1 or other encoding, `UnicodeDecodeError` raised. File quarantined. Admin dashboard (US-11) flags encoding issues. |
| DS-05 | Schema change (new/missing/renamed columns) | Franchise upgrades POS software | S2 | `KeyError` in ETL — entire file fails to process | ETL should validate column headers before processing. Currently fails loudly — Airflow task goes red. Requires manual column mapping fix. |
| DS-06 | Empty file uploaded | Franchise system glitch | S4 | Pandas reads 0 rows; ETL logs "0 loaded" and moves on | No impact. `log_summary` shows zero rows for that file. |
| DS-07 | Duplicate file uploaded | Franchise re-uploads same file | S4 | ETL skips — idempotency check on `source_file` column prevents double-loading | No impact. Already handled by design. |
| DS-08 | Abnormally high error rate (> 5%) | Corrupted POS export, software bug at franchise | S3 | Large volume of rows quarantined to `error_log`; dashboard revenue appears artificially low | `log_summary` reports quarantine count. Admin dashboard quarantine feed (US-08) surfaces the spike. Investigate source file with franchise team. |

### 4.2 Landing Zone Faults

| ID | Fault | Trigger | Severity | Impact | Mitigation |
|----|-------|---------|----------|--------|------------|
| LZ-01 | GCS bucket permissions revoked | IAM misconfiguration | S1 | No files accessible — entire ETL fails | Service Account permissions audited during setup (Phase 2). `setup_server.sh` documents required IAM roles. Airflow task fails immediately with clear permission error. |
| LZ-02 | Disk full on GCP VM | Large file accumulation, no cleanup policy | S2 | New files cannot be written; ETL cannot read partially written files | Monitor disk usage. Implement retention policy — archive files older than 90 days to cold storage. |
| LZ-03 | File deleted before ETL runs | Manual cleanup, accidental deletion | S2 | ETL skips the file (glob finds nothing); data gap in warehouse | Landing zone should be append-only. Restrict delete permissions to admin Service Account only. |

### 4.3 Pipeline / Airflow Faults

| ID | Fault | Trigger | Severity | Impact | Mitigation |
|----|-------|---------|----------|--------|------------|
| PL-01 | Airflow scheduler down | Container crash, OOM kill | S1 | No DAGs execute — all data ingestion stops | Docker restart policy (`restart: unless-stopped`). Monitor container health. `docker-compose up -d` recovers. |
| PL-02 | Airflow webserver down | Port conflict, container crash | S3 | Cannot monitor DAGs via UI, but scheduler still runs DAGs on schedule | Webserver is independent of scheduler. Restart container. DAG execution unaffected. |
| PL-03 | `load_dimensions` task fails | DB connection refused, master file missing | S1 | Downstream tasks (`process_franchise_a`, `process_franchise_b`) are blocked — no sales loaded | Task has 2 retries with 5-min delay. If DB is down, fix DB first. If file missing, re-run seed generator. |
| PL-04 | `process_franchise_a` fails mid-file | OOM on large file, DB connection timeout | S2 | Partial load — some rows inserted, file not marked complete | On retry, ETL checks `source_file` — if rows exist, it skips. Risk: partial file appears loaded. Mitigation: wrap file processing in a transaction (future improvement). |
| PL-05 | `process_franchise_b` fails mid-file | Same as PL-04 | S2 | Same as PL-04 for Franchise B | Same mitigation. |
| PL-06 | Barcode mapping file missing or corrupt | File deleted, encoding issue | S2 | All Franchise B sales fail rule B5 (unknown barcode) — entire file quarantined | ETL should check mapping file existence before processing sales. Currently fails with `FileNotFoundError`. |
| PL-07 | ETL script import error | Dependency missing in container, syntax error after code push | S1 | DAG fails to parse — Airflow shows "Import Error" | Pin dependencies in `pipeline/requirements.txt`. Test DAG parsing before deploying: `python -c "import daily_load_job"`. |
| PL-08 | SQLAlchemy connection pool exhausted | Too many concurrent connections, connection leak | S2 | `OperationalError` — tasks fail to connect to DB | `pool_pre_ping=True` already configured. Set `pool_size` and `max_overflow` limits. Ensure connections are closed after use. |

### 4.4 Database Faults

| ID | Fault | Trigger | Severity | Impact | Mitigation |
|----|-------|---------|----------|--------|------------|
| DB-01 | PostgreSQL container down | OOM kill, disk full, Docker daemon restart | S1 | All ETL fails, admin dashboard down, no new data to Vercel | Docker restart policy. Monitor with `docker ps`. Recovery: `docker-compose up -d postgres`. Data persists in Docker volume. |
| DB-02 | Database volume lost | `docker-compose down -v` (accidental), disk failure | S1 | All warehouse data lost — dimensions, facts, error log | Backup strategy: daily `pg_dump` to GCS. Recovery: restore from backup, then re-run ETL (idempotent, but source files must still exist in landing zone). |
| DB-03 | `init.sql` not executed on first boot | File not mounted correctly in `docker-compose.yml` | S1 | Tables don't exist — every ETL query fails with `relation does not exist` | Verify volume mount: `./database/init.sql:/docker-entrypoint-initdb.d/init.sql`. If missed, run `init.sql` manually: `psql -U admin -d omnihub -f init.sql`. |
| DB-04 | `sales_fact` table bloat (100M+ rows) | Normal growth over months of operation | S3 | Slow dashboard queries, slow `COUNT(*)` in `log_summary` | Add table partitioning by `transaction_date` (monthly). Create summary/materialized views for dashboard queries. Existing indexes (`idx_sf_franchise`, `idx_sf_date`, `idx_sf_sku`) help but won't prevent full-scan slowdowns. |
| DB-05 | `error_log` table bloat | High error rate over time | S4 | Slow quarantine queries on admin dashboard | Implement retention: archive error_log rows older than 90 days. Add index on `detected_at`. |
| DB-06 | Foreign key violation on `sales_fact.sku_code` | Barcode maps to SKU not in `dim_product` | S3 | Insert fails for that batch of rows | ETL loads dimensions before facts (DAG dependency). If a new SKU appears in mapping but not in product master, the FK constraint rejects it. Fix: update product master first. |
| DB-07 | `.env` credentials mismatch | `.env` edited but docker-compose not restarted | S1 | ETL connects with wrong credentials — `OperationalError: password authentication failed` | Keep `.env` as single source of truth. After editing, always `docker-compose down && docker-compose up -d`. |

### 4.5 Frontend Faults

| ID | Fault | Trigger | Severity | Impact | Mitigation |
|----|-------|---------|----------|--------|------------|
| FE-01 | Vercel deployment fails | Build error in `frontend/` code, dependency issue | S2 | Public executive dashboard shows last successful deployment (stale but functional) | Vercel auto-rollback to last working build. Fix code and re-push. Dashboard data is unaffected (comes from Vercel Postgres). |
| FE-02 | Vercel Postgres unreachable | Vercel infra outage, connection limit hit | S2 | Executive dashboard shows error or empty charts | Vercel status page monitoring. Connection pooling via `@vercel/postgres`. No local mitigation — depends on Vercel SLA. |
| FE-03 | Vercel Postgres not synced with GCP warehouse | Sync job not implemented yet, or sync fails | S3 | Executive dashboard shows stale summary data while GCP warehouse has fresh data | Implement a sync step in the Airflow DAG (future) that pushes aggregated summaries to Vercel Postgres after each ETL run. |
| FE-04 | Admin dashboard (GCP) down | `frontend-admin` container crash, port 80 conflict | S3 | Data admins cannot monitor quarantine or raw data — but ETL continues running | Restart container: `docker-compose up -d frontend_admin`. ETL and data flow are unaffected. |
| FE-05 | Hindi text renders as boxes/squares | Frontend font missing Devanagari glyphs | S4 | ~15% of product names, store names, customer names display incorrectly | Ensure frontend uses a font with Devanagari support (e.g., Noto Sans). CSS: `font-family: 'Noto Sans', sans-serif`. |
| FE-06 | Dashboard slow (> 2s load) | Large unindexed queries, no summary tables | S3 | Violates NFR — executives experience poor UX | Vercel frontend reads only from lightweight summary tables (by design). If slow, check Vercel Postgres query plans. GCP admin dashboard may be slow on raw data — add materialized views. |

### 4.6 Infrastructure Faults

| ID | Fault | Trigger | Severity | Impact | Mitigation |
|----|-------|---------|----------|--------|------------|
| IF-01 | GCP VM down | GCP zone outage, billing issue, accidental deletion | S1 | Everything on GCP stops — DB, Airflow, admin dashboard. Vercel frontend stays up but with stale data. | GCP uptime SLA. Rebuild from `setup_server.sh` + `docker-compose.yml` + GitHub repo. Restore DB from backup. |
| IF-02 | Docker daemon crash | Kernel update, resource exhaustion | S1 | All containers stop | SSH into VM, restart Docker: `sudo systemctl restart docker`. Containers with restart policy come back automatically. |
| IF-03 | `code-server` down | Process crash, port conflict | S4 | Developers cannot access remote workspace via browser | `sudo systemctl restart code-server@$USER`. No impact on data pipeline or dashboards. |
| IF-04 | GitHub repo unavailable | GitHub outage | S4 | Cannot push code or trigger Vercel deploys | Temporary — wait for GitHub recovery. Local code unaffected. Vercel serves last successful build. |
| IF-05 | SSL/domain routing failure | Certificate expiry, DNS misconfiguration | S3 | Custom domain inaccessible — users see browser security warning | Renew certificate. Verify DNS records. Vercel handles SSL automatically for its domain. GCP domain needs manual cert management. |

---

## 5. Risk Heat Map

```
              Low Impact ◄──────────────────► High Impact
            ┌─────────────┬─────────────┬─────────────┐
 Likely     │ DS-06,DS-07 │ DS-01,DS-02 │             │
            │ FE-05       │ DS-08       │             │
            ├─────────────┼─────────────┼─────────────┤
 Possible   │ IF-03,IF-04 │ DS-03,DS-04 │ PL-04,PL-05│
            │ DB-05       │ FE-03,FE-06 │ PL-06       │
            ├─────────────┼─────────────┼─────────────┤
 Unlikely   │ PL-02       │ DS-05,LZ-02 │ DB-01,DB-02│
            │             │ DB-04,DB-06 │ IF-01,IF-02│
            │             │ FE-01,IF-05 │ PL-01,DB-07│
            └─────────────┴─────────────┴─────────────┘
```

## 6. Recovery Time Objectives

| Scenario | RTO | RPO | Recovery Steps |
|----------|-----|-----|----------------|
| Single container crash | < 5 min | 0 (no data loss) | Docker auto-restart or `docker-compose up -d` |
| PostgreSQL data loss | < 1 hour | Last backup (daily) | Restore `pg_dump` from GCS, re-run ETL for delta |
| Full GCP VM loss | < 2 hours | Last backup | Provision new VM, run `setup_server.sh`, clone repo, `docker-compose up -d`, restore DB backup |
| Vercel outage | N/A | N/A | Wait for Vercel recovery — outside our control |
| Corrupted source file | < 30 min | 0 | Delete bad rows from `sales_fact` + `error_log` by `source_file`, fix file, re-trigger DAG |

## 7. Monitoring Checklist

| What | How | Frequency |
|------|-----|-----------|
| Airflow DAG status | Airflow UI — green/red/yellow | Daily |
| Quarantine spike | `SELECT rule_code, COUNT(*) FROM error_log WHERE detected_at::date = CURRENT_DATE GROUP BY rule_code` | Daily |
| Row counts | `log_summary` Airflow task output | Every DAG run |
| Disk usage | `df -h` on GCP VM | Weekly |
| Docker container health | `docker ps` | Daily |
| Vercel build status | Vercel dashboard | On each push |
| DB table sizes | `SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class WHERE relkind='r' ORDER BY pg_total_relation_size(oid) DESC LIMIT 10;` | Weekly |

## 8. Open Risks & Future Mitigations

| Risk | Current State | Planned Mitigation |
|------|--------------|-------------------|
| No automated DB backup | Manual `pg_dump` only | Schedule daily `pg_dump` to GCS via cron or Airflow DAG |
| Partial file load (PL-04/PL-05) | File marked as loaded even if partial | Wrap per-file insert in a DB transaction with rollback on failure |
| No Vercel Postgres sync | Summary tables not populated | Add sync task to Airflow DAG after `log_summary` |
| No alerting | Failures only visible in Airflow UI | Integrate Airflow email/Slack alerts on task failure |
| Single VM, single zone | Full outage if VM or zone goes down | Move to managed services (Cloud SQL, Cloud Composer) for HA |
| No rate limiting on admin dashboard | Heavy queries could slow DB for ETL | Connection pooling + read replica for admin dashboard |
