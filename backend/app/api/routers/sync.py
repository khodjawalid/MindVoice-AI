from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

from app.services.empatica.s3_sync import (
    sync_empatica_day,
    create_s3_client,
    get_utc_yesterday,
)
from app.services.empatica.avro_processor import process_empatica_avro, find_avro_files
from app.services.migration import SignalUploader
from pathlib import Path

router = APIRouter(prefix="/sync", tags=["sync"])


def has_avro_data(local_dir: str) -> bool:
    """Check if the local directory has AVRO files to process."""
    _, avro_files = find_avro_files(Path(local_dir))
    return len(avro_files) > 0


class EmpaticaSyncRequest(BaseModel):
    date: Optional[str] = None


@router.post("/empatica")
def sync_empatica(payload: EmpaticaSyncRequest):
    try:
        # 1️⃣ Date logic
        date = payload.date or get_utc_yesterday()

        local_base_dir = os.getenv("EMPATICA_LOCAL_DIR", "./empatica_data")
        local_dir = os.path.join(local_base_dir, f"empatica_{date}")

        # 2️⃣ Folder exists with AVRO data → skip S3 sync, process AVRO
        # Folder exists but empty → try to sync anyway
        if os.path.exists(local_dir) and has_avro_data(local_dir):
            processing_result = process_empatica_avro(
                local_dir=local_dir,
                date=date,
            )
            return {
                "status": "skipped",
                "date": date,
                "reason": "already_synced",
                "local_dir": local_dir,
                "processing": processing_result,
            }

        # 3️⃣ S3 client
        s3_client = create_s3_client(
            access_key=os.getenv("EMPATICA_ACCESS_KEY_ID"),
            secret_key=os.getenv("EMPATICA_SECRET_ACCESS_KEY"),
            region=os.getenv("EMPATICA_S3_REGION", "us-east-1"),
        )

        # 4️⃣ Sync
        local_dir = sync_empatica_day(
            date=date,
            bucket_name=os.getenv("EMPATICA_S3_BUCKET"),
            prefix_root=os.getenv("EMPATICA_S3_PREFIX"),
            device_serial=os.getenv("EMPATICA_DEVICE_SERIAL"),
            local_base_dir=local_base_dir,
            s3_client=s3_client,
        )

        # Process AVRO files after sync
        processing_result = process_empatica_avro(
            local_dir=local_dir,
            date=date,
        )

        return {
            "status": "success",
            "date": date,
            "local_dir": local_dir,
            "processing": processing_result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Empatica sync failed: {str(e)}",
        )


@router.get("/available-dates")
def get_available_dates():
    """
    Get all dates that have processed Empatica data on disk.

    Returns:
        List of dates in YYYY-MM-DD format, sorted descending.
    """
    uploader = SignalUploader()
    return {"dates": uploader.get_available_dates()}


@router.post("/migrate/{date}")
def migrate_signals(date: str, force: bool = False):
    """
    Migrate the 3 aggregated signals for a date to Supabase.

    Uploads to tables:
    - eda_aggregated: EDA per-minute (~1.4K rows/day)
    - hr_aggregated: HR per-minute (~1.4K rows/day)
    - tags: User-tagged events (~12 rows/day)

    Args:
        date: Date in YYYY-MM-DD format
        force: If True, overwrite existing data. If False, skip if data exists.
    """
    try:
        uploader = SignalUploader()
        results = uploader.upload_day(date, force=force)

        # Check if skipped
        if results.get("status") == "skipped":
            return results

        # Check if any uploads failed
        errors = [
            (table, result)
            for table, result in results.items()
            if result.get("status") == "error"
        ]

        if errors:
            return {
                "status": "partial_failure",
                "date": date,
                "results": results,
            }

        return {
            "status": "success",
            "date": date,
            "results": results,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}",
        )


@router.post("/migrate-all")
def migrate_all_signals():
    """
    Migrate all dates that have processed data on disk but not in Supabase.

    This endpoint is safe to call multiple times - it will skip dates that
    already have data in Supabase.

    Returns:
        Dict with results for each date.
    """
    try:
        uploader = SignalUploader()
        available_dates = uploader.get_available_dates()

        if not available_dates:
            return {
                "status": "no_data",
                "message": "No processed data found on disk",
            }

        results = {}
        for date in available_dates:
            results[date] = uploader.upload_day(date, force=False)

        # Count successes and skips
        migrated = [d for d, r in results.items() if r.get("status") != "skipped"]
        skipped = [d for d, r in results.items() if r.get("status") == "skipped"]

        return {
            "status": "success",
            "migrated_count": len(migrated),
            "skipped_count": len(skipped),
            "results": results,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}",
        )
