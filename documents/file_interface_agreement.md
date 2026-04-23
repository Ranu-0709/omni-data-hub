# File Interface Agreement (FIA): Omni Data Hub

## 1. Purpose
This document defines the exact file contract between each data provider (Master Company, Franchise A, Franchise B) and the Omni Data Hub ingestion layer. Any file that does not conform to this agreement will be rejected or quarantined by the ETL pipeline.

All parties must treat this document as the single source of truth for file format, naming, encoding, delivery schedule, and column specifications.

## 2. General Rules (All Files)

| Property | Requirement |
|----------|-------------|
| Encoding | UTF-8 with BOM (`utf-8-sig`) |
| Line ending | LF (`\n`) or CRLF (`\r\n`) — both accepted |
| Header row | Mandatory — first row must contain exact column names as specified below |
| Quoting | Fields containing the delimiter or newlines must be quoted with double quotes (`"`) |
| Null representation | Empty string (no value between delimiters) — not the literal text `NULL` or `None` |
| Multilingual text | Hindi (Devanagari, U+0900–U+097F) is permitted in text fields. No transliteration required. |
| Trailing newline | Optional — accepted but not required |
| Max file size | 2 GB per file |

---

## 3. Landing Zone Structure

```
storage/landing_zone/
├── master_company/          ← Manufacturer-owned reference data
│   ├── product_master.csv
│   └── customer_master.csv
├── franchise_a/             ← Brick-and-mortar store data
│   ├── storemaster_monthly_refresh.csv
│   ├── sales_monthly_YYYY_MM.csv
│   └── sales_weekly_YYYY_MM_DD.csv
└── franchise_b/             ← Quick-commerce hub data
    ├── hubmaster_weekly_refresh.psv
    ├── barcode_sku_mapping.psv
    ├── sales_monthly_YYYY_MM.psv
    └── sales_daily_YYYY_MM_DD.psv
```

Each provider must upload files **only** to their designated folder. Cross-folder uploads will be ignored.

---

## 4. File Specifications

### 4.1 Master Company — Product Master

| Property | Value |
|----------|-------|
| File name | `product_master.csv` |
| Delimiter | Comma (`,`) |
| Delivery | On demand — whenever the product catalog changes |
| Delivery method | Full replacement (overwrite) |
| Owner | Master Company (Garment Manufacturer) |

| # | Column | Type | Nullable | Description | Example |
|---|--------|------|----------|-------------|---------|
| 1 | `sku_code` | VARCHAR(20) | No | Unique manufacturer SKU | `SKU-0001` |
| 2 | `ean_barcode` | BIGINT | No | EAN-13 barcode (890x series) | `8908830421175` |
| 3 | `product_name` | TEXT | No | Brand + garment type (may contain Hindi) | `WeaveMaster Dhoti` |
| 4 | `brand` | VARCHAR(50) | No | Brand label | `UrbanWeave` |
| 5 | `category` | VARCHAR(50) | No | Garment category | `Ethnic Wear` |
| 6 | `sub_category` | VARCHAR(50) | No | Garment sub-category | `Dhoti` |
| 7 | `size` | VARCHAR(20) | No | Size code | `34`, `XL`, `Free Size` |
| 8 | `color` | VARCHAR(30) | No | Color name | `Charcoal` |
| 9 | `fabric` | VARCHAR(30) | No | Fabric type | `Poly-Cotton` |
| 10 | `batch_code` | VARCHAR(20) | No | Manufacturing batch | `B2410-895` |
| 11 | `manufacturing_date` | DATE | No | Format: `YYYY-MM-DD` | `2024-10-28` |
| 12 | `mrp` | DECIMAL(10,2) | No | Maximum retail price (₹) | `7947.71` |
| 13 | `hsn_code` | INT | No | HSN code for GST | `6217` |
| 14 | `gst_pct` | INT | No | GST slab (5 or 12) | `5` |

**Constraints:**
- `sku_code` must be unique across the file
- `ean_barcode` must be a valid 13-digit number in the 890x range
- `mrp` must be > 0
- `gst_pct` must be 5 or 12

---

### 4.2 Master Company — Customer Master

| Property | Value |
|----------|-------|
| File name | `customer_master.csv` |
| Delimiter | Comma (`,`) |
| Delivery | On demand — whenever loyalty membership changes |
| Delivery method | Full replacement (overwrite) |
| Owner | Master Company (Garment Manufacturer) |

| # | Column | Type | Nullable | Description | Example |
|---|--------|------|----------|-------------|---------|
| 1 | `customer_id` | VARCHAR(20) | No | Loyalty program ID | `LOYAL-0001` |
| 2 | `customer_name` | TEXT | No | Full name (may contain Hindi) | `Bachittar Bhakta` |
| 3 | `phone` | VARCHAR(30) | No | Indian phone number | `08439581885` |
| 4 | `email` | VARCHAR(100) | No | Email address | `user@example.com` |
| 5 | `city` | VARCHAR(50) | No | Indian city | `Rourkela` |
| 6 | `state` | VARCHAR(10) | No | State code | `OD` |
| 7 | `loyalty_tier` | VARCHAR(20) | No | Tier level | `Bronze`, `Silver`, `Gold`, `Platinum` |
| 8 | `join_date` | DATE | No | Format: `YYYY-MM-DD` | `2022-10-10` |

