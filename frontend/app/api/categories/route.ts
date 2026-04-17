import { pool } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const period = req.nextUrl.searchParams.get("period") || "weekly";
  const days = period === "monthly" ? 30 : 7;

  const byCategory = await pool.query(`
    SELECT category,
           SUM(total_revenue) as revenue,
           SUM(total_units) as units,
           SUM(total_returns) as returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - CAST(${days} || ' days' AS INTERVAL)
    GROUP BY category
    ORDER BY revenue DESC`);

  const byBrand = await pool.query(`
    SELECT brand, category, sub_category,
           SUM(total_revenue) as revenue
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - CAST(${days} || ' days' AS INTERVAL)
    GROUP BY brand, category, sub_category
    ORDER BY revenue DESC
    LIMIT 50`);

  const returnsByCategory = await pool.query(`
    SELECT category, franchise_id,
           SUM(total_returns) as returns
    FROM summary_revenue_daily
    WHERE date >= CURRENT_DATE - CAST(${days} || ' days' AS INTERVAL)
    GROUP BY category, franchise_id
    ORDER BY category`);

  return NextResponse.json({
    byCategory: byCategory.rows,
    byBrand: byBrand.rows,
    returnsByCategory: returnsByCategory.rows,
  });
}
