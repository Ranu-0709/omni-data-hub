# backend/main.py
from fastapi import FastAPI
import psycopg2
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# This is the "Waitress" that allows the Frontend to talk to the Backend
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.get("/franchises")
def get_data():
    conn = psycopg2.connect("host=omni_db dbname=omnihub user=admin password=password")
    cur = conn.cursor()
    cur.execute("SELECT franchise_name, onboard_date FROM franchise_onboarding_summary")
    return [{"name": r[0], "date": str(r[1])} for r in cur.fetchall()]