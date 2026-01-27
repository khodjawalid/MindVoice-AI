"""
Hume AI Expression Measurement Inference Service

This module provides multimodal emotion inference using Hume AI's Expression Measurement API:
- Face: Facial expression analysis (48 emotions)
- Prosody: Speech/voice emotion analysis (48 emotions)

The results are mapped to our 9-emotion format for consistency with the existing app.
"""

import os
import asyncio
import json
import time
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from hume import AsyncHumeClient
from hume.expression_measurement.batch.types import InferenceBaseRequest, Models, Face, Prosody

load_dotenv()

# Target emotions for our app (mapped from Hume's 48 emotions)
TARGET_EMOTIONS = [
    "anger", "calm", "contempt", "disgust", 
    "fear", "happy", "neutral", "sad", "surprise"
]

# Mapping from Hume emotion names to our target emotions
# Hume has 48 emotions, we map the most relevant ones
HUME_TO_TARGET_MAPPING = {
    # Direct mappings
    "Anger": "anger",
    "Calmness": "calm",
    "Contempt": "contempt",
    "Disgust": "disgust",
    "Fear": "fear",
    "Joy": "happy",
    "Sadness": "sad",
    "Surprise (positive)": "surprise",
    "Surprise (negative)": "surprise",
    
    # Secondary mappings (contribute to target emotions)
    "Annoyance": "anger",
    "Contentment": "calm",
    "Satisfaction": "calm",
    "Relief": "calm",
    "Amusement": "happy",
    "Excitement": "happy",
    "Ecstasy": "happy",
    "Triumph": "happy",
    "Pride": "happy",
    "Horror": "fear",
    "Anxiety": "fear",
    "Distress": "sad",
    "Disappointment": "sad",
    "Shame": "sad",
    "Guilt": "sad",
    "Embarrassment": "sad",
}

# Emotions that contribute to "neutral" when all others are low
NEUTRAL_INDICATORS = [
    "Concentration", "Contemplation", "Interest", "Realization"
]


def get_hume_client() -> AsyncHumeClient:
    """Get an async Hume client with API key from environment."""
    api_key = os.getenv("HUME_API_KEY")
    if not api_key:
        raise ValueError(
            "HUME_API_KEY not found in environment variables. "
            "Please add it to your .env file."
        )
    return AsyncHumeClient(api_key=api_key)


def aggregate_hume_emotions(predictions: list[dict], modality: str = "face") -> dict[str, float]:
    """
    Aggregate Hume emotion predictions from multiple frames/segments.
    
    Args:
        predictions: List of prediction objects from Hume API
        modality: "face" or "prosody"
        
    Returns:
        Dictionary of emotion name -> average score
    """
    emotion_scores = {}
    emotion_counts = {}
    
    for pred in predictions:
        if modality == "face" and "face" in pred:
            for face_pred in pred.get("face", {}).get("predictions", []):
                for emotion in face_pred.get("emotions", []):
                    name = emotion.get("name")
                    score = emotion.get("score", 0)
                    if name:
                        emotion_scores[name] = emotion_scores.get(name, 0) + score
                        emotion_counts[name] = emotion_counts.get(name, 0) + 1
                        
        elif modality == "prosody" and "prosody" in pred:
            for prosody_pred in pred.get("prosody", {}).get("predictions", []):
                for emotion in prosody_pred.get("emotions", []):
                    name = emotion.get("name")
                    score = emotion.get("score", 0)
                    if name:
                        emotion_scores[name] = emotion_scores.get(name, 0) + score
                        emotion_counts[name] = emotion_counts.get(name, 0) + 1
    
    # Calculate averages
    averaged = {}
    for name, total_score in emotion_scores.items():
        count = emotion_counts.get(name, 1)
        averaged[name] = total_score / count
        
    return averaged


def map_to_target_emotions(
    face_emotions: dict[str, float],
    prosody_emotions: dict[str, float],
    face_weight: float = 0.5,
    prosody_weight: float = 0.5
) -> dict[str, float]:
    """
    Map Hume's 48 emotions to our 9 target emotions using weighted fusion.
    
    Args:
        face_emotions: Emotion scores from face analysis
        prosody_emotions: Emotion scores from prosody analysis
        face_weight: Weight for face predictions (default 0.5)
        prosody_weight: Weight for prosody predictions (default 0.5)
        
    Returns:
        Dictionary of target emotion -> probability
    """
    # Initialize target emotion scores
    target_scores = {emotion: 0.0 for emotion in TARGET_EMOTIONS}
    target_counts = {emotion: 0 for emotion in TARGET_EMOTIONS}
    
    # Process face emotions
    for hume_emotion, score in face_emotions.items():
        if hume_emotion in HUME_TO_TARGET_MAPPING:
            target = HUME_TO_TARGET_MAPPING[hume_emotion]
            target_scores[target] += score * face_weight
            target_counts[target] += 1
    
    # Process prosody emotions
    for hume_emotion, score in prosody_emotions.items():
        if hume_emotion in HUME_TO_TARGET_MAPPING:
            target = HUME_TO_TARGET_MAPPING[hume_emotion]
            target_scores[target] += score * prosody_weight
            target_counts[target] += 1
    
    # Calculate neutral score based on other scores being low
    non_neutral_sum = sum(
        target_scores[e] for e in TARGET_EMOTIONS if e != "neutral"
    )
    
    # Add neutral indicators from both modalities
    for indicator in NEUTRAL_INDICATORS:
        if indicator in face_emotions:
            target_scores["neutral"] += face_emotions[indicator] * face_weight * 0.3
        if indicator in prosody_emotions:
            target_scores["neutral"] += prosody_emotions[indicator] * prosody_weight * 0.3
    
    # If other emotions are very low, boost neutral
    if non_neutral_sum < 0.3:
        target_scores["neutral"] = max(target_scores["neutral"], 0.5)
    
    # Normalize to probabilities (sum to 1)
    total = sum(target_scores.values())
    if total > 0:
        probabilities = {k: v / total for k, v in target_scores.items()}
    else:
        # Default to neutral if no emotions detected
        probabilities = {e: 0.0 for e in TARGET_EMOTIONS}
        probabilities["neutral"] = 1.0
    
    return probabilities


