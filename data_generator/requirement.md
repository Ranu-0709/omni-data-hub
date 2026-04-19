# Data Generator — Requirements

## Overview

Generate realistic fake retail sales data for an **Indian garment manufacturing company** and its two franchise channels. The manufacturer produces shirts, jeans, kurtis, ethnic wear, winterwear, accessories, and more. All data is restricted to India.

---

## Unicode & Multilingual Support

- All CSV/PSV files are written with **UTF-8 BOM** (`utf-8-sig`) encoding for Excel compatibility on Windows
- ~15% of names and labels include **Hindi (Devanagari)** text, controlled by `HINDI_PCT` constant
- Affected fields: `customer_name`, `product_name`, `store_name`
- Examples:
  - Customer: `आदित्य शर्मा`, `प्रिया गुप्ता`
  - Product: `SilkRoute Kurti शानदार`, `DesiDrape Saree राजशाही`
  - Store: `श्री वस्त्र भंडार`, `नया फैशन हाउस`

---

## Data Ownership & Flow

```
┌──────────────────────────────────────────────────────────┐
│         MASTER COMPANY (Garment Manufacturer)             │
│                                                          │
│  Owns: product_master.csv, customer_master.csv           │
│  - Creates SKUs, EAN barcodes, batch codes               │
│  - Defines size/color/fabric per product                 │
│  - Runs the loyalty program (customer IDs, tiers)        │
│  - Shares product catalog downstream to both franchises  │
└──────────────┬───────────────────────┬───────────────────┘
               │                       │
       ┌───────▼────────┐      ┌───────▼────────┐
       │  FRANCHISE A    │      │  FRANCHISE B    │
       │  (Brick &       │      │  (Quick         │
       │   Mortar Store) │      │   Commerce)     │
       │                 │      │                 │
       │  Uses mfg SKU   │      │  Creates own    │
       │  codes directly │      │  item_barcode   │
       │  in POS sales   │      │  for warehouse  │
       │                 │      │  ops, maps back │
       │  Uses mfg       │      │  to mfg SKU via │
       │  loyalty IDs    │      │  barcode_sku_   │
       │  for customers  │      │  mapping.psv    │
       └────────────────┘      └─────────────────┘
```

### Why does Franchise B own the barcode mapping?

In real-world quick-commerce (Myntra Instamart, Ajio Express, etc.):
1. The manufacturer ships garments with EAN barcodes on hang tags / packaging
2. The q-commerce platform creates **internal barcodes** for warehouse bin management, size-color variant tracking, and multi-pack handling
3. One manufacturer SKU can have **multiple internal barcodes** (e.g., same shirt in different warehouse zones, or combo packs)
4. Franchise B maintains and shares the `barcode_sku_mapping` file so the manufacturer can reconcile sales back to their product catalog

The manufacturer does NOT create these internal barcodes — they only know their own EAN/SKU codes.

---

## Master Company (Garment Manufacturer)

### Product Master (`product_master.csv`)
| Column | Type | Description |
|---|---|---|
| sku_code | string | `SKU-nnnn` — manufacturer's product identifier |
| ean_barcode | int | 13-digit EAN barcode (890x series — India) |
| product_name | string | Brand + garment type, ~15% include Hindi tags (e.g., "शानदार") |
| brand | string | One of 15 garment brand labels |
| category | string | Menswear, Womenswear, Kids, Ethnic Wear, Winterwear, Accessories |
| sub_category | string | Specific garment type (Formal Shirt, Kurti, Jeans, etc.) |
| size | string | XS, S, M, L, XL, XXL, 3XL, 28–42, Free Size |
| color | string | Black, Navy, Maroon, Indigo, etc. (18 colors) |
| fabric | string | Cotton, Linen, Denim, Silk, Rayon, etc. (16 fabrics) |
| batch_code | string | `Byymm-nnn` format |
| manufacturing_date | date | Before seed start date |
| mrp | float | Maximum retail price in INR (₹299–₹9,999) |
| hsn_code | int | Garment HSN code (6101–6217 series) |
| gst_pct | int | GST slab: 5% (≤₹1000) or 12% (>₹1000) |

### Customer Master (`customer_master.csv`)
| Column | Type | Description |
|---|---|---|
| customer_id | string | `LOYAL-nnnn` — loyalty program ID |
| customer_name | string | Indian name — English (Faker en_IN) or Hindi (Faker hi_IN, ~15%) |
| phone | string | Indian phone number |
| email | string | Email address |
| city | string | Indian city |
| state | string | State code |
| loyalty_tier | string | Bronze (40%), Silver (30%), Gold (20%), Platinum (10%) |
| join_date | date | 1–3 years before seed start |

---

## Franchise A — Brick-and-mortar garment store

### Store Master (`storemaster_monthly_refresh.csv`)
| Column | Type | Description |
|---|---|---|
| store_code | string | `FA-nnn` |
| store_name | string | Indian company name — English or Hindi (~15%) |
| city | string | Indian city |
| state | string | State code |

### Sales Schema (`sales_weekly_*.csv` / `sales_monthly_*.csv`)
| Column | Type | Description |
|---|---|---|
| invoice_number | string | `INV-nnnnn` |
| store_code | string | References store master |
| transaction_timestamp | datetime | Within file's date window |
| sku_code | string | References **manufacturer's product_master** |
| quantity | int | Positive (sale) or negative (return) |
| unit_price | float | Selling price in INR (₹299–₹9,999) |
| transaction_type | string | `SALE` or `RETURN` |
| customer_id | string | References **manufacturer's customer_master** or blank |

---

## Franchise B — Quick-commerce garment delivery

