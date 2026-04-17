# Business Requirement Document: Omni Data Hub

## 1. Executive Summary
Omni Data Hub is a centralized data engineering platform designed to collect, clean, and visualize retail sales data from an **Indian garment manufacturing company** and its diverse franchise networks. The manufacturer produces menswear, womenswear, kids wear, ethnic wear, winterwear, and accessories across 15 brand labels and 10,000+ SKUs.

The manufacturer struggles to see a unified view of sales when different franchise channels use different software, different file formats, different product codes, and even different languages (English and Hindi). 

Omni Data Hub acts as a universal translator. It takes messy, scattered data from traditional brick-and-mortar garment stores and modern quick-commerce delivery hubs, standardizes it, and feeds it into lightning-fast dashboards.

## 2. Project Objectives
* **Unified Visibility:** Provide a single source of truth for all franchise sales across the garment manufacturer's channels.
* **Automated Ingestion:** Replace manual Excel reporting with automated Python and Airflow pipelines.
* **Data Normalization:** Translate Franchise B's internal warehouse barcodes into the manufacturer's master SKU codes using the barcode-SKU mapping.
* **Product Intelligence:** Enable analytics by garment attributes — size, color, fabric, category — using the manufacturer's product master.
* **Scalable Architecture:** Build a system capable of processing gigabytes of raw data (1–2 GB per monthly file) without crashing the public-facing dashboards.

## 3. System Architecture
The system uses a decoupled architecture to ensure safety and performance. We use the "Kitchen and Dining Room" model.

* **The Engine Room (GCP):** A powerful Google Cloud Ubuntu server runs PostgreSQL, Apache Airflow, and the Python data processing scripts via Docker.
* **The Workspace:** Developers access the server using a lightweight `code-server` instance accessed through a web browser.
* **The Control Room (GCP Frontend):** An admin Next.js dashboard runs directly on the cloud server to monitor the massive raw database and data anomalies.
* **The Public Showroom (Vercel Frontend):** A fast, read-only Next.js dashboard is hosted on Vercel. It connects to a lightweight Vercel Postgres database that only holds summary data. 
* **Version Control:** All code is managed in a single GitHub Monorepo. Vercel automatically builds updates when code is pushed to the `frontend` folder.

## 4. Data Sources

### 4.0 Master Company (Garment Manufacturer)
The manufacturer owns and maintains the core reference data shared downstream to all franchises.

* **Product Master (`product_master.csv`):** 10,000 garment SKUs with EAN barcodes, brand, category, sub-category, size, color, fabric, batch code, MRP, HSN code, and GST slab.
* **Customer Master (`customer_master.csv`):** 5,000 loyalty program members with demographics, tier (Bronze/Silver/Gold/Platinum), and join date.
* **Format:** Comma-Separated Values (.csv), UTF-8 BOM encoded
* **Multilingual:** ~15% of product names and customer names include Hindi (Devanagari) text alongside English — reflecting real Indian retail data.

### 4.1 Franchise A (Brick-and-Mortar Garment Stores)
* **Format:** Comma-Separated Values (.csv), UTF-8 BOM encoded
* **Sales Frequency:** Weekly uploads (one file per week)
* **Master Data Frequency:** Monthly store master updates
* **Key Traits:** Uses the manufacturer's SKU codes directly from product master. References the manufacturer's loyalty customer IDs (up to 21% of transactions have no loyalty ID — walk-in customers). Tracks returns using negative quantities in the same sales column. ~15% of store names are in Hindi.

