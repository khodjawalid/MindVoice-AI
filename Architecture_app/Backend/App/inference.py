# inference.py
# Ce fichier contient la classe principale:
# - charge le modèle .pt une seule fois
# - prépare le preprocessing
# - exécute l'inférence vidéo en utilisant video_utils + postprocess
# - renvoie timeline + peaks + segments au format Python (serialisable JSON)

from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
import cv2

from torchvision import transforms
from torchvision.models import resnet18

from .video_utils import open_video, get_fps, make_sampler_step, iter_sampled_frames, FaceCropperHaar
from .postprocess import smooth_probs_buffered, compute_peaks, compute_segments


class EmotionVideoInferer:
    """
    Classe "service" d'inférence.
    Instanciée une fois au démarrage de l'API (modèle chargé en mémoire).
    """
    def __init__(self, model_pt: Path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # ---------- 1) Charger checkpoint .pt ----------
        ckpt = torch.load(model_pt, map_location=self.device)

        # ---------- 2) Récupérer métadonnées (emotions, img_size, norm) ----------
        default_emotions = ["neutral","happy","sad","surprise","fear","anger","disgust","contempt"]

        if isinstance(ckpt, dict) and "emotion_to_idx" in ckpt:
            self.emotion_to_idx = ckpt["emotion_to_idx"]
            self.idx_to_emotion = ckpt.get("idx_to_emotion", {v:k for k,v in self.emotion_to_idx.items()})
            self.emotions = [self.idx_to_emotion[i] for i in range(len(self.idx_to_emotion))]
        else:
            self.emotions = default_emotions
            self.emotion_to_idx = {e:i for i,e in enumerate(self.emotions)}
            self.idx_to_emotion = {i:e for e,i in self.emotion_to_idx.items()}

        self.img_size = ckpt.get("img_size", 224) if isinstance(ckpt, dict) else 224

        norm = ckpt.get("imagenet_norm", {"mean":[0.485,0.456,0.406], "std":[0.229,0.224,0.225]}) if isinstance(ckpt, dict) else {"mean":[0.485,0.456,0.406], "std":[0.229,0.224,0.225]}
        self.mean = norm["mean"]
        self.std = norm["std"]

        # ---------- 3) Construire ResNet-18 avec tête adaptée ----------
        self.model = resnet18(weights=None)
        self.model.fc = nn.Linear(self.model.fc.in_features, len(self.emotions))

        # state_dict: peut être stocké dans ckpt["model_state"] ou directement ckpt
        if isinstance(ckpt, dict) and "model_state" in ckpt:
            state = ckpt["model_state"]
        elif isinstance(ckpt, dict):
            state = ckpt
        else:
            state = ckpt

        self.model.load_state_dict(state, strict=False)
        self.model.to(self.device)
        self.model.eval()

        # ---------- 4) Preprocessing (doit correspondre à l'entraînement) ----------
        self.preprocess = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size)),
            transforms.ToTensor(),
            transforms.Normalize(self.mean, self.std),
        ])

        # ---------- 5) Détecteur visage offline ----------
        self.face_cropper = FaceCropperHaar(margin=0.25)

    @torch.no_grad()
    def _predict_face_bgr(self, face_bgr: np.ndarray) -> np.ndarray:
        """
        Prend un crop visage (BGR), applique preprocessing, renvoie probs [C].
        """
        face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(face_rgb).convert("RGB")
        x = self.preprocess(pil).unsqueeze(0).to(self.device)
        logits = self.model(x)
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        return probs

    def infer_video(
        self,
        video_path: Path,
        sample_fps: int = 8,
        window_sec: float = 1.0,
        conf_thresh: float = 0.35,
    ) -> Dict[str, Any]:
        """
        Inférence complète sur une vidéo, renvoie:
        - timeline (points temps/probs)
        - peaks (moments forts)
        - segments (résumé)
        """
        cap = open_video(video_path)
        video_fps = get_fps(cap)
        step = make_sampler_step(video_fps, sample_fps)

        # nb de frames dans la fenêtre de lissage
        window = max(1, int(round(sample_fps * window_sec)))

        times: List[float] = []
        probs_raw: List[np.ndarray] = []
        valid_mask: List[bool] = []  # True si on a un visage & probs, False sinon

        # ---------- Lecture & prédiction frame par frame ----------
        for frame_idx, t_sec, frame_bgr in iter_sampled_frames(cap, video_fps, step):
            bbox = self.face_cropper.detect_face_bbox(frame_bgr)
            if bbox is None:
                # Pas de visage => on stocke un placeholder
                times.append(float(t_sec))
                probs_raw.append(None)
                valid_mask.append(False)
                continue

            face = self.face_cropper.crop_with_margin(frame_bgr, bbox)
            if face is None or face.size == 0 or min(face.shape[:2]) < 20:
                times.append(float(t_sec))
                probs_raw.append(None)
                valid_mask.append(False)
                continue

            probs = self._predict_face_bgr(face)
            times.append(float(t_sec))
            probs_raw.append(probs)
            valid_mask.append(True)

        cap.release()

        # ---------- Lissage (on ne lisse que sur les frames valides) ----------
        # Pour garder un timeline aligné avec times, on crée une liste smoothed alignée.
        probs_valid = [p for p in probs_raw if p is not None]
        if probs_valid:
            probs_valid_sm = smooth_probs_buffered(probs_valid, window)
        else:
            probs_valid_sm = []

        # Reconstruction alignée
        probs_smoothed_aligned: List[Optional[np.ndarray]] = []
        vi = 0
        for ok in valid_mask:
            if ok:
                probs_smoothed_aligned.append(probs_valid_sm[vi])
                vi += 1
            else:
                probs_smoothed_aligned.append(None)

        # ---------- Construire timeline JSON-ready ----------
        timeline = []
        probs_for_stats = []  # liste smoothed sans None (pour peaks/segments)
        times_for_stats = []

        for t, p in zip(times, probs_smoothed_aligned):
            if p is None:
                timeline.append({
                    "t": t,
                    "pred": "unknown",
                    "conf": 0.0,
                    "probs": None
                })
                continue

            pred_idx = int(np.argmax(p))
            conf = float(np.max(p))
            pred = self.idx_to_emotion[pred_idx]
            if conf < conf_thresh:
                pred_out = "unknown"
            else:
                pred_out = pred

            timeline.append({
                "t": t,
                "pred": pred_out,
                "conf": conf,
                "probs": {self.idx_to_emotion[i]: float(p[i]) for i in range(len(self.emotions))}
            })

            probs_for_stats.append(p)
            times_for_stats.append(t)

        # ---------- Peaks & segments sur les frames valides ----------
        if probs_for_stats:
            peaks = compute_peaks(times_for_stats, probs_for_stats, self.emotions)
            segments = compute_segments(times_for_stats, probs_for_stats, self.emotions, conf_thresh)
        else:
            peaks = []
            segments = []

        return {
            "emotions": self.emotions,
            "fps_used": int(sample_fps),
            "window_sec": float(window_sec),
            "conf_thresh": float(conf_thresh),
            "timeline": timeline,
            "peaks": peaks,
            "segments": segments,
        }
