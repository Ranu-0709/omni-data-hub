# Frontend — Requirements

## Overview

The Executive Dashboard is a **read-only**, public-facing Next.js application hosted on **Vercel**. It provides garment sales analytics for the manufacturing company's leadership — revenue, returns, category performance, size/color trends, and franchise comparison.

This frontend is **self-contained** — it uses its own Vercel Postgres database with pre-aggregated summary tables. It does NOT connect to the main GCP data warehouse.

> **Phase 1 (current):** Seed the Vercel Postgres with summary data via SQL scripts or a seed script.
> **Phase 2 (future):** Automated data push from the GCP pipeline to Vercel Postgres via API or direct sync.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│                   Vercel                     │
│                                             │
│   Next.js App (App Router)                  │
│   ├── Dashboard Pages (SSR / RSC)           │
│   ├── API Routes (/api/*)                   │
│   └── Vercel Postgres (summary tables only) │
│                                             │
│   ← Read-only, no write from UI             │
│   ← < 2 second page load target             │
└─────────────────────────────────────────────┘
         ▲
         │ Phase 2: automated sync
         │
┌────────┴────────┐
│  GCP Pipeline    │
│  (out of scope)  │
└─────────────────┘
```

---

## Database Schema (Vercel Postgres)

Summary/aggregated tables only — no raw transaction rows.

### `summary_revenue_daily`
Pre-aggregated daily revenue by franchise, city, and category.

| Column | Type | Description |
|---|---|---|
| id | serial | PK |
| date | date | Transaction date |
| franchise_id | varchar(1) | `A` or `B` |
| city | varchar(50) | City name |
| state | varchar(5) | State code |
| category | varchar(30) | Menswear, Womenswear, Kids, etc. |
| sub_category | varchar(50) | Formal Shirt, Kurti, Jeans, etc. |
| brand | varchar(50) | Brand label |
| total_revenue | decimal(15,2) | Sum of selling price × quantity |
| total_units | int | Sum of units sold |
| total_returns | int | Count of returned units |
| return_revenue | decimal(15,2) | Revenue lost to returns |

### `summary_top_products`
Top-selling products by size, color, and fabric.

| Column | Type | Description |
|---|---|---|
| id | serial | PK |
| period | varchar(10) | `weekly` or `monthly` |
| period_start | date | Start of period |
| sku_code | varchar(20) | Product SKU |
| product_name | varchar(100) | Product name (may contain Hindi) |
| brand | varchar(50) | Brand |
| category | varchar(30) | Category |
| size | varchar(10) | Size |
| color | varchar(20) | Color |
| fabric | varchar(30) | Fabric |
| units_sold | int | Total units |
| revenue | decimal(15,2) | Total revenue |

### `summary_store_hub`
Store and hub performance rankings.

| Column | Type | Description |
|---|---|---|
| id | serial | PK |
| date | date | Transaction date |
| franchise_id | varchar(1) | `A` or `B` |
| location_code | varchar(20) | store_code or hub_id |
| location_name | varchar(100) | Store/hub name (may contain Hindi) |
| city | varchar(50) | City |
| total_revenue | decimal(15,2) | Daily revenue |
| total_units | int | Daily units |
| total_returns | int | Daily returns |

### `summary_loyalty`
Loyalty vs walk-in split for Franchise A.

| Column | Type | Description |
|---|---|---|
| id | serial | PK |
| date | date | Transaction date |
| loyalty_tier | varchar(10) | Bronze, Silver, Gold, Platinum, or `Walk-in` |
| total_revenue | decimal(15,2) | Revenue |
| total_units | int | Units |
| customer_count | int | Distinct customers |

### `meta_last_sync`
Tracks when data was last pushed from GCP (Phase 2).

| Column | Type | Description |
|---|---|---|
| id | serial | PK |
| synced_at | timestamp | Last sync timestamp |
| source | varchar(20) | `seed` or `pipeline` |
| rows_synced | int | Total rows pushed |

---

## Pages

### Page 1: Overview (`/`)
The main landing page — high-level KPIs and trends.

| Component | Data Source | Description |
|---|---|---|
| Revenue Cards | `summary_revenue_daily` | Total revenue this week, last week, % change. Separate cards for Franchise A and B |
| Revenue Trend | `summary_revenue_daily` | Line chart — daily revenue over last 30 days, one line per franchise |
| Sales vs Returns | `summary_revenue_daily` | Pie/donut chart — total sales vs total returns (units) |
| Last Synced | `meta_last_sync` | Footer badge showing when data was last updated |

### Page 2: Category Analytics (`/categories`)
Garment category deep-dive.

| Component | Data Source | Description |
|---|---|---|
| Category Revenue | `summary_revenue_daily` | Horizontal bar chart — revenue by category (Menswear, Womenswear, etc.) |
| Category Returns | `summary_revenue_daily` | Vertical stacked bar — returns by category, split by Franchise A and B |
| Brand Revenue | `summary_revenue_daily` | Horizontal bar chart — top 30 brands by revenue |

### Page 3: Size & Color Trends (`/trends`)
Production planning insights.

| Component | Data Source | Description |
|---|---|---|
| Top 10 Sizes | `summary_top_products` | Horizontal bar — top 10 sizes by units sold |
| Top 10 Colors | `summary_top_products` | Horizontal bar — top 10 colors by units sold |
| Fabric Mix | `summary_top_products` | Donut chart — revenue share by fabric type |

### Page 4: Location Leaderboard (`/locations`)
Store and hub performance.

| Component | Data Source | Description |
|---|---|---|
| Top 10 Stores | `summary_store_hub` | Bar chart — top 10 Franchise A stores by revenue |
| Top 10 Hubs | `summary_store_hub` | Bar chart — top 10 Franchise B hubs by revenue |
| City Leaderboard | `summary_revenue_daily` | Table — top 10 cities by revenue, with units and return rate |
| Franchise Comparison | `summary_revenue_daily` | Side-by-side cards — A vs B total revenue, units, return rate |

### Page 5: Loyalty Insights (`/loyalty`)
Franchise A loyalty program analysis.

| Component | Data Source | Description |
|---|---|---|
| Loyalty vs Walk-in | `summary_loyalty` | Donut chart — revenue split |
| Tier Breakdown | `summary_loyalty` | Stacked bar — revenue by tier (Bronze, Silver, Gold, Platinum) |
| Loyalty Trend | `summary_loyalty` | Line chart — loyalty vs walk-in revenue over last 30 days |

---

## API Routes

All API routes are read-only `GET` endpoints. They query Vercel Postgres and return JSON.

| Route | Description |
|---|---|
| `GET /api/overview` | Revenue KPIs, weekly comparison, sales vs returns |
| `GET /api/categories?period=weekly` | Category revenue, returns, brand breakdown |
| `GET /api/trends?period=monthly` | Top sizes, colors, fabrics |
| `GET /api/locations?franchise=A&limit=10` | Top stores/hubs by revenue |
| `GET /api/loyalty?days=30` | Loyalty tier breakdown and trend |
| `GET /api/meta` | Last sync timestamp and row count |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS + next-themes (dark/light mode) |
| Charts | Recharts |
| Database | Vercel Postgres (@vercel/postgres) |
| Hosting | Vercel (auto-deploy from `frontend/` folder in monorepo) |
| Font | Noto Sans + Noto Sans Devanagari (for Hindi text support) |
| Theme | next-themes — user toggle, persisted in localStorage, respects OS preference |

---

## Non-Functional Requirements

| Requirement | Target |
|---|---|
| Page load | < 2 seconds (Lighthouse performance > 90) |
| Mobile responsive | All pages must work on 375px+ screens |
| Read-only | No write operations from the UI |
| Unicode | Must render Hindi (Devanagari) text in names and labels |
| Theme | User-selectable dark/light mode, persisted in localStorage |
| Accessibility | WCAG 2.1 AA compliant |
| SEO | Not required (internal dashboard) |

---

## Phasing

### Phase 1 (Current) — Static Seed
- Create Vercel Postgres schema (summary tables)
- Seed database with sample aggregated data via `npm run db:seed`
- Build all 5 dashboard pages with charts
- Deploy to Vercel

### Phase 2 (Future) — Automated Sync
- GCP Airflow pipeline pushes aggregated data to Vercel Postgres via API or direct connection
- `meta_last_sync` table updated on each push
- Dashboard shows live data with "Last updated" badge

---

## Out of Scope (This Project)
- Raw transaction data browsing (that's the Admin Dashboard on GCP)
- Data ingestion or ETL
- User authentication (public read-only dashboard)
- Write/edit/delete operations
- Admin features (quarantine, barcode mapping viewer)
