import { sql } from "@/lib/db";
import { NextResponse } from "next/server";

export async function GET() {
  const result = await sql`
    SELECT synced_at, source, rows_synced
    FROM meta_last_sync
    ORDER BY synced_at DESC
    LIMIT 1`;

  return NextResponse.json(result.rows[0] || { synced_at: null, source: "none", rows_synced: 0 });
}
