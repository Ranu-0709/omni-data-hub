import { sql } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const days = parseInt(req.nextUrl.searchParams.get("days") || "30");

  const tierBreakdown = await sql`
    SELECT loyalty_tier,
           SUM(total_revenue) as revenue,
           SUM(total_units) as units,
           SUM(customer_count) as customers
    FROM summary_loyalty
    WHERE date >= CURRENT_DATE - CAST(${days} || ' days' AS INTERVAL)
    GROUP BY loyalty_tier
    ORDER BY revenue DESC`;

  const trend = await sql`
    SELECT date,
           SUM(CASE WHEN loyalty_tier != 'Walk-in' THEN total_revenue ELSE 0 END) as loyalty_revenue,
           SUM(CASE WHEN loyalty_tier = 'Walk-in' THEN total_revenue ELSE 0 END) as walkin_revenue
    FROM summary_loyalty
    WHERE date >= CURRENT_DATE - CAST(${days} || ' days' AS INTERVAL)
    GROUP BY date
    ORDER BY date`;

  return NextResponse.json({
    tierBreakdown: tierBreakdown.rows,
    trend: trend.rows,
  });
}
