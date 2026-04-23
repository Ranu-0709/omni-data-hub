# Notebooks — Exploratory Data Analysis

## Overview
This folder contains Jupyter notebooks that profile, validate, and visualise the raw landing-zone data **before** it enters the Airflow ETL pipeline.

| Notebook | Franchise | Data Format | Focus |
|----------|-----------|-------------|-------|
| `eda_franchise_a.ipynb` | A — Brick-and-mortar stores | CSV (`,`) | Sales, loyalty vs walk-in, returns (negative qty) |
| `eda_franchise_b.ipynb` | B — Quick-commerce hubs | PSV (`\|`) | Barcode→SKU mapping, net price, order statuses |

## Prerequisites

```
pip install pandas numpy matplotlib seaborn
```

Jupyter (or VS Code notebook support) is required to run the `.ipynb` files.

## Data Dependency
Both notebooks read from `data_generator/storage/landing_zone/` using relative paths.  
If the folder is empty, generate seed data first:

```bash
cd data_generator
pip install -r requirements.txt
python SeedDataGenerator.py
```

## How to Run

```bash
cd notebooks
jupyter notebook
```

Open either notebook and **Run All**.

## Quarantine Rules Tested

### Franchise A
| Rule | Check |
|------|-------|
| A1 | `unit_price` is not NaN and > 0 |
| A2 | `abs(quantity)` ≤ 100 |
| A3 | `transaction_timestamp` is not in the future |
| A4 | `sku_code` exists in product master |

### Franchise B
| Rule | Check |
|------|-------|
| B1 | `mrp_price` > 0 |
| B2 | `discount_applied` ≥ 0 and ≤ `mrp_price` |
| B3 | `delivery_timestamp` is not in the future |
| B4 | `order_uuid` is unique |
| B5 | `item_barcode` exists in mapping with `is_active = 1` |

## Notes
- All source files use **UTF-8 BOM** (`utf-8-sig`) encoding to support Hindi (Devanagari) text.
- ~0.5% of rows contain **deliberate data-quality errors** injected by the seed generator for pipeline testing.
- Row counts vary between runs due to ±10% jitter in the generator.
