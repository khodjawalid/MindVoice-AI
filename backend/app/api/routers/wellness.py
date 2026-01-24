# app/api/routes/wellness.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.supabase import supabase

router = APIRouter(prefix="/wellness", tags=["wellness"])

BATCH_SIZE = 1000


def fetch_all_rows(table: str, select: str, filters: Optional[dict] = None, order_by: Optional[str] = None):
    """Fetch all rows from a table using pagination (Supabase default limit is 1000)."""
    all_data = []
    offset = 0

    while True:
        query = supabase.table(table).select(select)

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        if order_by:
            query = query.order(order_by, desc=False)

        query = query.range(offset, offset + BATCH_SIZE - 1)
        res = query.execute()

        all_data.extend(res.data)

        if len(res.data) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    return all_data


class TagReviewUpdate(BaseModel):
    emotion_label: Optional[str] = None
    stress_level: Optional[int] = None
    video_url: Optional[str] = None
    reviewed: Optional[bool] = None


@router.get("/init")
def init_tag_reviews():
    """Create tag_reviews for each has_tag=true in biometrics_demo"""

    # Get all biometrics with has_tag=true
    tagged = fetch_all_rows(
        table="biometrics_demo",
        select="id, timestamp_unix",
        filters={"has_tag": True}
    )

    # Get existing reviews
    existing = fetch_all_rows(
        table="tag_reviews",
        select="biometric_id"
    )
    existing_ids = {r["biometric_id"] for r in existing}

    # Insert new ones only
    new_reviews = [
        {
            "biometric_id": bio["id"],
            "timestamp_unix": bio["timestamp_unix"],
            "reviewed": False
        }
        for bio in tagged
        if bio["id"] not in existing_ids
    ]

    if new_reviews:
        supabase.table("tag_reviews").insert(new_reviews).execute()

    return {
        "tags_found": len(tagged),
        "reviews_created": len(new_reviews)
    }


@router.get("/tags")
def get_tags():
    """Get all tag reviews"""
    data = fetch_all_rows(
        table="tag_reviews",
        select="*",
        order_by="timestamp_unix"
    )
    return {"data": data, "count": len(data)}


@router.get("/tags/pending")
def get_pending_tags():
    """Get unreviewed tags only"""
    data = fetch_all_rows(
        table="tag_reviews",
        select="*",
        filters={"reviewed": False},
        order_by="timestamp_unix"
    )
    return {"data": data, "count": len(data)}


@router.patch("/tags/{review_id}")
def update_tag(review_id: str, update: TagReviewUpdate):
    """Update a tag review"""
    
    data = update.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    result = supabase.table("tag_reviews").update(data).eq("id", review_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Review not found")

    return {"data": result.data[0]}