async def run_hume_inference(
    video_path: Path,
    face_weight: float = 0.5,
    prosody_weight: float = 0.5,
    timeout: int = 120
) -> dict:
    """
    Run Hume Expression Measurement inference on a video file.
    
    Args:
        video_path: Path to the video file
        face_weight: Weight for face predictions (0-1)
        prosody_weight: Weight for prosody predictions (0-1)
        timeout: Maximum time to wait for job completion (seconds)
        
    Returns:
        Dictionary with inference results in the same format as late_fusion
    """
    client = get_hume_client()
    
    # Configure models for face and prosody analysis
    config = InferenceBaseRequest(
        models=Models(
            face=Face(),
            prosody=Prosody()
        )
    )
    
    # Start the batch job with the local file
    with open(video_path, "rb") as f:
        job_id = await client.expression_measurement.batch.start_inference_job_from_local_file(
            file=[f],
            json=config
        )
    
    # Poll for job completion
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Hume job {job_id} timed out after {timeout} seconds")
        
        job_details = await client.expression_measurement.batch.get_job_details(id=job_id)
        status = job_details.state.status
        
        if status == "COMPLETED":
            break
        elif status == "FAILED":
            raise RuntimeError(f"Hume job {job_id} failed: {job_details.state}")
        
        # Wait before polling again
        await asyncio.sleep(2)
    
    # Get predictions
    predictions = await client.expression_measurement.batch.get_job_predictions(id=job_id)
    
    # Parse predictions - extract face and prosody emotions
    face_emotions_raw = {}
    prosody_emotions_raw = {}
    face_count = 0
    prosody_count = 0
    
    for source_result in predictions:
        if not hasattr(source_result, 'results'):
            continue
            
        results = source_result.results
        if not results or not hasattr(results, 'predictions'):
            continue
        
        for pred in results.predictions:
            if not hasattr(pred, 'models'):
                continue
            
            models = pred.models
            
            # Extract face emotions
            if hasattr(models, 'face') and models.face:
                face_data = models.face
                if hasattr(face_data, 'grouped_predictions') and face_data.grouped_predictions:
                    for group in face_data.grouped_predictions:
                        if hasattr(group, 'predictions'):
                            for face_pred in group.predictions:
                                if hasattr(face_pred, 'emotions'):
                                    for emotion in face_pred.emotions:
                                        name = emotion.name
                                        score = emotion.score
                                        face_emotions_raw[name] = face_emotions_raw.get(name, 0) + score
                                    face_count += 1
            
            # Extract prosody emotions
            if hasattr(models, 'prosody') and models.prosody:
                prosody_data = models.prosody
                if hasattr(prosody_data, 'grouped_predictions') and prosody_data.grouped_predictions:
                    for group in prosody_data.grouped_predictions:
                        if hasattr(group, 'predictions'):
                            for prosody_pred in group.predictions:
                                if hasattr(prosody_pred, 'emotions'):
                                    for emotion in prosody_pred.emotions:
                                        name = emotion.name
                                        score = emotion.score
                                        prosody_emotions_raw[name] = prosody_emotions_raw.get(name, 0) + score
                                    prosody_count += 1
    
    # Average the emotions
    face_emotions = {k: v / face_count for k, v in face_emotions_raw.items()} if face_count > 0 else {}
    prosody_emotions = {k: v / prosody_count for k, v in prosody_emotions_raw.items()} if prosody_count > 0 else {}
    
    # Map to target emotions with weighted fusion
    emotion_probabilities = map_to_target_emotions(
        face_emotions, prosody_emotions,
        face_weight, prosody_weight
    )
    
    # Find predicted label
    pred_label = max(emotion_probabilities, key=emotion_probabilities.get)
    pred_confidence = emotion_probabilities[pred_label]
    
    # Build result in same format as late_fusion
    labels_9 = TARGET_EMOTIONS
    probs_9 = [emotion_probabilities[label] for label in labels_9]
    
    return {
        "labels_9": labels_9,
        "probs_9": probs_9,
        "pred_label": pred_label,
        "pred_confidence": pred_confidence,
        "emotion_probabilities": emotion_probabilities,
        "raw_face_emotions": face_emotions,
        "raw_prosody_emotions": prosody_emotions,
        "job_id": job_id
    }


# Synchronous wrapper for FastAPI compatibility
def run_hume_inference_sync(
    video_path: Path,
    face_weight: float = 0.5,
    prosody_weight: float = 0.5,
    timeout: int = 120
) -> dict:
    """Synchronous wrapper for run_hume_inference."""
    return asyncio.run(run_hume_inference(
        video_path, face_weight, prosody_weight, timeout
    ))
