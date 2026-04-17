# Data Generator

Generates realistic fake retail sales data for an **Indian garment manufacturing company** and its two franchise channels. The manufacturer produces menswear, womenswear, kids wear, ethnic wear, winterwear, and accessories. Optimised for multi-GB output.

- All files are **UTF-8 BOM** encoded (`utf-8-sig`) for Excel compatibility on Windows
- ~15% of customer names, product names, and store names include **Hindi (देवनागरी)** text

## Data Ownership

```
Master Company (Garment Manufacturer)
  ├── product_master.csv      → SKU catalog: garment type, size, color, fabric, batch, MRP, HSN, GST
  └── customer_master.csv     → Loyalty program (IDs, tiers, demographics)

Franchise A (Brick & Mortar Store)
  ├── storemaster              → Physical store locations across India
  └── sales (weekly CSV)       → POS transactions referencing master SKU + loyalty ID

Franchise B (Quick Commerce)
  ├── hubmaster                → Delivery hub locations
  ├── barcode_sku_mapping      → Internal barcode → manufacturer SKU (owned by B)
  └── sales (daily PSV)        → Orders referencing Franchise B's internal barcodes
```

## Files

| File | Purpose |
|---|---|
| `SeedDataGenerator.py` | One-time: creates all masters + 12 monthly sales files per franchise |
| `RefreshDataGenerator.py` | Incremental: reads seed masters, generates weekly/daily sales |
| `requirement.md` | Full data spec — schemas, ownership, errors, volumes |
| `requirements.txt` | Python dependencies |

## Setup

```bash
cd data_generator
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

## Usage

### 1. Seed (run once — must run first)

```bash
python SeedDataGenerator.py
```

Generates:
- **Master company:** `product_master.csv` (10K garment SKUs with size/color/fabric), `customer_master.csv` (5K loyalty customers)
- **Franchise A:** store master + 12 monthly sales CSVs (50M rows total)
- **Franchise B:** hub master + barcode-SKU mapping + 12 monthly sales PSVs (250M rows total)

### 2. Refresh (run on schedule — requires seed masters)

```bash
python RefreshDataGenerator.py
```

Reads `product_master.csv`, `customer_master.csv`, and `barcode_sku_mapping.psv` from the seed output, then generates:
- Franchise A: 1 weekly CSV (7-day window)
- Franchise B: 7 daily PSVs (one per day)

Set `REFRESH_START_DATE` at the top of the file before each run.

> **Important:** `RefreshDataGenerator.py` will fail if seed masters don't exist. Always run seed first.

## Configuration

All tunables are constants at the top of each file.

### Volume & Dates
| Constant | Seed Default | Refresh Default | Description |
|---|---|---|---|
| `ROWS_FRANCHISE_A` | 50,000,000 | 500,000 | Total / base row count |
| `ROWS_FRANCHISE_B` | 250,000,000 | 150,000/day | Total / base row count |
| `ROWS_VARIANCE_PCT` | 30 | 30 | ±% randomisation per file |
| `MASTER_SKU_COUNT` | 10,000 | — | Garment SKUs in catalog |
| `LOYALTY_CUSTOMER_COUNT` | 5,000 | — | Customers in loyalty program |

### Data Quality
| Constant | Default | Description |
|---|---|---|
| `LOYALTY_BLANK_MAX_PCT` | 0.21 | Max 21% of customer IDs blank |
| `LOYALTY_VARIANCE_PCT` | 20–100 | Blank rate swing below max per chunk |
| `ERROR_PCT` | 0.005 | ~0.5% rows get injected errors |
| `HINDI_PCT` | 0.15 | ~15% of names/labels in Hindi (Devanagari) |

### Performance
| Constant | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | 500,000 | Rows per chunk — controls peak memory (~200 MB) |
| `MAX_WORKERS` | cpu_count - 1 | Parallel processes for file generation |

## Output

```
storage/landing_zone/
├── master_company/
│   ├── product_master.csv          ← garment SKU catalog (size, color, fabric)
│   └── customer_master.csv         ← loyalty customer database
├── franchise_a/
│   ├── storemaster_monthly_refresh.csv
│   ├── sales_monthly_2025_04.csv   ← seed (one per month)
│   ├── ...
│   └── sales_weekly_2026_04_07.csv ← refresh
└── franchise_b/
    ├── hubmaster_weekly_refresh.psv
    ├── barcode_sku_mapping.psv     ← internal barcode → SKU mapping
    ├── sales_monthly_2025_04.psv   ← seed (one per month)
    ├── ...
    ├── sales_daily_2026_04_07.psv  ← refresh (one per day)
    └── ...
```

## Product Taxonomy

| Category | Sub-categories |
|---|---|
| Menswear | Formal Shirt, Casual Shirt, T-Shirt, Polo, Jeans, Trousers, Chinos, Shorts, Blazer, Jacket |
| Womenswear | Kurti, Salwar Set, Saree, Blouse, Leggings, Palazzo, Top, Dress, Skirt, Jumpsuit |
| Kids | Kids T-Shirt, Kids Jeans, Kids Dress, Kids Shorts, Kids Ethnic Set |
| Ethnic Wear | Kurta Pajama, Sherwani, Nehru Jacket, Dhoti, Lehenga, Anarkali, Churidar Set |
| Winterwear | Sweater, Hoodie, Cardigan, Thermal, Puffer Jacket, Shawl |
| Accessories | Belt, Wallet, Scarf, Tie, Pocket Square, Cap, Socks |

## Future Scope

- **Franchise C — International E-Commerce:** Tie-up with Amazon or similar marketplace for India + international sales (multi-currency, global shipping)
- **Franchise D — Own E-Commerce Store:** Company's direct-to-consumer website with worldwide delivery, own payment gateway, separate customer accounts

## Schemas

See [requirement.md](requirement.md) for full column definitions, data ownership, error categories, and business rules.
