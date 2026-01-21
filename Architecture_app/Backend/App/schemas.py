# schemas.py
# Ici on définit les structures JSON que l'API va renvoyer au front.
# Ça rend la réponse stable (contrat clair) et facile à consommer côté Next.js.

from pydantic import BaseModel
from typing import Dict, List, Optional


class TimelinePoint(BaseModel):
    # Timestamp en secondes depuis le début de la vidéo
    t: float
    # Émotion prédite (ou "unknown" si pas de visage / confiance faible)
    pred: str
    # Confiance = max(probs)
    conf: float
    # Probabilités par émotion (None si unknown)
    probs: Optional[Dict[str, float]] = None


class Peak(BaseModel):
    # L'émotion concernée
    emotion: str
    # Moment du pic (sec)
    t_peak: float
    # Valeur du pic
    p_peak: float


class Segment(BaseModel):
    # Segment temporel où une émotion domine (résumé)
    emotion: str
    t_start: float
    t_end: float
    mean_conf: float


class InferenceResponse(BaseModel):
    emotions: List[str]
    fps_used: int
    window_sec: float
    conf_thresh: float

    timeline: List[TimelinePoint]
    peaks: List[Peak]
    segments: List[Segment]
