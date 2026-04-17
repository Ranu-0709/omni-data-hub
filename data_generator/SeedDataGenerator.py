"""
One-time seed data generator.
Run ONCE to backfill the landing zone with historical master + sales data.

Data ownership:
  - Master Company (manufacturer): product_master, customer_master
  - Franchise A (retail): store_master, weekly sales (references master SKU + loyalty)
  - Franchise B (quick-commerce): hub_master, barcode_sku_mapping, daily sales

Optimised for multi-GB output:
  - Parallel file generation (one process per monthly file)
  - Chunked writes (constant memory per worker)
  - Numpy-vectorised ops — no Python loops in hot path
"""
import pandas as pd
import numpy as np
import uuid
import random
from faker import Faker
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

fake_en = Faker('en_IN')
fake_hi = Faker('hi_IN')
HINDI_PCT = 0.15               # ~15% of names/labels will be in Hindi

# ──────────────────── CONSTANTS ────────────────────
ROWS_FRANCHISE_A = 50_000_000       # Total historical sales rows
ROWS_FRANCHISE_B = 250_000_000      # Total historical sales rows (~1-2 GB per monthly file)
CHUNK_SIZE = 500_000               # Rows per chunk (controls memory per worker)
MAX_WORKERS = max(1, cpu_count() - 1)
MASTER_SKU_COUNT = 10_000
LOYALTY_CUSTOMER_COUNT = 5_000     # Customers in manufacturer's loyalty program
STORE_COUNT_A = 10
HUB_COUNT_B = 500
BARCODE_PER_SKU_MIN = 1            # Min internal barcodes Franchise B creates per SKU
BARCODE_PER_SKU_MAX = 3            # Max (variants/pack sizes get separate barcodes)
ROWS_VARIANCE_PCT = 30             # ±% variance in rows per month
LOYALTY_BLANK_MAX_PCT = 0.21       # Max fraction of customers without loyalty ID
LOYALTY_VARIANCE_PCT = 100         # % below max — actual rate per chunk randomised
ERROR_PCT = 0.005                  # ~0.5 % rows get a data-quality error

# India geo bounds
INDIA_LAT_MIN, INDIA_LAT_MAX = 8.0, 35.0
INDIA_LON_MIN, INDIA_LON_MAX = 68.0, 97.0

INDIA_CITIES = [
    ("Bengaluru", "KA"), ("Mysuru", "KA"),
    ("Mumbai", "MH"), ("Pune", "MH"), ("Nagpur", "MH"),
    ("Delhi", "DL"), ("Noida", "UP"), ("Lucknow", "UP"),
    ("Chennai", "TN"), ("Coimbatore", "TN"),
    ("Kolkata", "WB"), ("Hyderabad", "TS"),
    ("Ahmedabad", "GJ"), ("Jaipur", "RJ"),
    ("Kochi", "KL"), ("Bhopal", "MP"),
    ("Patna", "BR"), ("Chandigarh", "CH"),
    ("Guwahati", "AS"), ("Indore", "MP"),
]

# Product taxonomy (Indian garment manufacturer)
BRANDS = [
    "OmniThreads", "UrbanWeave", "SilkRoute", "CottonKing", "DesiDrape",
    "StitchCraft", "FabIndia", "EthnicEdge", "StreetStyle", "RoyalStitch",
    "LoomLine", "ThreadBare", "IndoChic", "WeaveMaster", "KhaadiKraft",
]
CATEGORIES = {
    "Menswear":    ["Formal Shirt", "Casual Shirt", "T-Shirt", "Polo", "Jeans", "Trousers", "Chinos", "Shorts", "Blazer", "Jacket"],
    "Womenswear":  ["Kurti", "Salwar Set", "Saree", "Blouse", "Leggings", "Palazzo", "Top", "Dress", "Skirt", "Jumpsuit"],
    "Kids":        ["Kids T-Shirt", "Kids Jeans", "Kids Dress", "Kids Shorts", "Kids Ethnic Set"],
    "Ethnic Wear": ["Kurta Pajama", "Sherwani", "Nehru Jacket", "Dhoti", "Lehenga", "Anarkali", "Churidar Set"],
    "Winterwear":  ["Sweater", "Hoodie", "Cardigan", "Thermal", "Puffer Jacket", "Shawl"],
    "Accessories": ["Belt", "Wallet", "Scarf", "Tie", "Pocket Square", "Cap", "Socks"],
}
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL",
         "28", "30", "32", "34", "36", "38", "40", "42",
         "Free Size"]
