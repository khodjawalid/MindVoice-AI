"""
Video Inference Router

Handles video upload and multimodal emotion inference.

Supports two backends:
1. Hume AI Expression Measurement API (recommended for production/demo)
2. Local late fusion models (ResNet-18 + Wav2Vec2) as fallback

Set USE_HUME_INFERENCE=true in .env to use Hume AI (requires HUME_API_KEY)
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from pathlib import Path
import tempfile
import os
from typing import Optional

router = APIRouter(prefix="/inference", tags=["inference"])

# Configuration
USE_HUME = os.getenv("USE_HUME_INFERENCE", "true").lower() == "true"
HUME_API_KEY = os.getenv("HUME_API_KEY")

# Model paths for fallback (relative to backend directory)
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "models"
AUDIO_MODEL_PATH = MODELS_DIR / "best_model_audio.pt"
VIDEO_MODEL_PATH = MODELS_DIR / "best_model_image.pt"


class InferenceResult(BaseModel):
    """Response model for video inference."""
    labels_9: list[str]
    probs_9: list[float]
    pred_label: str
    pred_confidence: float
    emotion_probabilities: dict[str, float]
    backend: Optional[str] = None  # "hume" or "local"


class InferenceError(BaseModel):
    """Error response model."""
    detail: str


@router.post(
    "/video",
    response_model=InferenceResult,
    responses={
        400: {"model": InferenceError, "description": "Invalid video file"},
        500: {"model": InferenceError, "description": "Inference failed"},
    },
)
async def run_video_inference(
    video: UploadFile = File(..., description="Video file (mp4, webm, etc.)"),
    face_weight: float = 0.5,
    prosody_weight: float = 0.5,
    num_frames: int = 16,
    use_hume: Optional[bool] = None,
):
    """
    Run multimodal emotion inference on an uploaded video.

    The video is processed through either:
    - Hume AI Expression Measurement API (recommended, set USE_HUME_INFERENCE=true)
    - Local models: Vision (ResNet-18) + Audio (Wav2Vec2) with late fusion

    Returns probabilities for 9 emotions:
    anger, calm, contempt, disgust, fear, happy, neutral, sad, surprise
    """
    # Determine which backend to use
    should_use_hume = use_hume if use_hume is not None else USE_HUME
    
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

        if should_use_hume and HUME_API_KEY:
            # Use Hume AI API
            from app.services.hume_inference import run_hume_inference
            
            result = await run_hume_inference(
                video_path=temp_path,
                face_weight=face_weight,
                prosody_weight=prosody_weight,
                timeout=120
            )
            result["backend"] = "hume"
            
        else:
            # Fallback to local models
            if not AUDIO_MODEL_PATH.exists() or not VIDEO_MODEL_PATH.exists():
                raise HTTPException(
                    status_code=500,
                    detail="Local models not found and HUME_API_KEY not configured. "
                           "Please add HUME_API_KEY to your .env file."
                )
            
            from app.services.late_fusion import run_inference_cached

            result = run_inference_cached(
                video_file=temp_path,
                audio_pt=AUDIO_MODEL_PATH,
                video_pt=VIDEO_MODEL_PATH,
                wa=prosody_weight,  # Map prosody weight to audio
                wv=face_weight,     # Map face weight to video
                num_frames=num_frames,
            )
            result["backend"] = "local"

        return InferenceResult(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
    finally:
        # Always clean up temp file
        if temp_path and temp_path.exists():
            try:
                os.unlink(temp_path)
            except Exception:
                pass


@router.get("/health")
async def inference_health():
    """Check if inference service is ready."""
    audio_ok = AUDIO_MODEL_PATH.exists()
    video_ok = VIDEO_MODEL_PATH.exists()
    hume_ok = bool(HUME_API_KEY)

    if hume_ok:
        status = "ok"
        primary_backend = "hume"
    elif audio_ok and video_ok:
        status = "ok"
        primary_backend = "local"
    else:
        status = "not_configured"
        primary_backend = None

    return {
        "status": status,
        "primary_backend": primary_backend,
        "hume_configured": hume_ok,
        "use_hume_default": USE_HUME,
        "local_models": {
            "audio_model": str(AUDIO_MODEL_PATH),
            "audio_model_exists": audio_ok,
            "video_model": str(VIDEO_MODEL_PATH),
            "video_model_exists": video_ok,
        }
    }
