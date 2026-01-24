# app/api/routes/wellness.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.db.supabase import supabase

router = APIRouter(prefix="/wellness", tags=["wellness"])

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
    """Get all distinct dates that have tags."""
    res = (
        supabase.table("tags")
        .select("record_date")
        .order("record_date", desc=True)
        .execute()
    )

    # Extract unique dates
    dates = list(set(row["record_date"] for row in res.data))
    dates.sort(reverse=True)
    return dates


def get_latest_date() -> Optional[str]:
    """Get the most recent date with tags."""
    dates = get_available_dates()
    return dates[0] if dates else None


class TagUpdate(BaseModel):
    emotion_label: Optional[str] = None
    stress_level: Optional[int] = None
    video_url: Optional[str] = None
    reviewed: Optional[bool] = None


@router.get("/dates")
def list_available_dates():
    """Return list of all dates that have tags, sorted descending."""
    dates = get_available_dates()
    return {"dates": dates}


@router.get("/tags")
def get_tags(date: Optional[str] = None):
    """Get all tags for a specific date."""
    # Default to latest date if not specified
    if date is None:
        date = get_latest_date()

    if date is None:
        return {"date": None, "data": [], "count": 0, "message": "No data available"}

    # Fetch all tags for the date
    data = fetch_by_date("tags", date, order_by="timestamp")

    return {"date": date, "data": data, "count": len(data)}


@router.get("/tags/pending")
def get_pending_tags(date: Optional[str] = None):
    """Get unreviewed tags only for a specific date."""
    if date is None:
        date = get_latest_date()

    if date is None:
        return {"date": None, "data": [], "count": 0}

    all_data = []
    offset = 0

    while True:
        res = (
            supabase.table("tags")
            .select("*")
            .eq("record_date", date)
            .eq("reviewed", False)
            .order("timestamp", desc=False)
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )

        all_data.extend(res.data)

        if len(res.data) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    return {"date": date, "data": all_data, "count": len(all_data)}


@router.patch("/tags/{tag_id}")
def update_tag(tag_id: str, update: TagUpdate):
    """Update a tag with review data (emotion, stress level, etc.)."""

    data = update.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    result = (
        supabase.table("tags").update(data).eq("id", tag_id).execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Tag not found")

    return {"data": result.data[0]}