COLORS = ["Black", "White", "Navy", "Grey", "Beige", "Maroon", "Olive",
          "Sky Blue", "Pink", "Red", "Mustard", "Teal", "Charcoal",
          "Indigo", "Off-White", "Rust", "Lavender", "Peach"]
FABRICS = ["Cotton", "Linen", "Polyester", "Silk", "Denim", "Rayon",
           "Viscose", "Wool", "Khadi", "Georgette", "Chiffon", "Crepe",
           "Cotton Blend", "Poly-Cotton", "Lycra", "Fleece"]
GARMENT_HSN = [6101, 6102, 6103, 6104, 6105, 6106, 6109, 6110, 6111,
               6201, 6202, 6203, 6204, 6205, 6206, 6211, 6214, 6217]
LOYALTY_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]

# Hindi product name fragments (mixed into ~15% of product names)
HINDI_PRODUCT_TAGS = [
    "\u0936\u093e\u0928\u0926\u093e\u0930", "\u0930\u093e\u091c\u0936\u093e\u0939\u0940",
    "\u092a\u0930\u0902\u092a\u0930\u093e\u0917\u0924", "\u0926\u0947\u0936\u0940",
    "\u0938\u0941\u0928\u0939\u0930\u093e", "\u0938\u0902\u0917\u094d\u0930\u0939",
]  # shandar, rajshahi, paramparagat, desi, sunhara, sangrah

# Hindi store / hub name fragments
HINDI_STORE_NAMES = [
    "\u0936\u094d\u0930\u0940 \u0935\u0938\u094d\u0924\u094d\u0930 \u092d\u0902\u0921\u093e\u0930",
    "\u0928\u092f\u093e \u092b\u0948\u0936\u0928 \u0939\u093e\u0909\u0938",
    "\u0930\u093e\u091c \u0935\u0938\u094d\u0924\u094d\u0930\u093e\u0932\u092f",
]  # Shri Vastra Bhandar, Naya Fashion House, Raj Vastralaya

# FY 25-26
DATE_START = datetime(2025, 4, 1)
DATE_END = datetime(2026, 3, 31)

OUTPUT_DIR_MASTER = os.path.join("storage", "landing_zone", "master_company")
OUTPUT_DIR_A = os.path.join("storage", "landing_zone", "franchise_a")
OUTPUT_DIR_B = os.path.join("storage", "landing_zone", "franchise_b")
# ───────────────────────────────────────────────────

# Pre-compute lookup arrays
_sku_codes = np.array([f"SKU-{i:04d}" for i in range(1, MASTER_SKU_COUNT + 1)])
_store_codes = np.array([f"FA-{i:03d}" for i in range(1, STORE_COUNT_A + 1)])
_hub_ids = np.array([str(uuid.uuid4())[:8] for _ in range(HUB_COUNT_B)])
_loyalty_ids = np.array([f"LOYAL-{i:04d}" for i in range(1, LOYALTY_CUSTOMER_COUNT + 1)])
_statuses = np.array(["DELIVERED", "RETURNED", "CANCELLED"])
_status_weights = np.array([0.85, 0.10, 0.05])
_HEX = np.array(list('0123456789abcdef'))

# Will be populated after master generation
_ean_barcodes = None       # EAN-13 barcodes from product master
_fb_barcodes = None        # Franchise B internal barcodes (from mapping)


# ── HELPERS ──────────────────────────────────────
def _months_between(start, end):
    months = []
    cur = start.replace(day=1)
    while cur <= end:
        m_start = max(cur, start)
        next_month = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        m_end = min(next_month - timedelta(seconds=1), end)
        months.append((m_start, m_end))
        cur = next_month
    return months


def _rand_timestamps(n, start, end):
    delta_s = int((end - start).total_seconds())
    offsets = np.random.randint(0, max(delta_s, 1), size=n)
    epoch = np.datetime64(start, 's')
    return epoch + offsets.astype('timedelta64[s]')


def _fast_hex_ids(n, length=16):
    raw = np.random.choice(_HEX, size=(n, length))
    return np.array([''.join(row) for row in raw])


def _fast_prefixed_ids(prefix, n, low, high):
    nums = np.random.randint(low, high, size=n)
    return np.char.add(prefix, nums.astype(str))


