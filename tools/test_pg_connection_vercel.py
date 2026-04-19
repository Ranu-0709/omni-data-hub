"""Test connection to PostgreSQL running in Vercel."""

import psycopg2

# ── UPDATE THESE ──────────────────────────────────────────────
PG_HOST = "db.prisma.io"
PG_PORT = 5432
PG_DB = "postgres"
PG_USER = "2457aa2f9de3a7f814f8a1525ab207fc9686d11b2aaeaedf146a1c295618e2a4"
PG_PASSWORD = "sk_vv12v8BwY4DXyL9Ta8GLE"
# ──────────────────────────────────────────────────────────────

def main():
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            dbname=PG_DB, user=PG_USER, password=PG_PASSWORD,
            sslmode="require"
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print("Connected ✓")
        print(cur.fetchone()[0])
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Connection failed ✗\n{e}")

if __name__ == "__main__":
    main()
