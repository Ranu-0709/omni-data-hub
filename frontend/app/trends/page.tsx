import { sql } from "@/lib/db";
import ChartCard from "@/components/cards/ChartCard";
import TrendsCharts from "./TrendsCharts";

async function getData() {
  const topSizes = await sql`
    SELECT size as name, SUM(units_sold) as units
    FROM summary_top_products WHERE period='weekly' AND size IS NOT NULL
    GROUP BY size ORDER BY units DESC LIMIT 10`;

  const topColors = await sql`
    SELECT color as name, SUM(units_sold) as units
    FROM summary_top_products WHERE period='weekly' AND color IS NOT NULL
    GROUP BY color ORDER BY units DESC LIMIT 10`;

  const fabricMix = await sql`
    SELECT fabric as name, SUM(revenue) as value
    FROM summary_top_products WHERE period='weekly' AND fabric IS NOT NULL
    GROUP BY fabric ORDER BY value DESC`;

  return { topSizes: topSizes.rows, topColors: topColors.rows, fabricMix: fabricMix.rows };
}

export default async function TrendsPage() {
  const { topSizes, topColors, fabricMix } = await getData();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Size & Color Trends</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Top Sizes by Units Sold">
          <TrendsCharts type="bar" data={topSizes} />
        </ChartCard>
        <ChartCard title="Top Colors by Units Sold">
          <TrendsCharts type="bar" data={topColors} />
        </ChartCard>
        <ChartCard title="Fabric Mix by Revenue" className="lg:col-span-2">
          <TrendsCharts type="donut" data={fabricMix} />
        </ChartCard>
      </div>
    </div>
  );
}