def _inject_errors_a(df):
    n = len(df)
    err_count = max(1, int(n * ERROR_PCT))
    idx = np.random.choice(n, size=err_count, replace=False)
    third = err_count // 3
    df.iloc[idx[:third], df.columns.get_loc('quantity')] = -500
    df.iloc[idx[:third], df.columns.get_loc('transaction_type')] = 'RETURN'
    df.iloc[idx[third:2*third], df.columns.get_loc('unit_price')] = np.nan
    df.iloc[idx[2*third:], df.columns.get_loc('transaction_timestamp')] = np.datetime64('2030-01-01')
    return df


def _inject_errors_b(df):
    n = len(df)
    err_count = max(1, int(n * ERROR_PCT))
    idx = np.random.choice(n, size=err_count, replace=False)
    third = err_count // 3
    df.iloc[idx[:third], df.columns.get_loc('mrp_price')] = 0.00
    s2 = idx[third:2*third]
    if len(s2):
        df.iloc[s2, df.columns.get_loc('order_uuid')] = df.iloc[s2[0], df.columns.get_loc('order_uuid')]
    df.iloc[idx[2*third:], df.columns.get_loc('discount_applied')] = -1000.00
    return df


def _distribute_rows(total, num_months, variance_pct):
    avg = total / num_months
    lo = avg * (1 - variance_pct / 100)
    hi = avg * (1 + variance_pct / 100)
    raw = [random.uniform(lo, hi) for _ in range(num_months)]
    scale = total / sum(raw)
    distributed = [int(r * scale) for r in raw]
    diff = total - sum(distributed)
    distributed[random.randint(0, num_months - 1)] += diff
    return distributed


# ══════════════════════════════════════════════════
#  MASTER COMPANY DATA (manufacturer-owned)
# ══════════════════════════════════════════════════
def generate_product_master():
    """Product catalog owned by the manufacturing company.
    Both franchises reference this via sku_code / ean_barcode."""
    global _ean_barcodes

    categories_flat = []
    subcategories_flat = []
    for cat, subs in CATEGORIES.items():
        for sub in subs:
            categories_flat.append(cat)
            subcategories_flat.append(sub)

    n = MASTER_SKU_COUNT
    cat_sub_idx = np.random.randint(0, len(categories_flat), size=n)
    batch_dates = [DATE_START - timedelta(days=random.randint(30, 365)) for _ in range(n)]

    ean = np.random.randint(8_900_000_000_000, 8_909_999_999_999, size=n, dtype=np.int64)
    _ean_barcodes = ean

    df = pd.DataFrame({
        'sku_code': _sku_codes,
        'ean_barcode': ean,
        'product_name': [
            f"{random.choice(BRANDS)} {subcategories_flat[cat_sub_idx[i]]} {random.choice(HINDI_PRODUCT_TAGS)}"
            if random.random() < HINDI_PCT
            else f"{random.choice(BRANDS)} {subcategories_flat[cat_sub_idx[i]]}"
            for i in range(n)
        ],
        'brand': [random.choice(BRANDS) for _ in range(n)],
        'category': [categories_flat[cat_sub_idx[i]] for i in range(n)],
        'sub_category': [subcategories_flat[cat_sub_idx[i]] for i in range(n)],
        'size': [random.choice(SIZES) for _ in range(n)],
        'color': [random.choice(COLORS) for _ in range(n)],
        'fabric': [random.choice(FABRICS) for _ in range(n)],
        'batch_code': [f"B{d.strftime('%y%m')}-{random.randint(100,999)}" for d in batch_dates],
        'manufacturing_date': [d.strftime('%Y-%m-%d') for d in batch_dates],
        'mrp': np.round(np.random.uniform(299, 9999, size=n), 2),
        'hsn_code': [random.choice(GARMENT_HSN) for _ in range(n)],
        'gst_pct': np.random.choice([5, 12], size=n, p=[0.7, 0.3]),
    })
    os.makedirs(OUTPUT_DIR_MASTER, exist_ok=True)
    df.to_csv(os.path.join(OUTPUT_DIR_MASTER, "product_master.csv"), index=False, encoding='utf-8-sig')
    print(f"  product_master.csv  ({n:,} SKUs)")
    return df


