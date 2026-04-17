import { sql } from "@/lib/db";
import { NextResponse } from "next/server";

export async function GET() {
  const thisWeek = await sql`
    SELECT franchise_id,
           SUM(total_revenue) as revenue,
           SUM(total_units) as units,
           SUM(total_returns) as returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY franchise_id`;

  const lastWeek = await sql`
    SELECT franchise_id,
           SUM(total_revenue) as revenue,
           SUM(total_units) as units,
           SUM(total_returns) as returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '14 days'
      AND date < CURRENT_DATE - INTERVAL '7 days'
    GROUP BY franchise_id`;

  const trend = await sql`
    SELECT date, franchise_id,
           SUM(total_revenue) as revenue
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY date, franchise_id
    ORDER BY date`;

  const salesVsReturns = await sql`
    SELECT SUM(total_units) as total_sales,
           SUM(total_returns) as total_returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'`;

  return NextResponse.json({
    thisWeek: thisWeek.rows,
    lastWeek: lastWeek.rows,
    trend: trend.rows,
    salesVsReturns: salesVsReturns.rows[0],
  });
}
