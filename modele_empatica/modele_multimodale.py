from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import numpy as np
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


# ============================================================
# 1) Models wrappers (vos modèles existants / collègues)
# ============================================================

class PhysioModel:
    """
    Wrapper du modèle global WESAD (EDA+PR) -> p_stress(t)
    En pratique : tu appelles ton inference EDA/PR ici.
    """
    def __init__(self, model_path: str):
        obj = joblib.load(model_path)
        self.model = obj["model"]
        self.feature_names = obj.get("feature_names", None)

    def predict_proba_from_features(self, X_feat: np.ndarray) -> np.ndarray:
        # X_feat shape (N, D)
        return self.model.predict_proba(X_feat)[:, 1]  # p(stress)


class AudioModel:
    """
    Placeholder: votre collègue mettra son vrai modèle.
    """
    def predict_proba(self, audio_feat: np.ndarray) -> float:
        # retourne p(stress) pour un chunk audio
        return float(np.clip(np.mean(audio_feat), 0, 1))


class FaceModel:
    """
    Placeholder: votre collègue mettra son vrai modèle.
    """
    def predict_proba(self, face_feat: np.ndarray) -> float:
        return float(np.clip(np.mean(face_feat), 0, 1))


# ============================================================
# 2) Fusion layer (late fusion) + calibrator perso
# ============================================================

@dataclass
class FusionWeights:
    w_physio: float = 0.6
    w_audio: float = 0.2
    w_face: float = 0.2

    def normalize(self):
        s = self.w_physio + self.w_audio + self.w_face
        if s <= 0:
            self.w_physio, self.w_audio, self.w_face = 1.0, 0.0, 0.0
            return
        self.w_physio /= s
        self.w_audio /= s
        self.w_face /= s


class MultimodalFusion:
    """
    p_final = somme pondérée des probabilités par modalité.
    """
    def __init__(self, weights: FusionWeights):
        self.weights = weights
        self.weights.normalize()

    def fuse(self, p_physio: float, p_audio: Optional[float], p_face: Optional[float]) -> float:
        w = self.weights
        # si audio/face manquants -> on renormalise à la volée
        wp, wa, wf = w.w_physio, w.w_audio, w.w_face
        if p_audio is None:
            wa = 0.0
        if p_face is None:
            wf = 0.0
        s = wp + wa + wf
        if s <= 0:
            return float(p_physio)
        wp, wa, wf = wp/s, wa/s, wf/s
        p = wp*p_physio + (wa*(p_audio if p_audio is not None else 0.0)) + (wf*(p_face if p_face is not None else 0.0))
        return float(np.clip(p, 0.0, 1.0))


class DailyCalibrator:
    """
    Calibrateur perso appris SUR LES TAGS.
    Il prend en entrée les scores des modules (p_physio, p_audio, p_face, p_fused)
    et apprend à mieux coller aux labels utilisateur.
    => léger, rapide, réaliste avec peu de data.
    """
    def __init__(self):
        self.pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=2000))
        ])
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray):
        # X: (N, 4) = [p_physio, p_audio, p_face, p_fused] (audio/face peuvent être -1 si missing)
        self.pipe.fit(X, y)
        self.is_fitted = True

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            # pas de calibration => renvoie juste p_fused
            return X[:, 3]
        return self.pipe.predict_proba(X)[:, 1]


# ============================================================
# 3) Tags: stockage + affichage + création dataset daily update
# ============================================================

@dataclass
class UserTag:
    ts_utc: str          # ex "2026-01-16T14:37:00Z"
    label: str           # "stress" / "neutral" / "amusement" / ...
    note: str = ""       # descriptif utilisateur


def load_tags_from_json(path: str) -> List[UserTag]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tags = []
    for item in data:
        tags.append(UserTag(ts_utc=item["ts_utc"], label=item["label"], note=item.get("note", "")))
    return tags


# ============================================================
# 4) Main system (inference timeline + daily update)
# ============================================================