### 4.2 Franchise B (Quick Commerce / Dark Stores)
* **Format:** Pipe-Separated Values (`.psv` extension, `|` delimiter), UTF-8 BOM encoded
* **Sales Frequency:** Daily uploads (one file per day)
* **Master Data Frequency:** Weekly hub master updates
* **Key Traits:** Uses internal warehouse barcodes (not the manufacturer's SKU codes). Franchise B owns and maintains a **barcode-SKU mapping file** (`barcode_sku_mapping.psv`) that maps their internal barcodes back to the manufacturer's SKU and EAN codes. Each SKU can have 1–3 internal barcodes (different size-color variants in warehouse). Uses UUIDs for orders. Anonymous buyers (no customer IDs). Final price is calculated dynamically (MRP minus discount). Order statuses include DELIVERED, RETURNED, and CANCELLED.

## 5. Functional Requirements
* **Data Ingestion:** The system must automatically detect new files dropped into isolated Google Cloud Storage folders — separate folders for `master_company/`, `franchise_a/`, and `franchise_b/`.
* **Data Transformation:** The pipeline must convert pipe-separated `.psv` files to standard formats, calculate net prices (MRP minus discount), and map Franchise B's internal barcodes to the manufacturer's SKU codes using the barcode-SKU mapping.
* **Product Enrichment:** The pipeline must join sales data with the product master to attach garment attributes (size, color, fabric, category) for downstream analytics.
* **Error Handling (EDA):** The pipeline must detect and flag bad data:
  * Franchise A: impossible return quantities (qty = -500), missing prices (NaN), future dates (year 2030)
  * Franchise B: zero MRP pricing, duplicate order UUIDs, negative discounts (discount > MRP)
* **Return Processing:** Franchise A returns are recorded as negative quantities. Franchise B returns are recorded as `status = RETURNED`. Both must be normalized into a consistent return model.
* **Unicode Handling:** The pipeline must correctly process Hindi (Devanagari) text in customer names, product names, and store names. All files use UTF-8 BOM encoding.

## 6. Non-Functional Requirements
* **Security:** Franchise owners must only access their specific cloud storage folders using restricted IAM Service Accounts.
* **Performance:** The public Next.js dashboard must load in under two seconds. This is achieved by separating the heavy ingestion database from the lightweight serving database.
* **Scalability:** The system must handle monthly files up to 2 GB (250M+ rows for Franchise B) with chunked processing and parallel execution.
* **Disaster Recovery:** All server infrastructure must be rebuildable using automated bash scripts (`setup_server.sh`) and Docker Compose files stored in GitHub.

## 7. Data Generator
The `data_generator` module produces realistic fake data for development and testing:

* **SeedDataGenerator.py:** One-time historical backfill — generates product master, customer master, store/hub masters, barcode-SKU mapping, and 12 monthly sales files per franchise (FY 25-26). Uses multiprocessing for parallel file generation.
* **RefreshDataGenerator.py:** Incremental refresh — reads seed masters, generates 1 weekly CSV for Franchise A and 7 daily PSVs for Franchise B. Cadence is enforced automatically from a single start date.
* **Data Quality Errors:** ~0.5% of rows contain deliberate errors for EDA pipeline testing.
* **Randomisation:** Row counts per file vary ±30%, loyalty blank rates vary per chunk, ensuring no two runs produce identical data.

## 8. Implementation Phasing
* **Phase 1:** GCP Foundation and Virtual Machine setup.
* **Phase 2:** Cloud Storage isolation and Service Account security (separate folders for master_company, franchise_a, franchise_b).
* **Phase 3:** Remote Workspace configuration (`code-server`).
* **Phase 4:** GitHub Monorepo and directory structure creation.
* **Phase 5:** Infrastructure as Code (Docker Compose and Bash scripts).
* **Phase 6:** Frontend Mockup and Vercel deployment.
* **Phase 7:** Custom Domain routing (`ranu.sudiptabanerjee.com`).
* **Phase 8:** Python Data Generator — seed data backfill + incremental refresh scripts.
* **Phase 9:** Apache Airflow DAG development for automated ETL (ingestion, barcode mapping, product enrichment, quarantine).

## 9. Future Scope
* **Franchise C — International E-Commerce:** Tie-up with Amazon or similar marketplace for India + international sales. Multi-currency support (INR, USD, EUR, GBP), international shipping, marketplace-specific order IDs.
* **Franchise D — Own E-Commerce Store:** Company's direct-to-consumer (D2C) website with worldwide delivery, own payment gateway, separate customer accounts with optional loyalty linking.
* **Predictive Analytics:** ML-based inventory forecasting by size/color/region.
* **Automated Reporting:** Scheduled email reports to franchise owners.