### Hub Master (`hubmaster_weekly_refresh.psv`)
| Column | Type | Description |
|---|---|---|
| hub_id | string | 8-char hex |
| hub_name | string | `Hub-<CityName>` |
| pincode | string | Indian 6-digit pincode |
| latitude | float | 8.0–35.0 |
| longitude | float | 68.0–97.0 |

### Barcode-SKU Mapping (`barcode_sku_mapping.psv`)
Owned by Franchise B — maps internal barcodes to manufacturer's catalog.

| Column | Type | Description |
|---|---|---|
| item_barcode | int | Franchise B's internal barcode (99-prefixed) |
| sku_code | string | References manufacturer's `sku_code` |
| ean_barcode | int | Manufacturer's EAN barcode (for cross-reference) |
| variant_label | string | Size-Color combo (e.g., "L-Navy", "32-Black") |
| is_active | int | 1 = active, 0 = discontinued (5% inactive) |

One SKU can have 1–3 internal barcodes (different size-color combos in warehouse).

### Sales Schema (`sales_daily_*.psv` / `sales_monthly_*.psv`)
| Column | Type | Description |
|---|---|---|
| order_uuid | string | 16-char random hex |
| hub_id | string | References hub master |
| item_barcode | int | References **Franchise B's barcode_sku_mapping** |
| units_sold | int | 1–3 |
| mrp_price | float | INR (₹299–₹9,999) |
| discount_applied | float | INR (₹0–₹500) |
| delivery_timestamp | datetime | Within file's date window |
| status | string | DELIVERED (85%), RETURNED (10%), CANCELLED (5%) |

---

## Data Quality Errors (Injected for EDA)

~0.5% of rows (`ERROR_PCT`) contain deliberate errors:

### Franchise A Errors
| Error | What happens |
|---|---|
| Excessive returns | `quantity = -500`, `transaction_type = RETURN` |
| Missing prices | `unit_price = NaN` |
| Future dates | `transaction_timestamp = 2030-01-01` |

### Franchise B Errors
| Error | What happens |
|---|---|
| Zero MRP | `mrp_price = 0.00` |
| Duplicate orders | Multiple rows share the same `order_uuid` |
| Negative discount | `discount_applied = -1000.00` |

---

## Volume & Variance

### Seed (one-time historical backfill)
| Parameter | Franchise A | Franchise B |
|---|---|---|
| Total rows | 50,000,000 | 250,000,000 |
| Date range | FY 25-26 (Apr 2025 – Mar 2026) | FY 25-26 (Apr 2025 – Mar 2026) |
| Files | 12 monthly CSVs | 12 monthly PSVs |
| Rows per month | Randomised ±30% | Randomised ±30% |
| Target file size | ~300–600 MB | ~1–2 GB |

### Refresh (incremental, scheduled)
| Parameter | Franchise A | Franchise B |
|---|---|---|
| Base rows | 500,000 per week | 150,000 per day |
| Cadence | 1 weekly file (7 days) | 7 daily files (1 per day) |
| Row variance | ±30% per run | ±30% per file |

### Master Data Volumes

All base counts are jittered ±`RANDOMIZE_PCT` (default 10%) at startup.

| Master | Base Count | Runtime Range |
|---|---|---|
| Products (SKUs) | 10,000 | ~9,000–11,000 |
| Loyalty customers | 5,000 | ~4,500–5,500 |
| Stores (Franchise A) | 10 (seed), +1 per refresh | ~9–11 |
| Hubs (Franchise B) | 500 (seed), +2 per refresh | ~450–550 |
| Barcode mappings | ~15,000–30,000 (1–3 per SKU) | Scales with SKU count |

### Randomisation Controls
| Constant | Purpose | Default |
|---|---|---|
| `ROWS_VARIANCE_PCT` | ±% variance in row count per file | 30 |
| `RANDOMIZE_PCT` | ±% jitter on base counts per run | 10 |
| `LOYALTY_BLANK_MAX_PCT` | Max % of blank customer IDs | 0.21 |
| `LOYALTY_VARIANCE_PCT` | How much blank rate swings below max | 20–100 |
| `ERROR_PCT` | Fraction of rows with injected errors | 0.005 |
| `HINDI_PCT` | Fraction of names/labels in Hindi (Devanagari) | 0.15 |

---

## Output Structure

```
storage/landing_zone/
├── master_company/
│   ├── product_master.csv
│   └── customer_master.csv
├── franchise_a/
│   ├── storemaster_monthly_refresh.csv
│   ├── sales_monthly_2025_04.csv          ← seed
│   ├── ...
│   └── sales_weekly_2026_04_07.csv        ← refresh
└── franchise_b/
    ├── hubmaster_weekly_refresh.psv
    ├── barcode_sku_mapping.psv
    ├── sales_monthly_2025_04.psv          ← seed
    ├── ...
    ├── sales_daily_2026_04_07.psv         ← refresh
    └── ...
```

---

## Future Scope (To Do)

### Franchise C — International E-Commerce (e.g., Amazon)
- Tie-up with Amazon or similar marketplace
- Sells both in India and internationally
- Multi-currency support (INR, USD, EUR, GBP)
- International shipping addresses, customs/duty fields
- Amazon-specific order IDs, fulfillment center codes
- Separate product listings with marketplace-specific pricing

### Franchise D — Company's Own E-Commerce Store
- Direct-to-consumer (D2C) worldwide delivery
- Company-owned website orders
- Global shipping with tracking
- Multi-currency checkout
- Own payment gateway transaction IDs
- Customer accounts separate from loyalty program (with optional linking)
