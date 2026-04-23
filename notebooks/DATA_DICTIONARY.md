# Data Dictionary

Single reference for every file and column used by the EDA notebooks.  
Source: `data_generator/storage/landing_zone/`

---

## Master Company

### product_master.csv

| Column | Type | Description |
|--------|------|-------------|
| sku_code | string | Manufacturer SKU (e.g. `SKU-0001`) |
| ean_barcode | int64 | EAN-13 barcode (890x series) |
| product_name | string | Brand + sub-category (may contain Hindi) |
| brand | string | One of 15 brand labels |
| category | string | Menswear, Womenswear, Kids, Ethnic Wear, Winterwear, Accessories |
| sub_category | string | Specific garment type (e.g. Formal Shirt, Kurti) |
| size | string | XS–3XL, 28–42, or Free Size |
| color | string | 18 possible colors |
| fabric | string | 16 possible fabrics |
| batch_code | string | Manufacturing batch (e.g. `B2410-895`) |
| manufacturing_date | date | YYYY-MM-DD |
| mrp | float | Maximum retail price (₹) |
| hsn_code | int | HSN code for GST classification |
| gst_pct | int | GST slab — 5% or 12% |

### customer_master.csv

| Column | Type | Description |
|--------|------|-------------|
| customer_id | string | Loyalty ID (e.g. `LOYAL-0001`) |
| customer_name | string | Full name (may contain Hindi) |
| phone | string | Indian phone number |
| email | string | Email address |
| city | string | Indian city |
| state | string | State code (e.g. KA, MH) |
| loyalty_tier | string | Bronze / Silver / Gold / Platinum |
| join_date | date | YYYY-MM-DD |

---

## Franchise A — Brick-and-Mortar Stores

### storemaster_monthly_refresh.csv

| Column | Type | Description |
|--------|------|-------------|
| store_code | string | Store ID (e.g. `FA-001`) |
| store_name | string | Store name (may contain Hindi) |
| city | string | Indian city |
| state | string | State code |

### sales_monthly_YYYY_MM.csv / sales_weekly_YYYY_MM_DD.csv

| Column | Type | Description |
|--------|------|-------------|
| invoice_number | string | Invoice ID (e.g. `INV-71064`) |
| store_code | string | FK → store master |
| transaction_timestamp | datetime | Sale/return timestamp |
| sku_code | string | FK → product master |
| quantity | int | Units sold (negative = return) |
| unit_price | float | Selling price per unit (₹) |
| transaction_type | string | `SALE` or `RETURN` |
| customer_id | string | FK → customer master (blank = walk-in) |

**Known injected errors:** qty = −500, unit_price = NaN, timestamp in year 2030.

---

## Franchise B — Quick Commerce / Dark Stores

### hubmaster_weekly_refresh.psv

| Column | Type | Description |
|--------|------|-------------|
| hub_id | string | UUID-based hub ID |
| hub_name | string | Hub label (e.g. `Hub-Bengaluru`) |
| pincode | string | 6-digit Indian pincode |
| latitude | float | Hub latitude |
| longitude | float | Hub longitude |

### barcode_sku_mapping.psv

| Column | Type | Description |
|--------|------|-------------|
| item_barcode | int64 | Franchise B internal barcode (99x series) |
| sku_code | string | FK → product master |
| ean_barcode | int64 | Manufacturer EAN-13 |
| variant_label | string | Size-Color variant (e.g. `40-White`) |
| is_active | int | 1 = active, 0 = deprecated |

Each SKU can have 1–3 internal barcodes (different warehouse variants).

### sales_monthly_YYYY_MM.psv / sales_daily_YYYY_MM_DD.psv

| Column | Type | Description |
|--------|------|-------------|
| order_uuid | string | 16-char hex order ID |
| hub_id | string | FK → hub master |
| item_barcode | int64 | FK → barcode_sku_mapping |
| units_sold | int | Units in order |
| mrp_price | float | MRP per unit (₹) |
| discount_applied | float | Discount per unit (₹) |
| delivery_timestamp | datetime | Delivery/attempt timestamp |
| status | string | DELIVERED / RETURNED / CANCELLED |

**Derived field:** `net_price = mrp_price − discount_applied`

**Known injected errors:** mrp_price = 0, duplicate order_uuid, discount_applied = −1000.
