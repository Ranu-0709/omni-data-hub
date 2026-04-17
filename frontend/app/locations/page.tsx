import { pool } from "@/lib/db";
import { formatCurrency, formatNumber } from "@/lib/utils";
import KpiCard from "@/components/cards/KpiCard";
import ChartCard from "@/components/cards/ChartCard";
import LocationsCharts from "./LocationsCharts";

async function getData() {
  const topStores = await pool.query(`
    SELECT location_name as name, SUM(total_revenue) as revenue
    FROM summary_store_hub WHERE franchise_id='A' AND date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY location_name ORDER BY revenue DESC LIMIT 10`);

  const topHubs = await pool.query(`
    SELECT location_name as name, SUM(total_revenue) as revenue
    FROM summary_store_hub WHERE franchise_id='B' AND date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY location_name ORDER BY revenue DESC LIMIT 10`);

  const topCities = await pool.query(`
    SELECT city, SUM(total_revenue) as revenue, SUM(total_units) as units, SUM(total_returns) as returns
    FROM summary_revenue_daily WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY city ORDER BY revenue DESC LIMIT 10`);

  const comparison = await pool.query(`
    SELECT franchise_id, SUM(total_revenue) as revenue, SUM(total_units) as units, SUM(total_returns) as returns
    FROM summary_revenue_daily WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY franchise_id`);

  return { topStores: topStores.rows, topHubs: topHubs.rows, topCities: topCities.rows, comparison: comparison.rows };
}

export default async function LocationsPage() {
  const { topStores, topHubs, topCities, comparison } = await getData();

  const a = comparison.find((r) => r.franchise_id === "A");
  const b = comparison.find((r) => r.franchise_id === "B");

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Location Leaderboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <KpiCard title="Franchise A — Stores" value={formatCurrency(Number(a?.revenue || 0))} subtitle={`${formatNumber(Number(a?.units || 0))} units`} />
        <KpiCard title="Franchise B — Quick Commerce" value={formatCurrency(Number(b?.revenue || 0))} subtitle={`${formatNumber(Number(b?.units || 0))} units`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
        <ChartCard title="Top 10 Stores (Franchise A)">
          <LocationsCharts data={topStores} />
        </ChartCard>
        <ChartCard title="Top 10 Hubs (Franchise B)">
          <LocationsCharts data={topHubs} />
        </ChartCard>
      </div>

      <ChartCard title="Top 10 Cities by Revenue">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left py-2 text-[var(--text-secondary)]">City</th>
                <th className="text-right py-2 text-[var(--text-secondary)]">Revenue</th>
                <th className="text-right py-2 text-[var(--text-secondary)]">Units</th>
                <th className="text-right py-2 text-[var(--text-secondary)]">Return Rate</th>
              </tr>
            </thead>
            <tbody>
              {topCities.map((row) => (
                <tr key={row.city as string} className="border-b border-[var(--border)]">
                  <td className="py-2">{row.city as string}</td>
                  <td className="text-right">{formatCurrency(Number(row.revenue))}</td>
                  <td className="text-right">{formatNumber(Number(row.units))}</td>
                  <td className="text-right">{((Number(row.returns) / Number(row.units)) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>
    </div>
  );
}
