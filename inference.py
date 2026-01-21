from pathlib import Path
import joblib
import numpy as np
import pandas as pd


# ===================== CONFIG =====================
#REAL_CSV = Path(r"C:\Users\amira\OneDrive\Documents\Master 2\PFE\git\MindVoice-AI\modele_fusion_eda_bvp\base_test.csv")
#WESAD_MODEL_PATH = Path("models/eda_pr_global_xgb.joblib")  # ton modèle entraîné
#OUT_CSV = Path("outputs/inference_wesad_scores.csv")

REAL_CSV = Path("/Users/manelmoulahcene/Desktop/modele_fusion_eda_bvp/base_test.csv")
PROJECT_DIR = Path(__file__).resolve().parent
WESAD_MODEL_PATH = PROJECT_DIR / "models" / "wrist_eda_pr_global_xgb.joblib"
OUT_CSV = PROJECT_DIR / "outputs" / "inference_results.csv"

WIN_SEC = 60     # taille fenêtre en secondes
FS_REAL = 1      # base_test.csv : 1 ligne = 1 seconde (à adapter si besoin)
WIN = WIN_SEC * FS_REAL

EDA_COL = "eda_scl_usiemens"
PR_COL  = "pulse_rate_bpm"


TS_ISO_COL = "timestamp_iso"
TS_UNIX_COL = "timestamp_unix"


# ===================== FEATURES =====================
def extract_features_1d(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float64)
    mean = x.mean()
    std = x.std()
    mn = x.min()
    mx = x.max()
    rng = mx - mn
    t = np.arange(len(x), dtype=np.float64)
    slope = np.polyfit(t, x, 1)[0] if len(x) > 1 else 0.0
    mad = np.mean(np.abs(np.diff(x))) if len(x) > 1 else 0.0
    return np.array([mean, std, mn, mx, rng, slope, mad], dtype=np.float32)


def build_feature_vector(w_eda: np.ndarray, w_pr: np.ndarray) -> np.ndarray:
    f_eda = extract_features_1d(w_eda)
    f_pr  = extract_features_1d(w_pr)
    return np.concatenate([f_eda, f_pr], axis=0)  # 14 dims


# ===================== IO HELPERS =====================
def read_base_csv(p: Path) -> pd.DataFrame:
    
    try:
        df = pd.read_csv(p, sep=";", engine="python")
        if df.shape[1] == 1:
            df = pd.read_csv(p, sep=",", engine="python")
    except Exception:
        df = pd.read_csv(p, sep=",", engine="python")

    # Nettoyage noms colonnes
    df.columns = df.columns.astype(str).str.strip()

    # Si jamais tes décimales sont avec virgule, on force en numérique
    for c in [EDA_COL, PR_COL]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "."), errors="coerce")

    return df


def load_model(model_path: Path):
    obj = joblib.load(model_path)
    # ton training sauvegarde souvent {"model": model, "feature_names": ...}
    if isinstance(obj, dict) and "model" in obj:
        return obj["model"], obj.get("feature_names", None)
    # sinon c'est déjà un modèle sklearn/xgb
    return obj, None


# ===================== MAIN INFERENCE =====================
def main():
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    # 1) Load model
    model, feature_names = load_model(WESAD_MODEL_PATH)

    # 2) Load CSV
    df = read_base_csv(REAL_CSV)

    # 3) Check required cols
    missing = [c for c in [EDA_COL, PR_COL] if c not in df.columns]
    if missing:
        raise ValueError(
            f"Colonnes manquantes dans {REAL_CSV.name}: {missing}\n"
            f"Colonnes dispo: {list(df.columns)}"
        )

    # 4) Keep only needed cols (+ timestamps if present), drop NaNs
    keep_cols = [EDA_COL, PR_COL]
    if TS_ISO_COL in df.columns:
        keep_cols.append(TS_ISO_COL)
    if TS_UNIX_COL in df.columns:
        keep_cols.append(TS_UNIX_COL)

    df = df[keep_cols].dropna().reset_index(drop=True)

    if len(df) < WIN:
        raise ValueError(f"Pas assez de données: {len(df)} lignes. Il faut au moins {WIN} lignes (WIN_SEC={WIN_SEC}, FS_REAL={FS_REAL}).")

    n_win = len(df) // WIN
    print(f"Rows: {len(df)} | WIN={WIN} -> Windows: {n_win}")

    eda = df[EDA_COL].values.astype(np.float32)
    pr  = df[PR_COL].values.astype(np.float32)

    results = []
    for k in range(n_win):
        a = k * WIN
        b = (k + 1) * WIN

        w_eda = eda[a:b]
        w_pr  = pr[a:b]

        x = build_feature_vector(w_eda, w_pr).reshape(1, -1)  # (1, 14)

        # 5) Predict proba stress
        # predict_proba -> [P(class0), P(class1)]
        proba = model.predict_proba(x)[0]
        p_stress = float(proba[1]) if len(proba) >= 2 else float(proba[-1])

        row = {
            "window": k,
            "start_idx": a,
            "end_idx": b - 1,
            "p_stress": p_stress,
        }

        
        if TS_ISO_COL in df.columns:
            row["t_start_iso"] = df.loc[a, TS_ISO_COL]
            row["t_end_iso"]   = df.loc[b - 1, TS_ISO_COL]
        if TS_UNIX_COL in df.columns:
            row["t_start_unix"] = df.loc[a, TS_UNIX_COL]
            row["t_end_unix"]   = df.loc[b - 1, TS_UNIX_COL]

        results.append(row)

    out = pd.DataFrame(results)

    print("\nProba stress (windows): min/mean/max =",
          float(out["p_stress"].min()),
          float(out["p_stress"].mean()),
          float(out["p_stress"].max()))
    print("Exemples p_stress:", np.round(out["p_stress"].values[:10], 3))

    out.to_csv(OUT_CSV, index=False)
    print("\nSaved ->", OUT_CSV.resolve())


if __name__ == "__main__":
    main()
