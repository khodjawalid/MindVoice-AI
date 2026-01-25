"""
Dashboard API Router - Stress Inference and Score Aggregation.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import os

from app.db.supabase import supabase
from app.services.inference import StressInferenceEngine, StressInferConfig

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Path to model and data files - resolve from backend root
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent

MODEL_PATH = BACKEND_ROOT / "app" / "services" / "inference" / "wrist_eda_pr_global_xgb.joblib"
DATA_BASE_PATH = PROJECT_ROOT / "empatica"

# Environment variable override
if os.getenv("MODEL_PATH"):
    MODEL_PATH = Path(os.getenv("MODEL_PATH"))
if os.getenv("DATA_BASE_PATH"):
    DATA_BASE_PATH = Path(os.getenv("DATA_BASE_PATH"))

BATCH_SIZE = 1000

# Initialize inference engine (lazy loading)
_inference_engine: Optional[StressInferenceEngine] = None


def get_inference_engine() -> StressInferenceEngine:
    """Lazy load the inference engine."""
    global _inference_engine
    if _inference_engine is None:
        config = StressInferConfig(
            window_sec=60,
            step_sec=60,
            threshold=0.5,
            min_coverage=0.7
        )
        _inference_engine = StressInferenceEngine(MODEL_PATH, config)
    return _inference_engine


def get_processed_raw_paths(date: str) -> tuple[Optional[Path], Optional[Path]]:
    """Find EDA and HR raw CSV files for a given date."""
    # Look for empatica_{date} folder
    date_folder = DATA_BASE_PATH / f"empatica_{date}"
    if not date_folder.exists():
        return None, None
    
    processed_folder = date_folder / "processed_raw"
    if not processed_folder.exists():
        return None, None
    
    eda_path = processed_folder / f"eda_raw_{date}.csv"
    hr_path = processed_folder / f"hr_raw_{date}.csv"
    
    if not eda_path.exists() or not hr_path.exists():
        return None, None
    
    return eda_path, hr_path


def check_existing_scores(date: str) -> List[dict]:
    """Check if scores already exist for a date."""
    res = (
        supabase.table("stress_scores_aggregated")
        .select("*")
        .eq("record_date", date)
        .order("datetime_utc", desc=False)
        .execute()
    )
    return res.data if res.data else []


def store_inference_results(date: str, results_df) -> int:
    """Store inference results in Supabase."""
    if results_df.empty:
        return 0
    
    # Prepare records for insertion
    records = []
    for _, row in results_df.iterrows():
        if row["stress_proba"] is not None and not (isinstance(row["stress_proba"], float) and row["stress_proba"] != row["stress_proba"]):
            records.append({
                "record_date": date,
                "datetime_utc": row["window_start_iso_utc"],
                "stress_proba": float(row["stress_proba"]),
                "stress_pred": int(row["stress_pred"]),
                "eda_coverage": float(row["eda_coverage"]),
                "hr_coverage": float(row["hr_coverage"]),
            })
    
    if not records:
        return 0
    
    # Delete existing records for this date (must have a condition for Supabase)
    try:
        supabase.table("stress_scores_aggregated").delete().eq("record_date", date).execute()
    except Exception as e:
        print(f"Warning: Could not delete existing records: {e}")
    
    # Insert in batches
    inserted = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        result = supabase.table("stress_scores_aggregated").insert(batch).execute()
        inserted += len(result.data) if result.data else 0
    
    return inserted


def fetch_scores_by_date(date: str) -> List[dict]:
    """Fetch all stress scores for a specific date."""
    all_data = []
    offset = 0

    while True:
        res = (
            supabase.table("stress_scores_aggregated")
            .select("*")
            .eq("record_date", date)
            .order("datetime_utc", desc=False)
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )

        all_data.extend(res.data)

        if len(res.data) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    return all_data


def fetch_tags_by_date(date: str) -> List[dict]:
    """Fetch all reviewed tags for a specific date."""
    all_data = []
    offset = 0

    while True:
        res = (
            supabase.table("tags")
            .select("*")
            .eq("record_date", date)
            .order("timestamp", desc=False)
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )

        all_data.extend(res.data)

        if len(res.data) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    return all_data


def get_available_dashboard_dates() -> List[str]:
    """Get all dates that have processed raw data available."""
    dates = []
    
    if not DATA_BASE_PATH.exists():
        return dates
    
    for folder in DATA_BASE_PATH.iterdir():
        if folder.is_dir() and folder.name.startswith("empatica_"):
            date = folder.name.replace("empatica_", "")
            processed_folder = folder / "processed_raw"
            if processed_folder.exists():
                eda_file = processed_folder / f"eda_raw_{date}.csv"
                hr_file = processed_folder / f"hr_raw_{date}.csv"
                if eda_file.exists() and hr_file.exists():
                    dates.append(date)
    
    dates.sort(reverse=True)
    return dates


class InferenceResponse(BaseModel):
    status: str
    date: str
    rows_inserted: int
    summary: dict


class DashboardDataResponse(BaseModel):
    date: str
    scores: List[dict]
    tags: List[dict]
    summary: dict


@router.get("/dates")
def list_available_dates():
    """Return list of all dates that have processed raw data available."""
    dates = get_available_dashboard_dates()
    return {"dates": dates}


@router.post("/infer/{date}")
def run_inference(date: str, force: bool = False):
    """
    Run stress inference for a specific date.
    
    Args:
        date: Date in YYYY-MM-DD format
        force: If True, re-run inference even if results exist
    """
    # Check if data files exist
    eda_path, hr_path = get_processed_raw_paths(date)
    if eda_path is None or hr_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Processed raw data not found for date {date}"
        )
    
    # Check if scores already exist
    if not force:
        existing = check_existing_scores(date)
        if existing:
            return {
                "status": "already_exists",
                "date": date,
                "rows_count": len(existing),
                "message": "Scores already exist. Use force=true to re-run."
            }
    
    # Run inference
    try:
        engine = get_inference_engine()
        results_df = engine.infer_from_csv_files(eda_path, hr_path)
        summary = engine.get_summary_stats(results_df)
        
        # Store results
        rows_inserted = store_inference_results(date, results_df)
        
        return {
            "status": "success",
            "date": date,
            "rows_inserted": rows_inserted,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference failed: {str(e)}"
        )


@router.get("/data/{date}")
def get_dashboard_data(date: str, run_inference_if_missing: bool = True):
    """
    Get dashboard data for a specific date.
    Includes stress scores and reviewed tags.
    
    Args:
        date: Date in YYYY-MM-DD format
        run_inference_if_missing: If True, run inference if no scores exist
    """
    # Try to get existing scores
    scores = fetch_scores_by_date(date)
    
    # Run inference if no scores and data exists
    if not scores and run_inference_if_missing:
        eda_path, hr_path = get_processed_raw_paths(date)
        if eda_path is not None and hr_path is not None:
            try:
                engine = get_inference_engine()
                results_df = engine.infer_from_csv_files(eda_path, hr_path)
                store_inference_results(date, results_df)
                scores = fetch_scores_by_date(date)
            except Exception as e:
                # Log error but continue with empty scores
                print(f"Inference error for {date}: {e}")
    
    # Get tags
    tags = fetch_tags_by_date(date)
    reviewed_tags = [t for t in tags if t.get("reviewed")]
    
    # Calculate summary
    summary = {}
    if scores:
        valid_scores = [s for s in scores if s.get("stress_proba") is not None]
        if valid_scores:
            avg_proba = sum(s["stress_proba"] for s in valid_scores) / len(valid_scores)
            stress_count = sum(1 for s in valid_scores if s.get("stress_pred") == 1)
            summary = {
                "avg_stress_proba": round(avg_proba, 3),
                "stress_ratio": round(stress_count / len(valid_scores), 3),
                "total_windows": len(scores),
                "valid_windows": len(valid_scores),
            }
    
    return {
        "date": date,
        "scores": scores,
        "tags": tags,
        "reviewed_tags": reviewed_tags,
        "summary": summary,
        "has_data": len(scores) > 0
    }


@router.get("/summary/{date}")
def get_dashboard_summary(date: str):
    """
    Get a quick summary for a date without full data.
    """
    scores = check_existing_scores(date)
    tags = fetch_tags_by_date(date)
    reviewed_tags = [t for t in tags if t.get("reviewed")]

    summary = {}
    if scores:
        valid_scores = [s for s in scores if s.get("stress_proba") is not None]
        if valid_scores:
            avg_proba = sum(s["stress_proba"] for s in valid_scores) / len(valid_scores)
            stress_count = sum(1 for s in valid_scores if s.get("stress_pred") == 1)
            summary = {
                "avg_stress_proba": round(avg_proba, 3),
                "stress_ratio": round(stress_count / len(valid_scores), 3),
                "total_windows": len(scores),
                "valid_windows": len(valid_scores),
            }

    return {
        "date": date,
        "has_scores": len(scores) > 0,
        "scores_count": len(scores),
        "tags_count": len(tags),
        "reviewed_tags_count": len(reviewed_tags),
        "summary": summary
    }


def fetch_video_inferences_by_date(date: str) -> List[dict]:
    """Fetch all video inferences for a specific date."""
    all_data = []
    offset = 0

    while True:
        res = (
            supabase.table("video_inferences")
            .select("*")
            .eq("record_date", date)
            .order("created_at", desc=False)
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )

        all_data.extend(res.data)

        if len(res.data) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    return all_data


@router.get("/video-inferences/{date}")
def get_video_inferences(date: str):
    """
    Get all video emotion inferences for a specific date.

    Returns:
        Video inference results from multimodal (vision + audio) analysis
    """
    inferences = fetch_video_inferences_by_date(date)

    # Calculate summary if there are inferences
    summary = {}
    if inferences:
        # Aggregate emotion probabilities
        emotion_totals: dict[str, list] = {}
        for inference in inferences:
            probs = inference.get("emotion_probabilities", {})
            for emotion, prob in probs.items():
                if emotion not in emotion_totals:
                    emotion_totals[emotion] = []
                emotion_totals[emotion].append(prob)

        # Calculate averages
        emotion_averages = {
            emotion: sum(probs) / len(probs)
            for emotion, probs in emotion_totals.items()
            if probs
        }

        # Find dominant emotion
        dominant_emotion = max(emotion_averages.items(), key=lambda x: x[1]) if emotion_averages else (None, 0)

        summary = {
            "total_recordings": len(inferences),
            "dominant_emotion": dominant_emotion[0],
            "dominant_confidence": round(dominant_emotion[1], 3),
            "emotion_averages": {k: round(v, 3) for k, v in emotion_averages.items()},
        }

    return {
        "date": date,
        "data": inferences,
        "count": len(inferences),
        "summary": summary
    }