**Constraints:**
- `customer_id` must be unique across the file
- `loyalty_tier` must be one of: `Bronze`, `Silver`, `Gold`, `Platinum`

---

### 4.3 Franchise A — Store Master

| Property | Value |
|----------|-------|
| File name | `storemaster_monthly_refresh.csv` |
| Delimiter | Comma (`,`) |
| Delivery | Monthly (1st week of each month) |
| Delivery method | Full replacement (overwrite) |
| Owner | Franchise A |

| # | Column | Type | Nullable | Description | Example |
|---|--------|------|----------|-------------|---------|
| 1 | `store_code` | VARCHAR(20) | No | Store identifier | `FA-001` |
| 2 | `store_name` | TEXT | No | Store name (may contain Hindi) | `Mammen, Magar and Mutti` |
| 3 | `city` | VARCHAR(50) | No | Indian city | `Surat` |
| 4 | `state` | VARCHAR(10) | No | State code | `GJ` |

**Constraints:**
- `store_code` must be unique across the file
- `store_code` must follow the pattern `FA-NNN`

---

### 4.4 Franchise A — Sales

| Property | Value |
|----------|-------|
| File name | `sales_monthly_YYYY_MM.csv` (seed/historical) or `sales_weekly_YYYY_MM_DD.csv` (incremental) |
| Delimiter | Comma (`,`) |
| Delivery | Weekly (every Monday for the prior week) |
| Delivery method | Append (new file per period — never overwrite previous files) |
| Owner | Franchise A |

| # | Column | Type | Nullable | Description | Example |
|---|--------|------|----------|-------------|---------|
| 1 | `invoice_number` | VARCHAR(20) | No | Invoice ID | `INV-71064` |
| 2 | `store_code` | VARCHAR(20) | No | FK → store master | `FA-006` |
| 3 | `transaction_timestamp` | DATETIME | No | Format: `YYYY-MM-DD HH:MM:SS` | `2025-04-02 02:35:05` |
| 4 | `sku_code` | VARCHAR(20) | No | FK → product master | `SKU-0681` |
| 5 | `quantity` | INT | No | Units sold (negative = return) | `3` or `-2` |
| 6 | `unit_price` | DECIMAL(10,2) | No | Selling price per unit (₹) | `5669.67` |
| 7 | `transaction_type` | VARCHAR(10) | No | `SALE` or `RETURN` | `SALE` |
| 8 | `customer_id` | VARCHAR(20) | **Yes** | FK → customer master (blank = walk-in) | `LOYAL-3654` or `` |

**Naming convention:**
- Historical (seed): `sales_monthly_2025_04.csv`
- Incremental: `sales_weekly_2026_04_01.csv` (date = Monday of that week)

**Constraints:**
- `store_code` must exist in the current store master
- `sku_code` must exist in the product master
- `unit_price` must not be NaN and must be > 0
- `quantity` absolute value must be ≤ 100 for a single line item
- `transaction_timestamp` must not be in the future
- `transaction_type` must be `SALE` or `RETURN`
- `customer_id` may be blank (walk-in customer, up to ~21% of rows)

**Known data quality errors (~0.5% of rows):**
- `quantity` = −500 with `transaction_type` = `RETURN`
- `unit_price` = NaN
- `transaction_timestamp` in year 2030

---

### 4.5 Franchise B — Hub Master

| Property | Value |
|----------|-------|
| File name | `hubmaster_weekly_refresh.psv` |
| Delimiter | Pipe (`\|`) |
| Delivery | Weekly (every Monday) |
| Delivery method | Full replacement (overwrite) |
| Owner | Franchise B |

| # | Column | Type | Nullable | Description | Example |
|---|--------|------|----------|-------------|---------|
| 1 | `hub_id` | VARCHAR(20) | No | UUID-based hub identifier | `b32488ec` |
| 2 | `hub_name` | TEXT | No | Hub label | `Hub-Jorhat` |
| 3 | `pincode` | VARCHAR(10) | No | 6-digit Indian pincode | `191115` |
| 4 | `latitude` | DECIMAL(9,6) | No | Hub latitude (8.0–35.0) | `11.172174` |
| 5 | `longitude` | DECIMAL(9,6) | No | Hub longitude (68.0–97.0) | `70.98357` |

**Constraints:**
- `hub_id` must be unique across the file
- `latitude` must be within India bounds (8.0–35.0)
- `longitude` must be within India bounds (68.0–97.0)

---

### 4.6 Franchise B — Barcode-SKU Mapping

| Property | Value |
|----------|-------|
| File name | `barcode_sku_mapping.psv` |
| Delimiter | Pipe (`\|`) |
| Delivery | On demand — whenever Franchise B creates new internal barcodes |
| Delivery method | Full replacement (overwrite) |
| Owner | Franchise B |