def generate_customer_master():
    """Loyalty customer database owned by the manufacturing company.
    Franchise A references customer_id from this master."""
    n = LOYALTY_CUSTOMER_COUNT
    city_state = [random.choice(INDIA_CITIES) for _ in range(n)]
    join_dates = [DATE_START - timedelta(days=random.randint(30, 1095)) for _ in range(n)]

    df = pd.DataFrame({
        'customer_id': _loyalty_ids,
        'customer_name': [
            fake_hi.name() if random.random() < HINDI_PCT else fake_en.name()
            for _ in range(n)
        ],
        'phone': [fake_en.phone_number() for _ in range(n)],
        'email': [fake_en.email() for _ in range(n)],
        'city': [c for c, _ in city_state],
        'state': [s for _, s in city_state],
        'loyalty_tier': np.random.choice(LOYALTY_TIERS, size=n, p=[0.40, 0.30, 0.20, 0.10]),
        'join_date': [d.strftime('%Y-%m-%d') for d in join_dates],
    })
    df.to_csv(os.path.join(OUTPUT_DIR_MASTER, "customer_master.csv"), index=False, encoding='utf-8-sig')
    print(f"  customer_master.csv  ({n:,} customers)")
    return df


# ══════════════════════════════════════════════════
#  FRANCHISE A — store master + sales
# ══════════════════════════════════════════════════
def generate_store_master():
    pairs = [random.choice(INDIA_CITIES) for _ in _store_codes]
    pd.DataFrame({
        'store_code': _store_codes,
        'store_name': [
            random.choice(HINDI_STORE_NAMES) if random.random() < HINDI_PCT else fake_en.company()
            for _ in _store_codes
        ],
        'city': [c for c, _ in pairs],
        'state': [s for _, s in pairs]
    }).to_csv(os.path.join(OUTPUT_DIR_A, "storemaster_monthly_refresh.csv"), index=False, encoding='utf-8-sig')
    print(f"  storemaster_monthly_refresh.csv  ({len(_store_codes)} stores)")


def _generate_chunk_a(n, start, end):
    blank_rate = random.uniform(
        LOYALTY_BLANK_MAX_PCT * (1 - LOYALTY_VARIANCE_PCT / 100),
        LOYALTY_BLANK_MAX_PCT
    )
    loyalty_mask = np.random.random(n) > blank_rate
    cust_ids = np.where(loyalty_mask, np.random.choice(_loyalty_ids, size=n), '')

    df = pd.DataFrame({
        'invoice_number': _fast_prefixed_ids("INV-", n, 10000, 100000),
        'store_code': np.random.choice(_store_codes, size=n),
        'transaction_timestamp': _rand_timestamps(n, start, end),
        'sku_code': np.random.choice(_sku_codes, size=n),
        'quantity': np.random.randint(1, 6, size=n),
        'unit_price': np.round(np.random.uniform(299, 9999, size=n), 2),
        'transaction_type': np.full(n, 'SALE'),
        'customer_id': cust_ids
    })
    return _inject_errors_a(df)


def _write_monthly_a(args):
    fname, target, m_start, m_end = args
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    t0 = time.time()
    first = True
    written = 0
    while written < target:
        n = min(CHUNK_SIZE, target - written)
        _generate_chunk_a(n, m_start, m_end).to_csv(
            fname, index=False, mode='a', header=first, encoding='utf-8-sig' if first else 'utf-8')
        first = False
        written += n
    return f"  {fname}  ({written:,} rows, {time.time()-t0:.1f}s)"


def generate_sales_a():
    months = _months_between(DATE_START, DATE_END)
    month_rows = _distribute_rows(ROWS_FRANCHISE_A, len(months), ROWS_VARIANCE_PCT)

    tasks = []
    for (m_start, m_end), target in zip(months, month_rows):
        fname = os.path.join(OUTPUT_DIR_A, f"sales_monthly_{m_start:%Y_%m}.csv")
        tasks.append((fname, target, m_start, m_end))

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_write_monthly_a, t): t for t in tasks}
        for f in as_completed(futures):
            print(f.result())


# ══════════════════════════════════════════════════
#  FRANCHISE B — hub master + barcode mapping + sales
# ══════════════════════════════════════════════════
def generate_hub_master():
    pd.DataFrame({
        'hub_id': _hub_ids,
        'hub_name': [f"Hub-{random.choice(INDIA_CITIES)[0]}" for _ in _hub_ids],
        'pincode': np.random.randint(110000, 856000, size=HUB_COUNT_B).astype(str),
        'latitude': np.round(np.random.uniform(INDIA_LAT_MIN, INDIA_LAT_MAX, HUB_COUNT_B), 6),
        'longitude': np.round(np.random.uniform(INDIA_LON_MIN, INDIA_LON_MAX, HUB_COUNT_B), 6)
    }).to_csv(os.path.join(OUTPUT_DIR_B, "hubmaster_weekly_refresh.psv"), index=False, sep="|", encoding='utf-8-sig')
    print(f"  hubmaster_weekly_refresh.psv  ({HUB_COUNT_B} hubs)")


