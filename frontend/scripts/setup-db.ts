import dotenv from "dotenv";
dotenv.config({ path: ".env.local" });

import pkg from "pg";
const { Client } = pkg;

const client = new Client({
  connectionString: process.env.POSTGRES_URL,
});

async function setup() {
  console.log("Creating tables...");

  await client.connect();

  await client.query(`
    CREATE TABLE IF NOT EXISTS summary_revenue_daily (
      id SERIAL PRIMARY KEY,
      date DATE NOT NULL,
      franchise_id VARCHAR(1) NOT NULL,
      city VARCHAR(50) NOT NULL,
      state VARCHAR(5) NOT NULL,
      category VARCHAR(30) NOT NULL,
      sub_category VARCHAR(50) NOT NULL,
      brand VARCHAR(50) NOT NULL,
      total_revenue DECIMAL(15,2) DEFAULT 0,
      total_units INT DEFAULT 0,
      total_returns INT DEFAULT 0,
      return_revenue DECIMAL(15,2) DEFAULT 0
    )`);

  await client.query(`
    CREATE TABLE IF NOT EXISTS summary_top_products (
      id SERIAL PRIMARY KEY,
      period VARCHAR(10) NOT NULL,
      period_start DATE NOT NULL,
      sku_code VARCHAR(20) NOT NULL,
      product_name VARCHAR(100) NOT NULL,
      brand VARCHAR(50) NOT NULL,
      category VARCHAR(30) NOT NULL,
      size VARCHAR(10),
      color VARCHAR(20),
      fabric VARCHAR(30),
      units_sold INT DEFAULT 0,
      revenue DECIMAL(15,2) DEFAULT 0
    )`);

  await client.query(`
    CREATE TABLE IF NOT EXISTS summary_store_hub (
      id SERIAL PRIMARY KEY,
      date DATE NOT NULL,
      franchise_id VARCHAR(1) NOT NULL,
      location_code VARCHAR(20) NOT NULL,
      location_name VARCHAR(100) NOT NULL,
      city VARCHAR(50) NOT NULL,
      total_revenue DECIMAL(15,2) DEFAULT 0,
      total_units INT DEFAULT 0,
      total_returns INT DEFAULT 0
    )`);

  await client.query(`
    CREATE TABLE IF NOT EXISTS summary_loyalty (
      id SERIAL PRIMARY KEY,
      date DATE NOT NULL,
      loyalty_tier VARCHAR(10) NOT NULL,
      total_revenue DECIMAL(15,2) DEFAULT 0,
      total_units INT DEFAULT 0,
      customer_count INT DEFAULT 0
    )`);

  await client.query(`
    CREATE TABLE IF NOT EXISTS meta_last_sync (
      id SERIAL PRIMARY KEY,
      synced_at TIMESTAMP DEFAULT NOW(),
      source VARCHAR(20) NOT NULL,
      rows_synced INT DEFAULT 0
    )`);

  console.log("All tables created.");
  await client.end();
}

setup().catch(console.error);
