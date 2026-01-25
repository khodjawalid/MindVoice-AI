"""
Signal Uploader Service

Uploads processed Empatica signals to Supabase tables:
- eda_aggregated: EDA per-minute aggregations
- hr_aggregated: HR per-minute aggregations
- tags: User-tagged events
"""

import math
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

from app.db.supabase import supabase


def json_safe(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a record for JSON serialization.

    Converts NaN/Inf floats to None and handles pandas Timestamps.
    """
    clean = {}
    for k, v in record.items():
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                clean[k] = None
            else:
                clean[k] = v
        elif isinstance(v, pd.Timestamp):
            clean[k] = v.isoformat()
        else:
            clean[k] = v
    return clean


class SignalUploader:
    """
    Uploads the 3 aggregated signals to their Supabase tables.

    Tables:
    - eda_aggregated: ~1.4K rows/day
    - hr_aggregated: ~1.4K rows/day
    - tags: ~12 rows/day
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the uploader.

        Args:
            base_dir: Base directory for processed data.
                      Defaults to EMPATICA_LOCAL_DIR env var or ./empatica_data
        """
        self.base_dir = Path(
            base_dir or os.getenv("EMPATICA_LOCAL_DIR", "./empatica_data")
        )

    def date_exists(self, date: str) -> bool:
        """Check if data for this date already exists in Supabase."""
        result = (
            supabase.table("hr_aggregated")
            .select("record_date")
            .eq("record_date", date)
            .limit(1)
            .execute()
        )
        return len(result.data) > 0

    def get_available_dates(self) -> list[str]:
        """Get all dates that have processed data on disk."""
        dates = []
        if not self.base_dir.exists():
            return dates
        for folder in self.base_dir.iterdir():
            if folder.is_dir() and folder.name.startswith("empatica_"):
                date = folder.name.replace("empatica_", "")
                processed_dir = folder / "processed_raw"
                if processed_dir.exists() and any(processed_dir.iterdir()):
                    dates.append(date)
        dates.sort(reverse=True)
        return dates

    def upload_day(self, date: str, force: bool = False) -> Dict[str, Any]:
        """
        Upload all signals for a given date to Supabase.

        Args:
            date: Date string in YYYY-MM-DD format (e.g., "2026-01-22")
            force: If True, overwrite existing data. If False, skip if data exists.

        Returns:
            Dict with results for each table upload
        """
        if not force and self.date_exists(date):
            return {
                "status": "skipped",
                "reason": "already_exists",
                "date": date,
            }

        results = {}
        results["eda_aggregated"] = self._upload_eda_aggregated(date)
        results["hr_aggregated"] = self._upload_hr_aggregated(date)
        results["tags"] = self._upload_tags(date)
        return results

    def _get_processed_dir(self, date: str) -> Path:
        """Get the processed_raw directory for a given date."""
        return self.base_dir / f"empatica_{date}" / "processed_raw"

    def _upload_eda_aggregated(self, date: str) -> Dict:
        """Upload EDA per-minute data to eda_aggregated table."""
        csv_path = self._get_processed_dir(date) / f"eda_per_minute_{date}.csv"

        if not csv_path.exists():
            return {
                "status": "skipped",
                "reason": "file_not_found",
                "path": str(csv_path),
            }

        df = pd.read_csv(csv_path)

        # Add record_date column
        df["record_date"] = date

        # Prepare records
        records = [json_safe(r) for r in df.to_dict(orient="records")]

        if not records:
            return {"status": "skipped", "reason": "no_data"}

        try:
            # Delete existing data for this date (idempotent)
            supabase.table("eda_aggregated").delete().eq(
                "record_date", date
            ).execute()

            # Insert new data
            supabase.table("eda_aggregated").insert(records).execute()

            return {
                "status": "success",
                "rows_uploaded": len(records),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def _upload_hr_aggregated(self, date: str) -> Dict:
        """Upload HR per-minute data to hr_aggregated table."""
        csv_path = self._get_processed_dir(date) / f"hr_per_minute_{date}.csv"

        if not csv_path.exists():
            return {
                "status": "skipped",
                "reason": "file_not_found",
                "path": str(csv_path),
            }

        df = pd.read_csv(csv_path)

        # Add record_date column
        df["record_date"] = date

        # Prepare records
        records = [json_safe(r) for r in df.to_dict(orient="records")]

        if not records:
            return {"status": "skipped", "reason": "no_data"}

        try:
            # Delete existing data for this date (idempotent)
            supabase.table("hr_aggregated").delete().eq(
                "record_date", date
            ).execute()

            # Insert new data
            supabase.table("hr_aggregated").insert(records).execute()

            return {
                "status": "success",
                "rows_uploaded": len(records),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def _upload_tags(self, date: str) -> Dict:
        """Upload tags data to tags table."""
        csv_path = self._get_processed_dir(date) / f"tags_raw_{date}.csv"

        if not csv_path.exists():
            return {
                "status": "skipped",
                "reason": "file_not_found",
                "path": str(csv_path),
            }

        df = pd.read_csv(csv_path)

        # Add record_date column
        df["record_date"] = date

        # Prepare records
        records = [json_safe(r) for r in df.to_dict(orient="records")]

        if not records:
            return {"status": "skipped", "reason": "no_data"}

        try:
            # Delete existing data for this date (idempotent)
            supabase.table("tags").delete().eq("record_date", date).execute()

            # Insert new data
            supabase.table("tags").insert(records).execute()

            return {
                "status": "success",
                "rows_uploaded": len(records),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
