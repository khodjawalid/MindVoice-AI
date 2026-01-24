from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import joblib
import numpy as np
import pandas as pd


# ----------------------------
# Feature extraction (identique à l'entraînement)
# ----------------------------
def extract_features_1d(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return np.full((7,), np.nan, dtype=np.float32)

    mean = x.mean()
    std = x.std()
    mn = x.min()
    mx = x.max()
    rng = mx - mn
    t = np.arange(len(x), dtype=np.float64)
    slope = np.polyfit(t, x, 1)[0] if len(x) > 1 else 0.0
    mad = np.mean(np.abs(np.diff(x))) if len(x) > 1 else 0.0
    return np.array([mean, std, mn, mx, rng, slope, mad], dtype=np.float32)


DEFAULT_FEATURE_NAMES = [
    "eda_mean", "eda_std", "eda_min", "eda_max", "eda_range", "eda_slope", "eda_mean_abs_diff",
    "pr_mean",  "pr_std",  "pr_min",  "pr_max",  "pr_range",  "pr_slope",  "pr_mean_abs_diff",
]


# ----------------------------
# Resampling utilities
# ----------------------------
def floor_to_step_micros(ts_micros: np.ndarray, step_sec: float) -> np.ndarray:
    step = int(round(step_sec * 1_000_000))
    return (ts_micros // step) * step


def to_uniform_series_4hz(
    df: pd.DataFrame,
    ts_col: str,
    val_col: str,
    start_micros: int,
    end_micros: int,
    fs_target: float = 4.0,
    fill: str = "edge",
) -> np.ndarray:
    """
    Convertit un stream timestampé en série uniforme à fs_target sur [start, end).
    - Bin en pas de 1/fs_target seconde (ex: 250ms)
    - Aggregation: mean
    - Fill: "edge" (pad avant/après avec bord), ou "nan"
    """
    if df.empty:
        n = int(round((end_micros - start_micros) / 1_000_000 * fs_target))
        return np.full((n,), np.nan, dtype=np.float32)

    step_sec = 1.0 / fs_target
    step_micros = int(round(step_sec * 1_000_000))

    # Filtre intervalle
    seg = df[(df[ts_col] >= start_micros) & (df[ts_col] < end_micros)]
    n = int(round((end_micros - start_micros) / 1_000_000 * fs_target))
    if n <= 0:
        return np.array([], dtype=np.float32)

    if seg.empty:
        return np.full((n,), np.nan, dtype=np.float32)

    ts = seg[ts_col].to_numpy(dtype=np.int64)
    vals = seg[val_col].to_numpy(dtype=np.float32)

    # Bin index 0..n-1
    bin_idx = (ts - start_micros) // step_micros
    bin_idx = bin_idx.astype(np.int64)
    mask = (bin_idx >= 0) & (bin_idx < n)
    bin_idx = bin_idx[mask]
    vals = vals[mask]

    # mean par bin (rapide, sans groupby lourd)
    out = np.full((n,), np.nan, dtype=np.float32)
    if bin_idx.size == 0:
        return out

    # Somme + compte par bin
    sums = np.bincount(bin_idx, weights=vals, minlength=n).astype(np.float32)
    cnts = np.bincount(bin_idx, minlength=n).astype(np.float32)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = sums / np.where(cnts == 0, np.nan, cnts)

    if fill == "edge":
        # fill forward/backward simple
        # backward fill (début)
        if np.isnan(out[0]):
            first = np.where(~np.isnan(out))[0]
            if first.size > 0:
                out[:first[0]] = out[first[0]]
        # forward fill
        for i in range(1, n):
            if np.isnan(out[i]):
                out[i] = out[i - 1]
    return out.astype(np.float32)


def coverage_ratio(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.isfinite(x).sum() / x.size)


# ----------------------------
# Inference Engine
# ----------------------------
@dataclass
class StressInferConfig:
    fs_target: float = 4.0           # 4Hz comme training
    window_sec: int = 60             # fenêtre = 60s (training)
    step_sec: int = 60               # sortie toutes les 60s (modifiable: 30s etc.)
    threshold: float = 0.5           # seuil décision binaire
    min_coverage: float = 0.7        # % minimum de points non-NaN par fenêtre
    fill_mode: str = "edge"          # "edge" ou "nan"


class StressInferenceEngine:
    def __init__(self, model_joblib_path: Path, config: Optional[StressInferConfig] = None):
        obj = joblib.load(model_joblib_path)
        self.model = obj["model"] if isinstance(obj, dict) and "model" in obj else obj
        self.feature_names = obj.get("feature_names") if isinstance(obj, dict) else None
        self.threshold = obj.get("threshold") if isinstance(obj, dict) else None
        self.cfg = config or StressInferConfig()

        if self.threshold is not None:
            self.cfg.threshold = float(self.threshold)

        if self.feature_names is None:
            self.feature_names = DEFAULT_FEATURE_NAMES

    def _features_from_window(self, eda_4hz: np.ndarray, hr_4hz: np.ndarray) -> Optional[np.ndarray]:
        # Coverage check
        if coverage_ratio(eda_4hz) < self.cfg.min_coverage:
            return None
        if coverage_ratio(hr_4hz) < self.cfg.min_coverage:
            return None

        # Si fill_mode="nan", on remplace les NaN restants (sécurité)
        if np.isnan(eda_4hz).any():
            eda_4hz = pd.Series(eda_4hz).fillna(method="ffill").fillna(method="bfill").to_numpy(dtype=np.float32)
        if np.isnan(hr_4hz).any():
            hr_4hz = pd.Series(hr_4hz).fillna(method="ffill").fillna(method="bfill").to_numpy(dtype=np.float32)

        f_eda = extract_features_1d(eda_4hz)
        f_hr  = extract_features_1d(hr_4hz)
        return np.concatenate([f_eda, f_hr], axis=0).astype(np.float32)

    def infer_from_raw_frames(
        self,
        eda_raw_df: pd.DataFrame,
        hr_raw_df: pd.DataFrame,
        ts_col: str = "timestamp_unix_micros",
        eda_col: str = "eda_raw",
        hr_col: str = "hr_bpm",
    ) -> pd.DataFrame:
        """
        Entrées:
          - eda_raw_df: colonnes [timestamp_unix_micros, eda_raw]
          - hr_raw_df : colonnes [timestamp_unix_micros, hr_bpm]
        Sortie:
          - DataFrame minute par minute (ou step_sec), avec proba/pred + coverage.
        """
        # Tri + types
        eda = eda_raw_df[[ts_col, eda_col]].dropna().sort_values(ts_col).copy()
        hr  = hr_raw_df[[ts_col, hr_col]].dropna().sort_values(ts_col).copy()

        eda[ts_col] = eda[ts_col].astype(np.int64)
        hr[ts_col]  = hr[ts_col].astype(np.int64)
        eda[eda_col] = eda[eda_col].astype(np.float32)
        hr[hr_col]   = hr[hr_col].astype(np.float32)

        if eda.empty or hr.empty:
            return pd.DataFrame(columns=[
                "window_start_micros", "window_start_iso_utc",
                "stress_proba", "stress_pred",
                "eda_coverage", "hr_coverage"
            ])

        # Définir la plage commune
        start = max(int(eda[ts_col].min()), int(hr[ts_col].min()))
        end   = min(int(eda[ts_col].max()), int(hr[ts_col].max()))

        # Aligner start sur step
        step_micros = int(round(self.cfg.step_sec * 1_000_000))
        win_micros  = int(round(self.cfg.window_sec * 1_000_000))
        start = (start // step_micros) * step_micros

        rows = []
        t0 = start
        while t0 + win_micros <= end:
            t1 = t0 + win_micros

            eda_4hz = to_uniform_series_4hz(
                eda, ts_col, eda_col, t0, t1,
                fs_target=self.cfg.fs_target, fill=self.cfg.fill_mode
            )
            hr_4hz = to_uniform_series_4hz(
                hr, ts_col, hr_col, t0, t1,
                fs_target=self.cfg.fs_target, fill=self.cfg.fill_mode
            )

            eda_cov = coverage_ratio(eda_4hz)
            hr_cov  = coverage_ratio(hr_4hz)

            feats = self._features_from_window(eda_4hz, hr_4hz)

            if feats is None:
                rows.append({
                    "window_start_micros": t0,
                    "window_start_iso_utc": pd.to_datetime(t0, unit="us", utc=True).isoformat(),
                    "stress_proba": np.nan,
                    "stress_pred": np.nan,
                    "eda_coverage": eda_cov,
                    "hr_coverage": hr_cov,
                })
            else:
                proba = float(self.model.predict_proba(feats.reshape(1, -1))[0, 1])
                pred = int(proba >= self.cfg.threshold)
                rows.append({
                    "window_start_micros": t0,
                    "window_start_iso_utc": pd.to_datetime(t0, unit="us", utc=True).isoformat(),
                    "stress_proba": proba,
                    "stress_pred": pred,
                    "eda_coverage": eda_cov,
                    "hr_coverage": hr_cov,
                })

            t0 += step_micros

        return pd.DataFrame(rows)


# ----------------------------
# CLI (optionnel) - pour test local
# ----------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Stress inference from EDA raw + HR raw using trained XGB model.")
    parser.add_argument("--model", type=str, required=True, help="Path to joblib model (new model)")
    parser.add_argument("--eda_csv", type=str, required=True, help="eda_raw_*.csv")
    parser.add_argument("--hr_csv", type=str, required=True, help="hr_raw_*.csv")
    parser.add_argument("--out_csv", type=str, default="", help="Optional output CSV path")
    parser.add_argument("--window_sec", type=int, default=60)
    parser.add_argument("--step_sec", type=int, default=60)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--min_coverage", type=float, default=0.7)
    args = parser.parse_args()

    cfg = StressInferConfig(
        window_sec=args.window_sec,
        step_sec=args.step_sec,
        threshold=args.threshold,
        min_coverage=args.min_coverage,
    )

    engine = StressInferenceEngine(Path(args.model), config=cfg)
    eda_df = pd.read_csv(args.eda_csv)
    hr_df  = pd.read_csv(args.hr_csv)

    out = engine.infer_from_raw_frames(eda_df, hr_df)

    print(out.head(10))
    print("\nRows:", len(out), "valid:", int(out["stress_proba"].notna().sum()))

    if args.out_csv:
        Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(args.out_csv, index=False)
        print("Saved ->", args.out_csv)


if __name__ == "__main__":
    main()



"""
engine = StressInferenceEngine(Path("models/wrist_eda_pr_global_xgb.joblib"))

out_df = engine.infer_from_raw_frames(eda_raw_df, hr_raw_df)
# out_df -> minute par minute : stress_proba + stress_pred
"""