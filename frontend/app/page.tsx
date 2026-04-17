import { sql } from "@/lib/db";
import { formatCurrency, formatNumber } from "@/lib/utils";
import KpiCard from "@/components/cards/KpiCard";
import ChartCard from "@/components/cards/ChartCard";
import OverviewCharts from "./OverviewCharts";

async function getData() {
  const thisWeek = await sql`
    SELECT franchise_id,
           COALESCE(SUM(total_revenue),0) as revenue,
           COALESCE(SUM(total_units),0) as units,
           COALESCE(SUM(total_returns),0) as returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY franchise_id`;

  const lastWeek = await sql`
    SELECT franchise_id,
           COALESCE(SUM(total_revenue),0) as revenue
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '14 days'
      AND date < CURRENT_DATE - INTERVAL '7 days'
    GROUP BY franchise_id`;

  const trend = await sql`
    SELECT date::text,
           SUM(CASE WHEN franchise_id='A' THEN total_revenue ELSE 0 END) as "franchiseA",
           SUM(CASE WHEN franchise_id='B' THEN total_revenue ELSE 0 END) as "franchiseB"
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY date ORDER BY date`;

  const totals = await sql`
    SELECT COALESCE(SUM(total_units),0) as total_sales,
           COALESCE(SUM(total_returns),0) as total_returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'`;

  const meta = await sql`SELECT synced_at, source FROM meta_last_sync ORDER BY synced_at DESC LIMIT 1`;

  return { thisWeek: thisWeek.rows, lastWeek: lastWeek.rows, trend: trend.rows, totals: totals.rows[0], meta: meta.rows[0] };
}

export default async function OverviewPage() {
  const { thisWeek, lastWeek, trend, totals, meta } = await getData();

  const getWeek = (rows: Record<string, unknown>[], fid: string) =>
    rows.find((r) => r.franchise_id === fid);

  const a = getWeek(thisWeek, "A");
  const b = getWeek(thisWeek, "B");
  const aLast = getWeek(lastWeek, "A");
  const bLast = getWeek(lastWeek, "B");

  const totalRev = Number(a?.revenue || 0) + Number(b?.revenue || 0);
  const totalLastRev = Number(aLast?.revenue || 0) + Number(bLast?.revenue || 0);
  const totalChange = totalLastRev > 0 ? ((totalRev - totalLastRev) / totalLastRev) * 100 : 0;

  const aChange = Number(aLast?.revenue || 0) > 0
    ? ((Number(a?.revenue || 0) - Number(aLast?.revenue || 0)) / Number(aLast?.revenue || 0)) * 100 : 0;
  const bChange = Number(bLast?.revenue || 0) > 0
    ? ((Number(b?.revenue || 0) - Number(bLast?.revenue || 0)) / Number(bLast?.revenue || 0)) * 100 : 0;

  const salesVsReturns = [
    { name: "Sales", value: Number(totals?.total_sales || 0) - Number(totals?.total_returns || 0) },
    { name: "Returns", value: Number(totals?.total_returns || 0) },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Overview</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <KpiCard title="Total Revenue (This Week)" value={formatCurrency(totalRev)} change={totalChange} />
        <KpiCard title="Franchise A Revenue" value={formatCurrency(Number(a?.revenue || 0))} change={aChange} subtitle="Brick & Mortar Stores" />
        <KpiCard title="Franchise B Revenue" value={formatCurrency(Number(b?.revenue || 0))} change={bChange} subtitle="Quick Commerce" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="Revenue Trend (30 Days)" className="lg:col-span-2">
          <OverviewCharts type="line" data={trend} />
        </ChartCard>
        <ChartCard title="Sales vs Returns (30 Days)">
          <OverviewCharts type="donut" data={salesVsReturns} />
        </ChartCard>
      </div>

      {meta && (
        <p className="mt-6 text-xs text-[var(--text-secondary)]">
          Last synced: {new Date(meta.synced_at as string).toLocaleString()} ({meta.source})
        </p>
      )}
    </div>
  );
}
