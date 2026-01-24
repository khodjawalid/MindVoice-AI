"""
Stress Inference Engine for EDA and HR signals.
Adapted from Eda_hr_inference.py for backend usage.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

import joblib
import numpy as np
import pandas as pd


# ----------------------------
# Feature extraction (identical to training)
# ----------------------------
def extract_features_1d(x: np.ndarray) -> np.ndarray:
    """Extract 7 statistical features from a 1D signal."""
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
    Convert a timestamped stream to uniform series at fs_target on [start, end).
    - Bin in steps of 1/fs_target seconds (e.g., 250ms)
    - Aggregation: mean
    - Fill: "edge" (pad before/after with edge), or "nan"
    """
    if df.empty:
        n = int(round((end_micros - start_micros) / 1_000_000 * fs_target))
        return np.full((n,), np.nan, dtype=np.float32)

    step_sec = 1.0 / fs_target
    step_micros = int(round(step_sec * 1_000_000))

    # Filter interval
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

    # mean per bin
    out = np.full((n,), np.nan, dtype=np.float32)
    if bin_idx.size == 0:
        return out

    sums = np.bincount(bin_idx, weights=vals, minlength=n).astype(np.float32)
    cnts = np.bincount(bin_idx, minlength=n).astype(np.float32)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = sums / np.where(cnts == 0, np.nan, cnts)

    if fill == "edge":
        # backward fill (start)
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
    """Calculate the ratio of finite (non-NaN) values."""
    if x.size == 0:
        return 0.0
    return float(np.isfinite(x).sum() / x.size)


# ----------------------------
# Inference Configuration
# ----------------------------
@dataclass
class StressInferConfig:
    fs_target: float = 4.0           # 4Hz as in training
    window_sec: int = 60             # window = 60s (training)
    step_sec: int = 60               # output every 60s
    threshold: float = 0.5           # binary decision threshold
    min_coverage: float = 0.7        # minimum % of non-NaN points per window
    fill_mode: str = "edge"          # "edge" or "nan"


# ----------------------------
# Inference Engine
# ----------------------------
class StressInferenceEngine:
    """Engine for stress inference from EDA and HR raw signals."""
    
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
        """Extract features from a window of EDA and HR data."""
        # Coverage check
        if coverage_ratio(eda_4hz) < self.cfg.min_coverage:
            return None
        if coverage_ratio(hr_4hz) < self.cfg.min_coverage:
            return None

        # Fill remaining NaN values
        if np.isnan(eda_4hz).any():
            eda_4hz = pd.Series(eda_4hz).ffill().bfill().to_numpy(dtype=np.float32)
        if np.isnan(hr_4hz).any():
            hr_4hz = pd.Series(hr_4hz).ffill().bfill().to_numpy(dtype=np.float32)

        f_eda = extract_features_1d(eda_4hz)
        f_hr = extract_features_1d(hr_4hz)
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
        Run inference on raw EDA and HR dataframes.
        
        Args:
            eda_raw_df: DataFrame with columns [timestamp_unix_micros, eda_raw]
            hr_raw_df: DataFrame with columns [timestamp_unix_micros, hr_bpm]
            
        Returns:
            DataFrame with minute-by-minute stress predictions.
        """
        # Sort and convert types
        eda = eda_raw_df[[ts_col, eda_col]].dropna().sort_values(ts_col).copy()
        hr = hr_raw_df[[ts_col, hr_col]].dropna().sort_values(ts_col).copy()

        eda[ts_col] = eda[ts_col].astype(np.int64)
        hr[ts_col] = hr[ts_col].astype(np.int64)
        eda[eda_col] = eda[eda_col].astype(np.float32)
        hr[hr_col] = hr[hr_col].astype(np.float32)

        if eda.empty or hr.empty:
            return pd.DataFrame(columns=[
                "window_start_micros", "window_start_iso_utc",
                "stress_proba", "stress_pred",
                "eda_coverage", "hr_coverage"
            ])

        # Define common range
        start = max(int(eda[ts_col].min()), int(hr[ts_col].min()))
        end = min(int(eda[ts_col].max()), int(hr[ts_col].max()))

        # Align start to step
        step_micros = int(round(self.cfg.step_sec * 1_000_000))
        win_micros = int(round(self.cfg.window_sec * 1_000_000))
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
            hr_cov = coverage_ratio(hr_4hz)

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

    def infer_from_csv_files(
        self,
        eda_csv_path: Path,
        hr_csv_path: Path,
    ) -> pd.DataFrame:
        """
        Run inference from CSV files.
        
        Args:
            eda_csv_path: Path to EDA raw CSV (columns: timestamp, datetime_utc, eda_us)
            hr_csv_path: Path to HR raw CSV (columns: timestamp, datetime_utc, hr_bpm)
            
        Returns:
            DataFrame with minute-by-minute stress predictions.
        """
        eda_df = pd.read_csv(eda_csv_path)
        hr_df = pd.read_csv(hr_csv_path)
        
        # Convert timestamp (seconds) to microseconds
        eda_df["timestamp_unix_micros"] = (eda_df["timestamp"] * 1_000_000).astype(np.int64)
        hr_df["timestamp_unix_micros"] = (hr_df["timestamp"] * 1_000_000).astype(np.int64)
        
        # Rename columns to match expected format
        eda_df = eda_df.rename(columns={"eda_us": "eda_raw"})
        
        return self.infer_from_raw_frames(
            eda_df, hr_df,
            ts_col="timestamp_unix_micros",
            eda_col="eda_raw",
            hr_col="hr_bpm"
        )

    def get_summary_stats(self, results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate summary statistics from inference results.
        
        Returns:
            Dictionary with avg_stress_proba, stress_ratio, total_windows, valid_windows
        """
        valid = results_df.dropna(subset=["stress_proba"])
        
        if valid.empty:
            return {
                "avg_stress_proba": None,
                "stress_ratio": None,
                "total_windows": len(results_df),
                "valid_windows": 0,
            }
        
        return {
            "avg_stress_proba": float(valid["stress_proba"].mean()),
            "stress_ratio": float(valid["stress_pred"].mean()),
            "total_windows": len(results_df),
            "valid_windows": len(valid),
        }
