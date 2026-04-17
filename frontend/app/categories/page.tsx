import { pool } from "@/lib/db";
import ChartCard from "@/components/cards/ChartCard";
import CategoriesCharts from "./CategoriesCharts";

async function getData() {
  const byCategory = await pool.query(`
    SELECT category,
           SUM(total_revenue) as revenue,
           SUM(total_units) as units,
           SUM(total_returns) as returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY category ORDER BY revenue DESC`);

  const returnsByFranchise = await pool.query(`
    SELECT category,
           SUM(CASE WHEN franchise_id='A' THEN total_returns ELSE 0 END) as "franchiseA",
           SUM(CASE WHEN franchise_id='B' THEN total_returns ELSE 0 END) as "franchiseB"
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY category ORDER BY category`);

  const byBrand = await pool.query(`
    SELECT brand, category,
           SUM(total_revenue) as revenue
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY brand, category
    ORDER BY revenue DESC LIMIT 30`);

  return { byCategory: byCategory.rows, returnsByFranchise: returnsByFranchise.rows, byBrand: byBrand.rows };
}

export default async function CategoriesPage() {
  const { byCategory, returnsByFranchise, byBrand } = await getData();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Category Analytics</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Revenue by Category (30 Days)">
          <CategoriesCharts type="bar" data={byCategory} />
        </ChartCard>
        <ChartCard title="Returns by Category & Franchise">
          <CategoriesCharts type="stacked" data={returnsByFranchise} />
        </ChartCard>
        <ChartCard title="Revenue by Brand" className="lg:col-span-2">
          <CategoriesCharts type="brandBar" data={byBrand} />
        </ChartCard>
      </div>
    </div>
  );
}
