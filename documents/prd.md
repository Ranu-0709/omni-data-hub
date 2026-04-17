# Product Requirement Document (PRD): Omni Data Hub

## 1. Product Vision
Omni Data Hub empowers an Indian garment manufacturing company to make split-second decisions by unifying fragmented, multi-franchise sales data — from brick-and-mortar stores to quick-commerce hubs — into a single, lightning-fast visual dashboard. The platform handles garment-specific analytics (size, color, fabric, category) and supports multilingual data (English + Hindi).

## 2. Target Personas
We are building this product for two very different types of users:

* **Persona 1: The Executive (The Consumer)**
  * **Role:** CEO, Regional Manager, or Franchise Owner.
  * **Needs:** Needs to see the bottom line instantly. Wants garment-level insights — which sizes sell best, which colors are trending, which categories drive returns. Does not care about how the data gets there. Needs a mobile-friendly, high-speed interface that never crashes.
  * **Workspace:** The Public Showroom (Hosted on Vercel).

* **Persona 2: The Data Admin (The Operator)**
  * **Role:** Data Engineer, System Administrator.
  * **Needs:** Needs deep visibility into system health, ingestion pipelines, and data quality issues. Needs to see the raw, messy data (including Hindi text) to fix errors. Must verify barcode-to-SKU mappings and product master integrity.
  * **Workspace:** The Control Room (Hosted on GCP).

## 3. User Stories
### For the Executive:
* **US-01:** As an Executive, I want to see a leaderboard of the "Top 10 Cities" by revenue so I can reward high-performing regions.
* **US-02:** As an Executive, I want to see a "Live Returns" gauge so I can spot defective product batches immediately.
* **US-03:** As an Executive, I want the dashboard to load in under 2 seconds on my phone, regardless of how much data is processing in the background.
* **US-04:** As an Executive, I want to see sales breakdown by **garment category** (Menswear, Womenswear, Kids, Ethnic Wear, Winterwear, Accessories) to understand channel mix.
* **US-05:** As an Executive, I want to see **top-selling sizes and colors** per category so I can guide production planning.
* **US-06:** As an Executive, I want to compare **Franchise A (store) vs Franchise B (quick-commerce)** performance side-by-side to evaluate channel strategy.

### For the Data Admin:
* **US-07:** As an Admin, I want to see an "Ingestion Health" chart showing the success or failure of daily Airflow jobs.
* **US-08:** As an Admin, I want an "Anomaly Quarantine" table that flags impossible data (e.g., year 2030 dates, ₹0 prices, -500 return quantities, negative discounts, duplicate order UUIDs).
* **US-09:** As an Admin, I want to view the raw barcode-SKU mapping to ensure Franchise B's internal barcodes are correctly translating to the manufacturer's SKU codes.
* **US-10:** As an Admin, I want to verify that product master attributes (size, color, fabric) are correctly joined to sales records after enrichment.
* **US-11:** As an Admin, I want to see which files contained Hindi text and verify they were ingested without encoding corruption.

## 4. Core Features & Requirements

### Feature 1: The Executive Dashboard (Vercel)
* **Read-Only Access:** Users cannot edit or delete data from this interface.
* **Aggregated Views:** Connects only to the Vercel Postgres summary tables, never the raw GCP database.
* **Key Visuals:**
  * Total Revenue (Current Week vs Last Week).
  * Bar Chart: Top 10 Hubs/Stores by revenue.
  * Pie Chart: Sales vs Returns by franchise.
  * Heatmap: Sales by Category × City.
  * Treemap: Revenue by Brand → Category → Sub-category.
  * Bar Chart: Top 5 Sizes and Top 5 Colors by units sold.
  * Loyalty vs Walk-in: Revenue split for Franchise A (loyalty customers vs blank customer_id).

### Feature 2: The Admin Dashboard (GCP)
* **Direct Database Connection:** Connects directly to the massive GCP PostgreSQL warehouse.
* **Key Visuals:**
  * System Uptime and Airflow Job Status.
  * Quarantine Feed: A live scrolling list of flagged transactions requiring manual review.
  * Raw Data Explorer: A search bar to look up specific `order_uuids`, `invoice_numbers`, or `sku_codes` to trace bugs.
  * Barcode Mapping Viewer: Browse `barcode_sku_mapping.psv` with search by `item_barcode` or `sku_code`.
  * Product Master Viewer: Browse product catalog with filters by category, brand, size, color, fabric.
  * File Ingestion Log: Shows each ingested file, row count, error count, encoding, and processing time.

