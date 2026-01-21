# video_utils.py
# Ce fichier contient uniquement des utilitaires "vidéo" :
# - ouvrir une vidéo
# - échantillonner des frames (ex: 8 fps)
# - détecter/cropper le visage (Haar cascade offline)
#
# Important : on garde la partie visage simple (Haar) pour fonctionner offline.
# Si plus tard tu veux MediaPipe/RetinaFace, tu remplaceras seulement ici.

from pathlib import Path
from typing import Iterator, Tuple, Optional

import numpy as np
import cv2


def open_video(path: Path) -> cv2.VideoCapture:
    """Ouvre la vidéo et vérifie qu'elle est lisible."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la vidéo: {path}")
    return cap


def get_fps(cap: cv2.VideoCapture) -> float:
    """Récupère le fps de la vidéo. Fallback à 25 si inconnu."""
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        fps = 25.0
    return float(fps)


def make_sampler_step(video_fps: float, sample_fps: int) -> int:
    """Calcule 1 frame sur N pour approximer sample_fps."""
    return max(1, int(round(video_fps / sample_fps)))


def iter_sampled_frames(
    cap: cv2.VideoCapture,
    video_fps: float,
    step: int
) -> Iterator[Tuple[int, float, np.ndarray]]:
    """
    Itère sur les frames échantillonnées.
    Rend: (frame_idx, t_sec, frame_bgr)
    """
    frame_idx = 0
    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            break

        # On ne traite qu'une frame toutes les 'step' frames
        if frame_idx % step == 0:
            t_sec = frame_idx / video_fps
            yield frame_idx, t_sec, frame_bgr

        frame_idx += 1


class FaceCropperHaar:
    """
    Détecteur visage simple offline (Haar).
    - Avantage: pas besoin d'internet / pas de modèles externes.
    - Limite: moins robuste qu'un détecteur moderne, mais suffisant pour POC.
    """
    def __init__(self, margin: float = 0.25):
        self.margin = margin
        haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(haar_path)
        if self.face_cascade.empty():
            raise RuntimeError("Haar cascade introuvable: opencv data manquante ?")

    def detect_face_bbox(self, frame_bgr: np.ndarray) -> Optional[Tuple[int,int,int,int]]:
        """Retourne bbox (x,y,w,h) du plus grand visage, ou None."""
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
        )
        if len(faces) == 0:
            return None
        faces = sorted(faces, key=lambda b: b[2]*b[3], reverse=True)
        return tuple(int(v) for v in faces[0])

    def crop_with_margin(self, frame_bgr: np.ndarray, bbox: Tuple[int,int,int,int]) -> np.ndarray:
        """Crop le visage avec une marge."""
        x, y, bw, bh = bbox
        h, w = frame_bgr.shape[:2]
        mx = int(bw * self.margin)
        my = int(bh * self.margin)

        x1 = max(0, x - mx)
        y1 = max(0, y - my)
        x2 = min(w, x + bw + mx)
        y2 = min(h, y + bh + my)

        return frame_bgr[y1:y2, x1:x2]
