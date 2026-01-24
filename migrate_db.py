from supabase import create_client
from dotenv import load_dotenv
import os
import pandas as pd
import numpy as np
import math

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)

# Sanity check
res = supabase.table("biometrics_demo").select("*").limit(1).execute()
print("Supabase connection OK:", res)

# Load CSV
date = "2026-01-16"
csv_path = f"./empatica_{date}/processed/merged_data_{date}.csv"
assert os.path.exists(csv_path), "CSV file not found"

df = pd.read_csv(csv_path)
print(f"CSV loaded: {len(df)} rows")

# Keep only required columns
df = df[
    ["timestamp_unix", "timestamp_iso", "eda", "heart_rate", "has_tag"]
]

# Force numeric
df["eda"] = pd.to_numeric(df["eda"], errors="coerce")
df["heart_rate"] = pd.to_numeric(df["heart_rate"], errors="coerce")

# Convert has_tag
df["has_tag"] = df["has_tag"].astype(bool)

# Prepare records safely
def json_safe(record: dict) -> dict:
    clean = {}
    for k, v in record.items():
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                clean[k] = None
            else:
                clean[k] = v
        else:
            clean[k] = v
    return clean

raw_records = df.to_dict(orient="records")
records = [json_safe(r) for r in raw_records]

# Insert
supabase.table("biometrics_demo").insert(records).execute()
print(f"✅ Inserted {len(records)} rows into Supabase")
