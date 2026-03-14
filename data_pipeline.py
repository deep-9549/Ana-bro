import polars as pl
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
RAW_CSV     = "data/raw_data.csv"
OUTPUT_FILE = "data/optimized_data.parquet"

# ── Sanity check ───────────────────────────────────────────────────────────────
if not os.path.exists(RAW_CSV):
    raise FileNotFoundError(
        f"Could not find '{RAW_CSV}'.\n"
        "Make sure 2019-Oct.csv is renamed/moved to data/raw_data.csv"
    )

print("🔍 Scanning CSV with Polars LazyFrame (no RAM overload)...")

# ── Step 1: Lazy scan — does NOT load into memory ──────────────────────────────
lf = pl.scan_csv(RAW_CSV, try_parse_dates=False)

# ── Step 2: Select only the columns we need ────────────────────────────────────
lf = lf.select([
    "event_time",
    "event_type",
    "product_id",
    "category_code",
    "brand",
    "price",
    "user_id",
])

# ── Step 3: Drop rows with nulls in critical columns ──────────────────────────
lf = lf.filter(
    pl.col("price").is_not_null() &
    pl.col("category_code").is_not_null() &
    pl.col("brand").is_not_null()
)

# ── Step 4: Feature engineering ───────────────────────────────────────────────
# Parse event_time string → Datetime, then extract Date and Hour
lf = lf.with_columns([
    pl.col("event_time")
      .str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S UTC", strict=False)
      .alias("event_time")
])

lf = lf.with_columns([
    pl.col("event_time").dt.date().alias("date"),
    pl.col("event_time").dt.hour().alias("hour"),
])

# Extract top-level category from 'electronics.smartphone' → 'electronics'
lf = lf.with_columns([
    pl.col("category_code")
      .str.split(".")
      .list.first()
      .alias("category_top")
])

# ── Step 5: Stream directly to Parquet — never loads full data into RAM ────────
print("⚙️  Processing and writing to Parquet (this may take 30–60 seconds)...")
lf.sink_parquet(OUTPUT_FILE, compression="snappy")

print(f"✅ Done! Optimized file saved → {OUTPUT_FILE}")

# ── Step 6: Quick validation ───────────────────────────────────────────────────
print("\n📊 Quick preview of processed data:")
df = pl.read_parquet(OUTPUT_FILE)
print(f"   Rows    : {df.shape[0]:,}")
print(f"   Columns : {df.shape[1]}")
print(f"   Columns : {df.columns}")
print(f"\n   Event types : {df['event_type'].unique().to_list()}")
print(f"   Date range  : {df['date'].min()} → {df['date'].max()}")
print(f"   Top categories: {df['category_top'].value_counts().head(5)}")
print("\n🚀 Pipeline complete. Ready for Phase 3!")