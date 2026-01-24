# app/api/routes/metrics.py
from typing import Optional, List
from fastapi import APIRouter
from app.db.supabase import supabase

router = APIRouter(prefix="/metrics", tags=["metrics"])

BATCH_SIZE = 1000


def fetch_by_date(table: str, date: str, order_by: str = "datetime_utc") -> List[dict]:
    """Fetch all rows from a table for a specific date."""
    all_data = []
    offset = 0

    while True:
        res = (
            supabase.table(table)
            .select("*")
            .eq("record_date", date)
            .order(order_by, desc=False)
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )

        all_data.extend(res.data)

        if len(res.data) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    return all_data


def get_available_dates() -> List[str]:
    """Get all distinct dates that have data (from hr_aggregated as reference)."""
    res = (
        supabase.table("hr_aggregated")
        .select("record_date")
        .order("record_date", desc=True)
        .execute()
    )

    # Extract unique dates
    dates = list(set(row["record_date"] for row in res.data))
    dates.sort(reverse=True)
    return dates


def get_latest_date() -> Optional[str]:
    """Get the most recent date with data."""
    dates = get_available_dates()
    return dates[0] if dates else None


@router.get("/")
def get_metrics(date: Optional[str] = None):
    """
    Fetch metrics for a specific date.

    If no date is provided, returns the most recent available date.
    Returns HR data, EDA data, and tags for the specified date.
    """
    # Default to latest date if not specified
    if date is None:
        date = get_latest_date()

    if date is None:
        return {
            "date": None,
            "hr": [],
            "eda": [],
            "tags": [],
            "message": "No data available",
        }

    # Fetch from new tables
    hr_data = fetch_by_date("hr_aggregated", date)
    eda_data = fetch_by_date("eda_aggregated", date)
    tags_data = fetch_by_date("tags", date, order_by="timestamp")

    return {
        "date": date,
        "hr": hr_data,
        "eda": eda_data,
        "tags": tags_data,
    }


@router.get("/dates")
def list_available_dates():
    """Return list of all dates that have data, sorted descending (most recent first)."""
    dates = get_available_dates()
    return {"dates": dates}
