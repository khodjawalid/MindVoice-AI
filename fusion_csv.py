# Fusion data CSV files into a single CSV file.
import numpy as np
import pandas as pd
from pathlib import Path

## Configuration
date = "2026-01-16"
PARENT_DIR = Path(__file__).resolve().parent / f"empatica_{date}"
eda_path = PARENT_DIR / f"digital_biomarkers/aggregated_per_minute/1-1-28_{date}_eda.csv"
hr_path  = PARENT_DIR / f"digital_biomarkers/aggregated_per_minute/1-1-28_{date}_pulse-rate.csv"
tags_path = PARENT_DIR / "processed" / f"tags_{date}.csv"
# Load data
eda_df = pd.read_csv(eda_path)
hr_df = pd.read_csv(hr_path)
tags_df = pd.read_csv(tags_path)

def round_unix(timestamp_unix: int) -> int:
    return (timestamp_unix + 30000) // 60000 * 60000

print(tags_df.head())

# Convert tags timestamps from microseconds to milliseconds
# Tags are in microseconds (1e6), but EDA/HR data is in milliseconds (1e3)
tags_df["timestamp_unix"] = tags_df["timestamp_unix"] // 1000

# Modify timestamp_unix in tags_df to match minute granularity using round_unix
tags_df["timestamp_unix"] = tags_df["timestamp_unix"].apply(round_unix)

# Create a simple binary indicator: keep only unique timestamps that have tags
tags_df = tags_df[["timestamp_unix"]].drop_duplicates()
tags_df["has_tag"] = 1

# Merge dataframes sequentially (pd.merge can only merge 2 dataframes at a time)
merged_df = pd.merge(
    eda_df,
    hr_df,
    on="timestamp_unix",
    how="outer",
    suffixes=("_eda", "_hr")
)

# Left join with tags to keep all EDA/HR timestamps, add has_tag column
merged_df = pd.merge(
    merged_df,
    tags_df,
    on="timestamp_unix",
    how="left"
)

# Fill NaN values in has_tag with 0 (no tag present)
merged_df["has_tag"] = merged_df["has_tag"].fillna(0).astype(int)


# Rename columns appropriately based on the merge suffixes
clean_df = merged_df.rename(columns={
    "timestamp_iso_eda": "timestamp_iso",
})

# Combine EDA columns: use value if available, otherwise use missing reason
# After merge with suffixes, missing_value_reason becomes missing_value_reason_eda
if "eda_scl_usiemens" in clean_df.columns:
    if "missing_value_reason_eda" in clean_df.columns:
        # Use EDA value if present, otherwise use missing reason
        clean_df["eda"] = clean_df["eda_scl_usiemens"].fillna(clean_df["missing_value_reason_eda"])
    else:
        # If no missing reason column, just use the EDA value
        clean_df["eda"] = clean_df["eda_scl_usiemens"]
    clean_df = clean_df.drop(columns=["eda_scl_usiemens"])
    if "missing_value_reason_eda" in clean_df.columns:
        clean_df = clean_df.drop(columns=["missing_value_reason_eda"])

# Combine HR columns: use value if available, otherwise use missing reason
# After merge with suffixes, missing_value_reason becomes missing_value_reason_hr
if "pulse_rate_bpm" in clean_df.columns:
    if "missing_value_reason_hr" in clean_df.columns:
        # Use HR value if present, otherwise use missing reason
        clean_df["heart_rate"] = clean_df["pulse_rate_bpm"].fillna(clean_df["missing_value_reason_hr"])
    else:
        # If no missing reason column, just use the HR value
        clean_df["heart_rate"] = clean_df["pulse_rate_bpm"]
    clean_df = clean_df.drop(columns=["pulse_rate_bpm"])
    if "missing_value_reason_hr" in clean_df.columns:
        clean_df = clean_df.drop(columns=["missing_value_reason_hr"])

# Drop duplicate columns and unnecessary columns
columns_to_drop = []
if "participant_full_id_eda" in clean_df.columns:
    columns_to_drop.append("participant_full_id_eda")
if "participant_full_id_hr" in clean_df.columns:
    columns_to_drop.append("participant_full_id_hr")
if "timestamp_iso_hr" in clean_df.columns:
    columns_to_drop.append("timestamp_iso_hr")
# Remove tag detail columns (we only keep has_tag)
if "tag_time_iso_utc" in clean_df.columns:
    columns_to_drop.append("tag_time_iso_utc")
if "source_file" in clean_df.columns:
    columns_to_drop.append("source_file")

if columns_to_drop:
    clean_df = clean_df.drop(columns=columns_to_drop)

# output in processed folder (use different name to avoid overwriting source tags file)
output_path = PARENT_DIR / "processed" / f"merged_data_{date}.csv"
clean_df.to_csv(output_path, index=False)
print(f"✅ Merged data saved to: {output_path}")