| # | Column | Type | Nullable | Description | Example |
|---|--------|------|----------|-------------|---------|
| 1 | `item_barcode` | BIGINT | No | Franchise B internal barcode (99x series) | `992514845855` |
| 2 | `sku_code` | VARCHAR(20) | No | FK → product master | `SKU-0001` |
| 3 | `ean_barcode` | BIGINT | No | Manufacturer EAN-13 | `8908830421175` |
| 4 | `variant_label` | VARCHAR(30) | No | Size-Color variant | `40-White` |
| 5 | `is_active` | INT | No | 1 = active, 0 = deprecated | `1` |

**Constraints:**
- `item_barcode` must be unique across the file
- `sku_code` must exist in the product master
- `ean_barcode` must match the corresponding `sku_code` in the product master
- Each `sku_code` can have 1–3 internal barcodes (different warehouse variants)
- `is_active` must be 0 or 1

---

### 4.7 Franchise B — Sales

| Property | Value |
|----------|-------|
| File name | `sales_monthly_YYYY_MM.psv` (seed/historical) or `sales_daily_YYYY_MM_DD.psv` (incremental) |
| Delimiter | Pipe (`\|`) |
| Delivery | Daily (by 01:00 UTC for the previous day) |
| Delivery method | Append (new file per period — never overwrite previous files) |
| Owner | Franchise B |

| # | Column | Type | Nullable | Description | Example |
|---|--------|------|----------|-------------|---------|
| 1 | `order_uuid` | VARCHAR(16) | No | 16-char hex order ID | `bab7ad4787e8a90f` |
| 2 | `hub_id` | VARCHAR(20) | No | FK → hub master | `11403664` |
| 3 | `item_barcode` | BIGINT | No | FK → barcode_sku_mapping | `992360261035` |
| 4 | `units_sold` | INT | No | Units in order (always positive) | `2` |
| 5 | `mrp_price` | DECIMAL(10,2) | No | MRP per unit (₹) | `8454.19` |
| 6 | `discount_applied` | DECIMAL(10,2) | No | Discount per unit (₹) | `261.69` |
| 7 | `delivery_timestamp` | DATETIME | No | Format: `YYYY-MM-DD HH:MM:SS` | `2025-04-02 07:06:22` |
| 8 | `status` | VARCHAR(20) | No | Order status | `DELIVERED` |

**Derived field (calculated by ETL, not in file):**
- `net_price = mrp_price − discount_applied`

**Naming convention:**
- Historical (seed): `sales_monthly_2025_04.psv`
- Incremental: `sales_daily_2026_04_01.psv`

**Constraints:**
- `order_uuid` must be unique within the file
- `item_barcode` must exist in `barcode_sku_mapping.psv` with `is_active = 1`
- `mrp_price` must be > 0
- `discount_applied` must be ≥ 0 and ≤ `mrp_price`
- `delivery_timestamp` must not be in the future
- `status` must be one of: `DELIVERED`, `RETURNED`, `CANCELLED`
- `units_sold` must be > 0

**Known data quality errors (~0.5% of rows):**
- `mrp_price` = 0.00
- Duplicate `order_uuid` within the same file
- `discount_applied` = −1000.00

---

## 5. Delivery Schedule Summary

| Provider | File | Format | Delimiter | Cadence | Method |
|----------|------|--------|-----------|---------|--------|
| Master Company | `product_master.csv` | CSV | `,` | On demand | Overwrite |
| Master Company | `customer_master.csv` | CSV | `,` | On demand | Overwrite |
| Franchise A | `storemaster_monthly_refresh.csv` | CSV | `,` | Monthly | Overwrite |
| Franchise A | `sales_weekly_YYYY_MM_DD.csv` | CSV | `,` | Weekly (Monday) | New file |
| Franchise B | `hubmaster_weekly_refresh.psv` | PSV | `\|` | Weekly (Monday) | Overwrite |
| Franchise B | `barcode_sku_mapping.psv` | PSV | `\|` | On demand | Overwrite |
| Franchise B | `sales_daily_YYYY_MM_DD.psv` | PSV | `\|` | Daily (by 01:00 UTC) | New file |

## 6. Rejection Criteria

A file will be **rejected entirely** (not processed) if:

1. File is empty (0 bytes)
2. Header row is missing or does not match the expected column names exactly
3. Delimiter does not match the expected format (comma for CSV, pipe for PSV)
4. Encoding is not UTF-8 BOM — causes `UnicodeDecodeError`
5. File is placed in the wrong landing zone folder

A file will be **partially processed** (bad rows quarantined) if:

1. Individual rows violate quarantine rules (A1–A4 for Franchise A, B1–B5 for Franchise B)
2. Quarantined rows are logged to the `error_log` table with the rule code and full raw row as JSON
3. Clean rows proceed to `sales_fact` normally

## 7. Change Management

Any change to file format, column names, data types, or delivery schedule must be:

1. Communicated to the Data Engineering team at least **5 business days** in advance
2. Documented as an update to this File Interface Agreement
3. Tested against the ETL pipeline in a staging environment before production deployment
4. Versioned — this document should carry a revision history

## 8. Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2025-04-01 | Data Engineering | Initial version — FY 25-26 launch |
