# Frontend — Executive Dashboard

Read-only public dashboard for the garment manufacturing company's leadership. Hosted on **Vercel** with its own **Vercel Postgres** database containing pre-aggregated summary data.

- Live revenue tracking across Franchise A (stores) and Franchise B (quick-commerce)
- Garment analytics — category, size, color, fabric breakdowns
- Location leaderboards — top stores, hubs, cities
- Loyalty program insights — tier performance, walk-in vs loyalty split
- Hindi (देवनागरी) text support in names and labels

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS + next-themes (dark/light mode) |
| Charts | Recharts |
| Database | Vercel Postgres (used for both local dev and production) |
| Hosting | Vercel (auto-deploy from `frontend/` folder via GitHub) |

## Prerequisites

- Node.js 18+
- npm
- GitHub account (repo must be pushed to GitHub)
- Vercel account (free tier works)

---

## Setup — Vercel Account & GitHub CI/CD

The full `omni-data-hub` monorepo lives on GitHub. Vercel only builds and deploys the `frontend/` directory.

### Step 1: Push monorepo to GitHub

```bash
cd omni-data-hub
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/Ranu-0709/omni-data-hub.git
git push -u origin main
```

### Step 2: Create Vercel account

1. Go to [vercel.com](https://vercel.com) and sign up with your **GitHub account**
2. This links your GitHub repos to Vercel automatically

### Step 3: Import project in Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **Import Git Repository**
3. Select the `omni-data-hub` repo
4. **Configure the project:**

#making update in readme

| Setting | Value |
|---|---|
| Framework Preset | Next.js |
| Root Directory | `frontend` |
| Build Command | `next build` |
| Output Directory | `.next` |
| Install Command | `npm install` |

5. Click **Deploy**

> Vercel will now auto-deploy every time you push to `main`. It only watches the `frontend/` directory — changes to `data_generator/`, `pipeline/`, etc. won't trigger a build.

### Step 4: Create Vercel Postgres database

1. In Vercel Dashboard → your project → **Storage** tab
2. Click **Create Database** → select **Postgres**
3. Choose a name (e.g., `omni-dashboard-db`) and region (closest to your users)
4. Click **Create**
5. Vercel automatically adds the connection env vars to your project:
   - `POSTGRES_URL`
   - `POSTGRES_PRISMA_URL`
   - `POSTGRES_URL_NON_POOLING`
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`
   - `POSTGRES_HOST`
   - `POSTGRES_DATABASE`

### Step 5: Pull env vars for local development

Install Vercel CLI if you haven't:

```bash
npm i -g vercel
```

Link your local project and pull the env vars:

```bash
cd frontend
vercel link
vercel env pull .env.local
```

This creates `.env.local` with the Postgres connection strings. This file is gitignored — never commit it.

> **Local dev connects to the same Vercel Postgres** — no local database needed.

### Step 6: Create database tables

```bash
npm run db:setup
```

Runs `scripts/setup-db.ts` against Vercel Postgres to create the summary tables.

### Step 7: Seed sample data

```bash
npm run db:seed
```

Populates summary tables with sample aggregated data for development.

### Step 8: Run locally

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## GitHub CI/CD Flow

```
GitHub Push (main branch)
    │
    ▼
Vercel detects change in frontend/ directory
    │
    ▼
Vercel runs: npm install → next build
    │
    ▼
Deploys to production URL
    │
    ▼
Preview deployments for PRs (automatic)
```

- **Production deploys:** Push to `main` → auto-deploys to production URL
- **Preview deploys:** Open a PR → Vercel creates a unique preview URL for that branch
- **Ignored paths:** Changes outside `frontend/` don't trigger builds (configure in Vercel Dashboard → Settings → Git → Ignored Build Step, or add `vercel.json`)

To explicitly ignore non-frontend changes, create `frontend/vercel.json`:

```json
{
  "ignoreCommand": "git diff --quiet HEAD^ HEAD -- ."
}
```

This tells Vercel: only build if files inside `frontend/` changed.

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              ← Root layout (fonts, theme, nav)
│   ├── globals.css             ← Tailwind + dark/light CSS vars
│   ├── page.tsx                ← Overview dashboard (/)
│   ├── OverviewCharts.tsx      ← Client chart wrapper
│   ├── categories/
│   │   ├── page.tsx            ← Category analytics
│   │   └── CategoriesCharts.tsx
│   ├── trends/
│   │   ├── page.tsx            ← Size & color trends
│   │   └── TrendsCharts.tsx
│   ├── locations/
│   │   ├── page.tsx            ← Store/hub leaderboard
│   │   └── LocationsCharts.tsx
│   ├── loyalty/
│   │   ├── page.tsx            ← Loyalty insights
│   │   └── LoyaltyCharts.tsx
│   └── api/
│       ├── overview/route.ts   ← Revenue KPIs
│       ├── categories/route.ts ← Category breakdown
│       ├── trends/route.ts     ← Size/color/fabric data
│       ├── locations/route.ts  ← Top stores/hubs
│       ├── loyalty/route.ts    ← Loyalty tier data
│       └── meta/route.ts       ← Last sync info
├── components/
│   ├── charts/
│   │   └── Charts.tsx          ← Recharts wrappers (line, bar, donut)
│   ├── cards/
│   │   ├── KpiCard.tsx         ← Revenue/units card with % change
│   │   └── ChartCard.tsx       ← Titled card wrapper
│   └── layout/
│       ├── Navbar.tsx          ← Navigation + theme toggle
│       ├── ThemeProvider.tsx   ← next-themes wrapper
│       └── ThemeToggle.tsx     ← Sun/moon toggle button
├── lib/
│   ├── db.ts                   ← Vercel Postgres connection
│   └── utils.ts                ← formatCurrency, formatNumber
├── scripts/
│   ├── setup-db.ts             ← Table creation DDL
│   └── seed.ts                 ← Sample data seeder
├── .env.local                  ← Vercel Postgres creds (gitignored)
├── vercel.json                 ← Monorepo build ignore config
├── tailwind.config.ts
├── postcss.config.js
├── next.config.js
├── tsconfig.json
├── package.json
├── requirement.md
└── README.md
```

## Pages

| Route | Page | Key Visuals |
|---|---|---|
| `/` | Overview | Revenue cards, trend line, sales vs returns donut |
| `/categories` | Category Analytics | Category revenue bar, returns by franchise stacked bar, brand revenue bar |
| `/trends` | Size & Color Trends | Top 10 sizes/colors bars, fabric mix donut |
| `/locations` | Location Leaderboard | Top 10 stores, top 10 hubs, city table, A vs B comparison |
| `/loyalty` | Loyalty Insights | Loyalty vs walk-in donut, tier breakdown, trend line |

## API Routes

All `GET` only — no mutations.

| Endpoint | Query Params | Returns |
|---|---|---|
| `/api/overview` | — | Weekly revenue, % change, sales vs returns |
| `/api/categories` | `period` (weekly/monthly) | Revenue by category, brand, sub-category |
| `/api/trends` | `period` (weekly/monthly) | Top sizes, colors, fabrics by units |
| `/api/locations` | `franchise` (A/B), `limit` | Top stores or hubs by revenue |
| `/api/loyalty` | `days` (default 30) | Tier breakdown, loyalty vs walk-in trend |
| `/api/meta` | — | Last sync timestamp, source, row count |

## Database

Uses **Vercel Postgres** for both local dev and production — same database, no drift.

| Table | Purpose |
|---|---|
| `summary_revenue_daily` | Daily revenue by franchise, city, category, brand |
| `summary_top_products` | Top products by size, color, fabric (weekly/monthly) |
| `summary_store_hub` | Store and hub daily performance |
| `summary_loyalty` | Loyalty tier vs walk-in daily split |
| `meta_last_sync` | Data freshness tracking |

See [requirement.md](requirement.md) for full column definitions.

## Unicode / Hindi Support

The dashboard renders Hindi (Devanagari) text in product names, store names, and customer references. Fonts:
- **Noto Sans** — Latin text
- **Noto Sans Devanagari** — Hindi text

Both loaded via `next/font/google` for zero layout shift.

## Dark / Light Mode

- User can toggle between dark and light themes via a button in the nav bar
- Powered by `next-themes` — wraps the app in a `ThemeProvider`
- Tailwind CSS `darkMode: 'class'` strategy — dark styles via `dark:` prefix
- Persisted in `localStorage` — survives page refresh and browser restart
- Defaults to OS preference (`prefers-color-scheme`) on first visit
- Charts (Recharts) adapt colors based on active theme

## Phases

**Phase 1 (current):** Self-contained dashboard with seeded sample data in Vercel Postgres. No connection to GCP.

**Phase 2 (future):** GCP Airflow pipeline pushes aggregated data to Vercel Postgres. Dashboard shows live data with "Last updated" badge.

## Schemas

See [requirement.md](requirement.md) for full database schema, page specs, API contracts, and non-functional requirements.