def generate_barcode_sku_mapping():
    """Franchise B's internal barcode → manufacturer SKU mapping.
    Owned by Franchise B — they create internal barcodes for warehouse ops,
    then share this mapping back so the manufacturer can reconcile sales."""
    global _fb_barcodes

    rows = []
    for i, sku in enumerate(_sku_codes):
        num_barcodes = random.randint(BARCODE_PER_SKU_MIN, BARCODE_PER_SKU_MAX)
        for j in range(num_barcodes):
            rows.append({
                'item_barcode': int(f"99{random.randint(10_000_000_00, 99_999_999_99)}"),
                'sku_code': sku,
                'ean_barcode': int(_ean_barcodes[i]),
                'variant_label': f"{random.choice(SIZES)}-{random.choice(COLORS)}",
                'is_active': random.choices([1, 0], weights=[95, 5])[0],
            })

    df = pd.DataFrame(rows)
    _fb_barcodes = df['item_barcode'].values
    df.to_csv(os.path.join(OUTPUT_DIR_B, "barcode_sku_mapping.psv"), index=False, sep="|", encoding='utf-8-sig')
    print(f"  barcode_sku_mapping.psv  ({len(df):,} mappings for {MASTER_SKU_COUNT:,} SKUs)")
    return df


def _generate_chunk_b(n, start, end, fb_barcodes):
    df = pd.DataFrame({
        'order_uuid': _fast_hex_ids(n),
        'hub_id': np.random.choice(_hub_ids, size=n),
        'item_barcode': np.random.choice(fb_barcodes, size=n),
        'units_sold': np.random.randint(1, 4, size=n),
        'mrp_price': np.round(np.random.uniform(299, 9999, size=n), 2),
        'discount_applied': np.round(np.random.uniform(0, 500, size=n), 2),
        'delivery_timestamp': _rand_timestamps(n, start, end),
        'status': np.random.choice(_statuses, size=n, p=_status_weights)
    })
    return _inject_errors_b(df)


def _write_monthly_b(args):
    fname, target, m_start, m_end, fb_barcodes = args
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    t0 = time.time()
    first = True
    written = 0
    while written < target:
        n = min(CHUNK_SIZE, target - written)
        _generate_chunk_b(n, m_start, m_end, fb_barcodes).to_csv(
            fname, index=False, sep="|", mode='a', header=first, encoding='utf-8-sig' if first else 'utf-8')
        first = False
        written += n
    return f"  {fname}  ({written:,} rows, {time.time()-t0:.1f}s)"


def generate_sales_b():
    months = _months_between(DATE_START, DATE_END)
    month_rows = _distribute_rows(ROWS_FRANCHISE_B, len(months), ROWS_VARIANCE_PCT)

    tasks = []
    for (m_start, m_end), target in zip(months, month_rows):
        fname = os.path.join(OUTPUT_DIR_B, f"sales_monthly_{m_start:%Y_%m}.psv")
        tasks.append((fname, target, m_start, m_end, _fb_barcodes))

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_write_monthly_b, t): t for t in tasks}
        for f in as_completed(futures):
            print(f.result())


# ── RUN ──────────────────────────────────────────
if __name__ == "__main__":
    t_start = time.time()

    print("=== SEED: Master Company Data ===")
    os.makedirs(OUTPUT_DIR_MASTER, exist_ok=True)
    os.makedirs(OUTPUT_DIR_A, exist_ok=True)
    os.makedirs(OUTPUT_DIR_B, exist_ok=True)
    product_df = generate_product_master()
    customer_df = generate_customer_master()

    print("\n=== SEED: Franchise A Masters ===")
    generate_store_master()

    print("\n=== SEED: Franchise B Masters ===")
    generate_hub_master()
    mapping_df = generate_barcode_sku_mapping()

    print(f"\n=== SEED: Franchise A — {ROWS_FRANCHISE_A:,} rows ({MAX_WORKERS} workers) ===")
    generate_sales_a()

    print(f"\n=== SEED: Franchise B — {ROWS_FRANCHISE_B:,} rows ({MAX_WORKERS} workers) ===")
    generate_sales_b()

    print(f"\n=== SEED complete in {time.time()-t_start:.1f}s. Files in storage/landing_zone/ ===")
