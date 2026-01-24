from pathlib import Path
from fastavro import reader
import pandas as pd
from datetime import datetime, timezone

# --------- CONFIG ----------
date = "2026-01-16"
AVRO_DIR = Path(f"./empatica_{date}/raw_data/v6")
OUT_DIR  = Path(f"./empatica_{date}/processed_raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)
# --------------------------

def micros_to_dt_utc(micros: int):
    return datetime.fromtimestamp(micros / 1e6, tz=timezone.utc)

def extract_stream(rec: dict, stream_name: str, value_key: str = "values"):
    raw = rec.get("rawData", {})
    stream = raw.get(stream_name)
    if not isinstance(stream, dict):
        return None
    ts0 = stream.get("timestampStart")
    fs  = stream.get("samplingFrequency")
    vals = stream.get(value_key)
    return ts0, fs, vals

def build_time_axis_micros(ts0_micros: int, fs: float, n: int):
    step = int(round(1_000_000 / fs))
    return [ts0_micros + i * step for i in range(n)]

eda_rows = []
bvp_rows = []
tag_rows = []

avro_files = sorted(AVRO_DIR.glob("*.avro"))
print("AVRO files:", len(avro_files))

for fp in avro_files:
    try:
        with open(fp, "rb") as f:
            r = reader(f)
            for rec in r:
                # ---------- TAGS ----------
                tags = rec.get("rawData", {}).get("tags", {})
                tags_list = tags.get("tagsTimeMicros", []) or []
                for t in tags_list:
                    tag_rows.append({
                        "timestamp_unix_micros": int(t),
                        "tag_time_iso_utc": micros_to_dt_utc(int(t)).isoformat(),
                        "source_file": fp.name
                    })

                # ---------- EDA ----------
                eda_data = extract_stream(rec, "eda", value_key="values")
                if eda_data is not None:
                    ts0, fs, vals = eda_data
                    if ts0 is not None and fs and isinstance(vals, list) and len(vals) > 0:
                        t_micros = build_time_axis_micros(int(ts0), float(fs), len(vals))
                        eda_rows.extend(
                            {"timestamp_unix_micros": t, "eda_raw": float(v), "source_file": fp.name}
                            for t, v in zip(t_micros, vals)
                        )

                # ---------- BVP ----------
                bvp_data = extract_stream(rec, "bvp", value_key="values")
                if bvp_data is not None:
                    ts0, fs, vals = bvp_data
                    if ts0 is not None and fs and isinstance(vals, list) and len(vals) > 0:
                        t_micros = build_time_axis_micros(int(ts0), float(fs), len(vals))
                        bvp_rows.extend(
                            {"timestamp_unix_micros": t, "bvp_raw": float(v), "source_file": fp.name}
                            for t, v in zip(t_micros, vals)
                        )

    except Exception as e:
        print("Error reading", fp.name, e)

# Save EDA/BVP
if eda_rows:
    eda_df = pd.DataFrame(eda_rows).sort_values("timestamp_unix_micros")
    eda_out = OUT_DIR / f"eda_raw_{date}.csv"
    eda_df.to_csv(eda_out, index=False)
    print("✅ EDA saved:", eda_out, "| rows:", len(eda_df))

if bvp_rows:
    bvp_df = pd.DataFrame(bvp_rows).sort_values("timestamp_unix_micros")
    bvp_out = OUT_DIR / f"bvp_raw_{date}.csv"
    bvp_df.to_csv(bvp_out, index=False)
    print("✅ BVP saved:", bvp_out, "| rows:", len(bvp_df))

# Save TAGS
if tag_rows:
    tags_df = pd.DataFrame(tag_rows).sort_values("timestamp_unix_micros")
    tags_out = OUT_DIR / f"tags_raw_{date}.csv"
    tags_df.to_csv(tags_out, index=False)
    print("✅ TAGS saved:", tags_out, "| rows:", len(tags_df))
else:
    print("⚠️ No TAGS extracted (possible: no tags on that day)")
