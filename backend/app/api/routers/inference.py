"""
Video Inference Router

Handles video upload and multimodal emotion inference using late fusion
of vision (ResNet-18) and audio (Wav2Vec2) models.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from pathlib import Path
import tempfile
import os
from typing import Optional

router = APIRouter(prefix="/inference", tags=["inference"])

# Model paths (relative to backend directory)
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
    audio_weight: float = 0.5,
    video_weight: float = 0.5,
    num_frames: int = 16,
):
    """
    Run multimodal emotion inference on an uploaded video.

    The video is processed through:
    1. Vision model (ResNet-18): Facial expression analysis
    2. Audio model (Wav2Vec2): Speech emotion recognition
    3. Late fusion: Combines both modalities

    Returns probabilities for 9 emotions:
    anger, calm, contempt, disgust, fear, happy, neutral, sad, surprise
    """
    # Validate models exist
    if not AUDIO_MODEL_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Audio model not found at {AUDIO_MODEL_PATH}"
        )
    if not VIDEO_MODEL_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Video model not found at {VIDEO_MODEL_PATH}"
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

        # Run inference (lazy import to avoid loading models at startup)
        from app.services.late_fusion import run_inference_cached

        result = run_inference_cached(
            video_file=temp_path,
            audio_pt=AUDIO_MODEL_PATH,
            video_pt=VIDEO_MODEL_PATH,
            wa=audio_weight,
            wv=video_weight,
            num_frames=num_frames,
        )

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

    return {
        "status": "ok" if (audio_ok and video_ok) else "missing_models",
        "audio_model": str(AUDIO_MODEL_PATH),
        "audio_model_exists": audio_ok,
        "video_model": str(VIDEO_MODEL_PATH),
        "video_model_exists": video_ok,
    }
