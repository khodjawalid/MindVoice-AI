# app/api/routes/wellness.py
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import tempfile
import os

from app.db.supabase import supabase

router = APIRouter(prefix="/wellness", tags=["wellness"])

# Model paths for inference
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "models"
AUDIO_MODEL_PATH = MODELS_DIR / "best_model_audio.pt"
VIDEO_MODEL_PATH = MODELS_DIR / "best_model_image.pt"

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


class VideoInferenceResult(BaseModel):
    """Response model for video inference."""
    id: str
    tag_id: str
    predicted_emotion: str
    pred_confidence: float
    emotion_probabilities: dict


@router.post("/tags/{tag_id}/inference")
async def run_tag_video_inference(
    tag_id: str,
    video: UploadFile = File(..., description="Video file for emotion inference"),
):
    """
    Run video emotion inference for a specific tag.

    Uploads the video, runs late fusion inference (vision + audio),
    stores the result in the video_inferences table, and deletes the video.
    """
    # Verify tag exists and get its record_date
    tag_result = supabase.table("tags").select("*").eq("id", tag_id).execute()
    if not tag_result.data:
        raise HTTPException(status_code=404, detail="Tag not found")

    tag = tag_result.data[0]
    record_date = tag.get("record_date")

    if not record_date:
        raise HTTPException(status_code=400, detail="Tag has no record_date")

    # Validate models exist
    if not AUDIO_MODEL_PATH.exists() or not VIDEO_MODEL_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="ML models not found. Please ensure models are deployed."
        )

    # Validate file type
    content_type = video.content_type or ""
    if not content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {content_type}. Expected video file."
        )

    temp_path = None
    try:
        # Save uploaded video to temp file
        suffix = Path(video.filename or "video.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await video.read()
            tmp.write(content)
            temp_path = Path(tmp.name)

        # Run inference
        from app.services.late_fusion import run_inference_cached

        result = run_inference_cached(
            video_file=temp_path,
            audio_pt=AUDIO_MODEL_PATH,
            video_pt=VIDEO_MODEL_PATH,
        )

        # Store result in database
        inference_data = {
            "tag_id": tag_id,
            "record_date": record_date,
            "predicted_emotion": result["pred_label"],
            "pred_confidence": result["pred_confidence"],
            "emotion_probabilities": result["emotion_probabilities"],
        }

        db_result = supabase.table("video_inferences").insert(inference_data).execute()

        if not db_result.data:
            raise HTTPException(status_code=500, detail="Failed to store inference result")

        return VideoInferenceResult(
            id=db_result.data[0]["id"],
            tag_id=tag_id,
            predicted_emotion=result["pred_label"],
            pred_confidence=result["pred_confidence"],
            emotion_probabilities=result["emotion_probabilities"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
    finally:
        # Always clean up temp file
        if temp_path and temp_path.exists():
            try:
                os.unlink(temp_path)
            except Exception:
                pass


@router.get("/tags/{tag_id}/inference")
def get_tag_inference(tag_id: str):
    """Get the video inference result for a specific tag."""
    result = (
        supabase.table("video_inferences")
        .select("*")
        .eq("tag_id", tag_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return {"data": None, "message": "No inference found for this tag"}

    return {"data": result.data[0]}


# ========== Daily Video Inference Endpoints ==========


class DailyVideoInferenceResult(BaseModel):
    """Response model for daily video inference."""
    id: str
    record_date: str
    predicted_emotion: str
    pred_confidence: float
    emotion_probabilities: dict


@router.get("/daily-inference/{date}")
def get_daily_inference(date: str):
    """
    Get the daily video inference result for a specific date.

    Returns the inference result if it exists, or None if no daily video
    has been recorded for this date yet.
    """
    result = (
        supabase.table("daily_video_inferences")
        .select("*")
        .eq("record_date", date)
        .limit(1)
        .execute()
    )

    if not result.data:
        return {"data": None, "exists": False}

    return {"data": result.data[0], "exists": True}


@router.post("/daily-inference/{date}")
async def run_daily_video_inference(
    date: str,
    video: UploadFile = File(..., description="Daily video file for emotion inference"),
):
    """
    Run video emotion inference for a daily summary video.

    This endpoint is called after all tags for the day have been reviewed.
    The video captures the user's overall emotional state for the day.
    """
    # Check if daily inference already exists
    existing = (
        supabase.table("daily_video_inferences")
        .select("id")
        .eq("record_date", date)
        .limit(1)
        .execute()
    )

    if existing.data:
        # Delete existing inference to allow re-recording
        supabase.table("daily_video_inferences").delete().eq("record_date", date).execute()

    # Validate models exist
    if not AUDIO_MODEL_PATH.exists() or not VIDEO_MODEL_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="ML models not found. Please ensure models are deployed."
        )

    # Validate file type
    content_type = video.content_type or ""
    if not content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {content_type}. Expected video file."
        )

    temp_path = None
    try:
        # Save uploaded video to temp file
        suffix = Path(video.filename or "video.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await video.read()
            tmp.write(content)
            temp_path = Path(tmp.name)

        # Run inference
        from app.services.late_fusion import run_inference_cached

        result = run_inference_cached(
            video_file=temp_path,
            audio_pt=AUDIO_MODEL_PATH,
            video_pt=VIDEO_MODEL_PATH,
        )

        # Store result in daily_video_inferences table
        inference_data = {
            "record_date": date,
            "predicted_emotion": result["pred_label"],
            "pred_confidence": result["pred_confidence"],
            "emotion_probabilities": result["emotion_probabilities"],
        }

        db_result = supabase.table("daily_video_inferences").insert(inference_data).execute()

        if not db_result.data:
            raise HTTPException(status_code=500, detail="Failed to store inference result")

        return DailyVideoInferenceResult(
            id=db_result.data[0]["id"],
            record_date=date,
            predicted_emotion=result["pred_label"],
            pred_confidence=result["pred_confidence"],
            emotion_probabilities=result["emotion_probabilities"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
    finally:
        # Always clean up temp file
        if temp_path and temp_path.exists():
            try:
                os.unlink(temp_path)
            except Exception:
                pass
