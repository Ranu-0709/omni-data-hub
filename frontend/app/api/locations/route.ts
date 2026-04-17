import { sql } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const franchise = req.nextUrl.searchParams.get("franchise") || "A";
  const limit = parseInt(req.nextUrl.searchParams.get("limit") || "10");

  const topLocations = await sql`
    SELECT location_code, location_name, city,
           SUM(total_revenue) as revenue,
           SUM(total_units) as units,
           SUM(total_returns) as returns
    FROM summary_store_hub
    WHERE franchise_id = ${franchise}
      AND date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY location_code, location_name, city
    ORDER BY revenue DESC
    LIMIT ${limit}`;

  const topCities = await sql`
    SELECT city,
           SUM(total_revenue) as revenue,
           SUM(total_units) as units,
           SUM(total_returns) as returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY city
    ORDER BY revenue DESC
    LIMIT 10`;

  const franchiseComparison = await sql`
    SELECT franchise_id,
           SUM(total_revenue) as revenue,
           SUM(total_units) as units,
           SUM(total_returns) as returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY franchise_id`;

  return NextResponse.json({
    topLocations: topLocations.rows,
    topCities: topCities.rows,
    franchiseComparison: franchiseComparison.rows,
  });
}