### Feature 3: Flexible Data Ingestion (Backend Engine)
* **Format Agnostic:** The system must automatically detect and process Comma-Separated (`.csv`) and Pipe-Separated (`.psv`) files.
* **Encoding Aware:** Must handle UTF-8 BOM (`utf-8-sig`) encoded files with Hindi (Devanagari) text without corruption.
* **Automated Enrichment:** The system must:
  * Stamp incoming rows with the correct Franchise ID.
  * Convert all timestamps to a standardized UTC format.
  * Join Franchise A sales with product master via `sku_code` to attach size/color/fabric/category.
  * Join Franchise B sales with `barcode_sku_mapping` via `item_barcode`, then with product master via `sku_code` to attach garment attributes.
  * Calculate net price for Franchise B: `net_price = mrp_price - discount_applied`.

### Feature 4: The Quarantine Engine (Data Quality)
The Airflow pipeline must feature a validation step before pushing to the main database.

**Franchise A Rules:**
* **Rule A1:** `unit_price` must not be NaN or ≤ 0.
* **Rule A2:** `quantity` must be reasonable (flag if abs(quantity) > 100 for a single line item).
* **Rule A3:** `transaction_timestamp` cannot be in the future.
* **Rule A4:** `sku_code` must exist in the product master.

**Franchise B Rules:**
* **Rule B1:** `mrp_price` must be > 0.
* **Rule B2:** `discount_applied` cannot be negative or greater than `mrp_price`.
* **Rule B3:** `delivery_timestamp` cannot be in the future.
* **Rule B4:** `order_uuid` must be unique within the file.
* **Rule B5:** `item_barcode` must exist in `barcode_sku_mapping.psv` and be marked `is_active = 1`.

**Action:** If a row violates any rule, it is diverted to an `error_log` table with the rule code and removed from the main sales calculation.

## 5. Data Model
The data warehouse uses a **Star Schema** to optimize dashboard speed.

### Fact Table: `sales_fact`
Unified sales from both franchises after transformation and enrichment.

| Column | Source |
|---|---|
| franchise_id | Stamped during ingestion (A or B) |
| transaction_date | Normalized timestamp |
| sku_code | Direct (A) or via barcode mapping (B) |
| store_or_hub_id | store_code (A) or hub_id (B) |
| quantity / units_sold | Unified |
| selling_price | unit_price (A) or mrp_price - discount (B) |
| customer_id | From sales (A) or NULL (B) |
| status | SALE/RETURN (A) or DELIVERED/RETURNED/CANCELLED (B) |

### Dimension Tables
* `dim_product` — from product master (sku_code, brand, category, sub_category, size, color, fabric)
* `dim_store` — from store master (store_code, store_name, city, state)
* `dim_hub` — from hub master (hub_id, hub_name, pincode, lat, lon)
* `dim_customer` — from customer master (customer_id, name, city, tier)
* `dim_date` — calendar dimension

## 6. UI/UX Guidelines
* **Framework:** Next.js with React components.
* **Styling:** Clean, minimalist corporate design. 
* **Color Palette:**
  * Executive Dashboard: Brand colors, high-contrast charts, focus on positive (green) and negative (red) indicators.
  * Admin Dashboard: Dark mode preferred to reduce eye strain, technical aesthetic, clear warning labels (yellow/orange).
* **Encoding:** All text rendering must support Devanagari (Hindi) characters in names, product labels, and store names.

## 7. Out of Scope (Future Versions)

### Version 2.0 — Franchise C (International E-Commerce)
* Tie-up with Amazon or similar marketplace for India + international sales.
* Multi-currency support (INR, USD, EUR, GBP).
* International shipping addresses, customs/duty fields.
* Marketplace-specific order IDs and fulfillment center codes.

### Version 2.1 — Franchise D (Own E-Commerce Store)
* Company's direct-to-consumer (D2C) website with worldwide delivery.
* Own payment gateway transaction IDs.
* Customer accounts separate from loyalty program (with optional linking).

### Version 3.0 — Advanced Analytics
* Predictive ML for inventory forecasting by size/color/region.
* Automated email reports to franchise owners.
* Seasonal trend analysis (festive season spikes, winter collection performance).
