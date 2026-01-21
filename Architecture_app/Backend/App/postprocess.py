# postprocess.py
# Ici on regroupe les étapes "après" le modèle:
# - lissage temporel (moving average)
# - extraction de peaks (moments forts)
# - segmentation (résumé lisible: émotion dominante par intervalle)

from typing import List, Dict, Any
import numpy as np


def smooth_probs_buffered(probs_list: List[np.ndarray], window: int) -> List[np.ndarray]:
    """
    Lisse les probabilités via moyenne glissante.
    window = nombre d'frames dans la fenêtre.
    """
    if window <= 1:
        return probs_list

    out = []
    buf = []
    for p in probs_list:
        buf.append(p)
        if len(buf) > window:
            buf.pop(0)
        out.append(np.mean(np.stack(buf), axis=0))
    return out


def compute_peaks(times: List[float], probs_smoothed: List[np.ndarray], emotions: List[str]) -> List[Dict[str, Any]]:
    """
    Pic = maximum global de chaque émotion (temps + valeur).
    """
    peaks = []
    P = np.stack(probs_smoothed)  # shape [T, C]
    for i, emo in enumerate(emotions):
        idx = int(np.argmax(P[:, i]))
        peaks.append({
            "emotion": emo,
            "t_peak": float(times[idx]),
            "p_peak": float(P[idx, i]),
        })
    # Tri décroissant par valeur du pic
    peaks.sort(key=lambda d: d["p_peak"], reverse=True)
    return peaks


def compute_segments(times: List[float], probs_smoothed: List[np.ndarray], emotions: List[str], conf_thresh: float) -> List[Dict[str, Any]]:
    """
    Segments = intervalles où l'émotion dominante reste la même.
    On ignore les frames trop incertaines (conf < conf_thresh) => 'unknown'.
    """
    segments = []
    if not probs_smoothed:
        return segments

    P = np.stack(probs_smoothed)  # [T, C]
    pred_idx = np.argmax(P, axis=1)
    conf = np.max(P, axis=1)

    # convertit en labels
    labels = []
    for i in range(len(times)):
        if conf[i] < conf_thresh:
            labels.append("unknown")
        else:
            labels.append(emotions[int(pred_idx[i])])

    # regroupe en segments
    start = 0
    while start < len(times):
        cur = labels[start]
        end = start
        while end + 1 < len(times) and labels[end + 1] == cur:
            end += 1

        t_start = times[start]
        t_end = times[end]
        mean_conf = float(np.mean(conf[start:end+1]))

        segments.append({
            "emotion": cur,
            "t_start": float(t_start),
            "t_end": float(t_end),
            "mean_conf": mean_conf,
        })
        start = end + 1

    return segments
