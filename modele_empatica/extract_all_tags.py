from fastavro import reader
from datetime import datetime, timezone
import pandas as pd
from pathlib import Path

AVRO_DIR = Path(r"C:\Users\amira\empatica_2026-01-16\raw_data\v6")

def micros_to_dt_utc(micros: int):
    return datetime.fromtimestamp(micros / 1e6, tz=timezone.utc)

all_tags = []

for avro_file in AVRO_DIR.glob("*.avro"):
    try:
        with open(avro_file, "rb") as f:
            r = reader(f)
            records = list(r)
            if not records:
                continue

            rec = records[0]
            tags = rec.get("rawData", {}).get("tags", {})
            tags_list = tags.get("tagsTimeMicros", [])

            for t in tags_list:
                all_tags.append({
                    "tag_time_micros": t,
                    "tag_time_iso_utc": micros_to_dt_utc(t).isoformat(),
                    "source_file": avro_file.name
                })
    except Exception as e:
        print("Error reading", avro_file.name, e)

df = pd.DataFrame(all_tags)
out = AVRO_DIR / "tags_all.csv"
df.to_csv(out, index=False)

print("Total tags found:", len(df))
print("Saved:", out)
