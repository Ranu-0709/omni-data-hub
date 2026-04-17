import { sql } from "@vercel/postgres";

const CITIES = [
  { city: "Bengaluru", state: "KA" }, { city: "Mumbai", state: "MH" },
  { city: "Delhi", state: "DL" }, { city: "Chennai", state: "TN" },
  { city: "Kolkata", state: "WB" }, { city: "Hyderabad", state: "TS" },
  { city: "Pune", state: "MH" }, { city: "Ahmedabad", state: "GJ" },
  { city: "Jaipur", state: "RJ" }, { city: "Kochi", state: "KL" },
];

const CATEGORIES: Record<string, string[]> = {
  Menswear: ["Formal Shirt", "Casual Shirt", "T-Shirt", "Jeans", "Trousers"],
  Womenswear: ["Kurti", "Salwar Set", "Saree", "Top", "Dress"],
  Kids: ["Kids T-Shirt", "Kids Jeans", "Kids Dress"],
  "Ethnic Wear": ["Kurta Pajama", "Sherwani", "Lehenga"],
  Winterwear: ["Sweater", "Hoodie", "Jacket"],
  Accessories: ["Belt", "Wallet", "Scarf"],
};

const BRANDS = [
  "OmniThreads", "UrbanWeave", "SilkRoute", "CottonKing", "DesiDrape",
  "StitchCraft", "EthnicEdge", "StreetStyle", "RoyalStitch", "LoomLine",
];

const SIZES = ["S", "M", "L", "XL", "XXL", "32", "34", "36", "Free Size"];
const COLORS = ["Black", "White", "Navy", "Grey", "Maroon", "Olive", "Sky Blue", "Red", "Mustard", "Teal"];
const FABRICS = ["Cotton", "Linen", "Polyester", "Silk", "Denim", "Rayon", "Wool", "Khadi"];
const TIERS = ["Bronze", "Silver", "Gold", "Platinum", "Walk-in"];

function rand(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}
function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}
function dateStr(daysAgo: number): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return d.toISOString().split("T")[0];
}

async function seed() {
  console.log("Clearing existing data...");
  await sql`TRUNCATE summary_revenue_daily, summary_top_products, summary_store_hub, summary_loyalty, meta_last_sync RESTART IDENTITY`;

  // --- summary_revenue_daily: 30 days × 10 cities × 2 franchises × categories ---
  console.log("Seeding summary_revenue_daily...");
  for (let d = 0; d < 30; d++) {
    const date = dateStr(d);
    for (const { city, state } of CITIES) {
      for (const franchise of ["A", "B"]) {
        const cats = Object.entries(CATEGORIES);
        // pick 3-4 categories per city/day to keep data realistic
        const selectedCats = cats.sort(() => Math.random() - 0.5).slice(0, rand(3, cats.length));
        for (const [category, subs] of selectedCats) {
          const sub = pick(subs);
          const brand = pick(BRANDS);
          const units = rand(10, 500);
          const returns = rand(0, Math.floor(units * 0.15));
          const avgPrice = rand(499, 4999);
          const revenue = units * avgPrice;
          const returnRev = returns * avgPrice;

          await sql`
            INSERT INTO summary_revenue_daily (date, franchise_id, city, state, category, sub_category, brand, total_revenue, total_units, total_returns, return_revenue)
            VALUES (${date}, ${franchise}, ${city}, ${state}, ${category}, ${sub}, ${brand}, ${revenue}, ${units}, ${returns}, ${returnRev})`;
        }
      }
    }
  }

  // --- summary_top_products: weekly top products ---
  console.log("Seeding summary_top_products...");
  for (let w = 0; w < 4; w++) {
    const periodStart = dateStr(w * 7);
    for (let i = 0; i < 50; i++) {
      const catEntries = Object.entries(CATEGORIES);
      const [category, subs] = pick(catEntries);
      const sub = pick(subs);
      const units = rand(50, 2000);
      const revenue = units * rand(499, 5999);
      const name = `${pick(BRANDS)} ${sub}`;
      const hindiNames = [`${name} शानदार`, `${name} राजशाही`, `${name} देशी`];
      const productName = Math.random() < 0.15 ? pick(hindiNames) : name;

      await sql`
        INSERT INTO summary_top_products (period, period_start, sku_code, product_name, brand, category, size, color, fabric, units_sold, revenue)
        VALUES ('weekly', ${periodStart}, ${"SKU-" + String(rand(1, 9999)).padStart(4, "0")}, ${productName}, ${pick(BRANDS)}, ${category}, ${pick(SIZES)}, ${pick(COLORS)}, ${pick(FABRICS)}, ${units}, ${revenue})`;
    }
  }

  // --- summary_store_hub ---
  console.log("Seeding summary_store_hub...");
  const storeNames = [
    "श्री वस्त्र भंडार", "नया फैशन हाउस", "राज वस्त्रालय",
    "Trendy Threads", "Fashion Point", "Style Hub", "Garment World",
    "Urban Closet", "Ethnic Emporium", "Silk Palace",
  ];
  for (let d = 0; d < 30; d++) {
    const date = dateStr(d);
    // Franchise A stores
    for (let s = 1; s <= 10; s++) {
      const { city } = pick(CITIES);
      const units = rand(20, 300);
      const returns = rand(0, Math.floor(units * 0.1));
      await sql`
        INSERT INTO summary_store_hub (date, franchise_id, location_code, location_name, city, total_revenue, total_units, total_returns)
        VALUES (${date}, 'A', ${"FA-" + String(s).padStart(3, "0")}, ${storeNames[s - 1]}, ${city}, ${units * rand(599, 3999)}, ${units}, ${returns})`;
    }
    // Franchise B hubs
    for (let h = 1; h <= 15; h++) {
      const { city } = pick(CITIES);
      const units = rand(50, 800);
      const returns = rand(0, Math.floor(units * 0.12));
      await sql`
        INSERT INTO summary_store_hub (date, franchise_id, location_code, location_name, city, total_revenue, total_units, total_returns)
        VALUES (${date}, 'B', ${"HUB-" + String(h).padStart(3, "0")}, ${"Hub-" + city}, ${city}, ${units * rand(399, 2999)}, ${units}, ${returns})`;
    }
  }

  // --- summary_loyalty ---
  console.log("Seeding summary_loyalty...");
  for (let d = 0; d < 30; d++) {
    const date = dateStr(d);
    for (const tier of TIERS) {
      const isWalkin = tier === "Walk-in";
      const units = isWalkin ? rand(200, 800) : rand(30, 400);
      const customers = isWalkin ? rand(150, 600) : rand(10, 200);
      const revenue = units * rand(699, 4999);
      await sql`
        INSERT INTO summary_loyalty (date, loyalty_tier, total_revenue, total_units, customer_count)
        VALUES (${date}, ${tier}, ${revenue}, ${units}, ${customers})`;
    }
  }

  // --- meta_last_sync ---
  await sql`INSERT INTO meta_last_sync (source, rows_synced) VALUES ('seed', 5000)`;

  console.log("Seed complete.");
}

seed().catch(console.error);
