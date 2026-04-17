import { pool } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const period = req.nextUrl.searchParams.get("period") || "weekly";

  const topSizes = await pool.query(`
    SELECT size, SUM(units_sold) as units
    FROM summary_top_products
    WHERE period = ${period} AND size IS NOT NULL
    GROUP BY size
    ORDER BY units DESC
    LIMIT 10`);

  const topColors = await pool.query(`
    SELECT color, SUM(units_sold) as units
    FROM summary_top_products
    WHERE period = ${period} AND color IS NOT NULL
    GROUP BY color
    ORDER BY units DESC
    LIMIT 10`);

  const fabricMix = await pool.query(`
    SELECT fabric, SUM(revenue) as revenue
    FROM summary_top_products
    WHERE period = ${period} AND fabric IS NOT NULL
    GROUP BY fabric
    ORDER BY revenue DESC`);

  const sizeColorMatrix = await pool.query(`
    SELECT size, color, SUM(units_sold) as units
    FROM summary_top_products
    WHERE period = ${period} AND size IS NOT NULL AND color IS NOT NULL
    GROUP BY size, color
    ORDER BY units DESC
    LIMIT 100`);

  return NextResponse.json({
    topSizes: topSizes.rows,
    topColors: topColors.rows,
    fabricMix: fabricMix.rows,
    sizeColorMatrix: sizeColorMatrix.rows,
  });
}