class MindVoiceSystem:
    def __init__(
        self,
        physio_model_path: str,
        weights: FusionWeights = FusionWeights(),
        calibrator_path: str = "models/daily_calibrator.joblib",
        weights_path: str = "models/fusion_weights.json",
    ):
        self.physio = PhysioModel(physio_model_path)
        self.audio = AudioModel()
        self.face = FaceModel()
        self.fusion = MultimodalFusion(weights)

        self.calibrator_path = Path(calibrator_path)
        self.weights_path = Path(weights_path)

        self.calibrator = DailyCalibrator()
        self._load_personalization_if_exists()

    def _load_personalization_if_exists(self):
        if self.calibrator_path.exists():
            self.calibrator = joblib.load(self.calibrator_path)
        if self.weights_path.exists():
            w = json.loads(self.weights_path.read_text(encoding="utf-8"))
            self.fusion = MultimodalFusion(FusionWeights(**w))

    def save_personalization(self):
        self.calibrator_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.calibrator, self.calibrator_path)
        self.weights_path.parent.mkdir(parents=True, exist_ok=True)
        self.weights_path.write_text(
            json.dumps(self.fusion.weights.__dict__, indent=2),
            encoding="utf-8"
        )

    # ---------- INFERENCE CONTINUE ----------
    def infer_timeline(
        self,
        X_physio_feat: np.ndarray,
        audio_feat_t: Optional[np.ndarray] = None,
        face_feat_t: Optional[np.ndarray] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Entrées :
          - X_physio_feat : features par fenêtre temporelle (N, D) pour EDA/PR (comme ton pipeline)
          - audio_feat_t : (N, da) ou None (si pas dispo en continu)
          - face_feat_t  : (N, df) ou None

        Sortie :
          - p_physio(t), p_audio(t), p_face(t), p_fused(t), p_final_calibrated(t)
        """
        N = X_physio_feat.shape[0]

        p_physio = self.physio.predict_proba_from_features(X_physio_feat)  # (N,)

        p_audio = None
        if audio_feat_t is not None:
            p_audio = np.array([self.audio.predict_proba(audio_feat_t[i]) for i in range(N)], dtype=np.float32)

        p_face = None
        if face_feat_t is not None:
            p_face = np.array([self.face.predict_proba(face_feat_t[i]) for i in range(N)], dtype=np.float32)

        p_fused = np.zeros(N, dtype=np.float32)
        for i in range(N):
            pa = None if p_audio is None else float(p_audio[i])
            pf = None if p_face is None else float(p_face[i])
            p_fused[i] = self.fusion.fuse(float(p_physio[i]), pa, pf)

        # Calibrator: entrée = [p_physio, p_audio, p_face, p_fused]
        X_cal = np.zeros((N, 4), dtype=np.float32)
        X_cal[:, 0] = p_physio
        X_cal[:, 1] = (-1.0 if p_audio is None else p_audio)  # -1 = missing
        X_cal[:, 2] = (-1.0 if p_face is None else p_face)
        X_cal[:, 3] = p_fused

        p_final = self.calibrator.predict_proba(X_cal)  # (N,)
        p_final = np.clip(p_final, 0.0, 1.0).astype(np.float32)

        return {
            "p_physio": p_physio.astype(np.float32),
            "p_audio": (np.full(N, np.nan, dtype=np.float32) if p_audio is None else p_audio),
            "p_face":  (np.full(N, np.nan, dtype=np.float32) if p_face is None else p_face),
            "p_fused": p_fused,
            "p_final": p_final,
        }

    # ---------- DAILY UPDATE via TAGS ----------
    def daily_update_from_tags(
        self,
        timeline_scores: Dict[str, np.ndarray],
        timeline_time_utc: List[str],
        tags: List[UserTag],
        window_minutes: int = 10,
    ):
        """
        On construit un dataset à partir des tags:
        - On prend les points proches du tag (±window_minutes) comme exemples
        - y = 1 si label == stress (pour demo), sinon 0
        - X = [p_physio, p_audio, p_face, p_fused]
        Puis on fit le calibrator (petit modèle léger).
        """
        # mapping index par timestamp (simple: exact match)
        idx_by_time = {t: i for i, t in enumerate(timeline_time_utc)}

        X_list, y_list = [], []
        for tg in tags:
            if tg.ts_utc not in idx_by_time:
                continue
            center = idx_by_time[tg.ts_utc]

            # convertit window_minutes -> nb points (si 1 point = 1 minute)
            # si votre timeline est 1 point/minute, c'est parfait.
            K = window_minutes
            lo = max(0, center - K)
            hi = min(len(timeline_time_utc), center + K + 1)

            # label binaire demo
            y_val = 1 if tg.label.strip().lower() in ["stress", "stressed"] else 0

            for i in range(lo, hi):
                X_list.append([
                    float(timeline_scores["p_physio"][i]),
                    float(timeline_scores["p_audio"][i]) if not np.isnan(timeline_scores["p_audio"][i]) else -1.0,
                    float(timeline_scores["p_face"][i])  if not np.isnan(timeline_scores["p_face"][i])  else -1.0,
                    float(timeline_scores["p_fused"][i]),
                ])
                y_list.append(y_val)

        if len(X_list) < 10:
            print("Pas assez d'exemples issus des tags pour faire un update (normal au début).")
            return

        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.int64)

        print("Daily update dataset:", X.shape, "pos=", int(y.sum()), "neg=", int((y == 0).sum()))

        self.calibrator.fit(X, y)
        self.save_personalization()
        print("Daily calibrator updated + saved.")
