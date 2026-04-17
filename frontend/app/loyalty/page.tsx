import { pool } from "@/lib/db";
import ChartCard from "@/components/cards/ChartCard";
import LoyaltyCharts from "./LoyaltyCharts";

async function getData() {
  const tierBreakdown = await pool.query(`
    SELECT loyalty_tier as name, SUM(total_revenue) as value
    FROM summary_loyalty WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY loyalty_tier ORDER BY value DESC`);

  const trend = await pool.query(`
    SELECT date::text,
           SUM(CASE WHEN loyalty_tier != 'Walk-in' THEN total_revenue ELSE 0 END) as "loyalty",
           SUM(CASE WHEN loyalty_tier = 'Walk-in' THEN total_revenue ELSE 0 END) as "walkIn"
    FROM summary_loyalty WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY date ORDER BY date`);

  const tierRevenue = await pool.query(`
    SELECT loyalty_tier as name, SUM(total_revenue) as revenue
    FROM summary_loyalty WHERE date >= CURRENT_DATE - INTERVAL '30 days' AND loyalty_tier != 'Walk-in'
    GROUP BY loyalty_tier ORDER BY revenue DESC`);

  return { tierBreakdown: tierBreakdown.rows, trend: trend.rows, tierRevenue: tierRevenue.rows };
}

export default async function LoyaltyPage() {
  const { tierBreakdown, trend, tierRevenue } = await getData();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Loyalty Insights</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Loyalty vs Walk-in Revenue">
          <LoyaltyCharts type="donut" data={tierBreakdown} />
        </ChartCard>
        <ChartCard title="Tier Revenue Breakdown">
          <LoyaltyCharts type="bar" data={tierRevenue} />
        </ChartCard>
        <ChartCard title="Loyalty vs Walk-in Trend (30 Days)" className="lg:col-span-2">
          <LoyaltyCharts type="line" data={trend} />
        </ChartCard>
      </div>
    </div>
  );
}
