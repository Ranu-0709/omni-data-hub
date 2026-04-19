"""Test connection to PostgreSQL running in Docker."""

import psycopg2

# ── UPDATE THESE ──────────────────────────────────────────────
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "omnihub"
PG_USER = "admin"
PG_PASSWORD = "password"
# ──────────────────────────────────────────────────────────────

def main():
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            dbname=PG_DB, user=PG_USER, password=PG_PASSWORD,
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
