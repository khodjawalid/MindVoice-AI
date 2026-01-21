import numpy as np
import pandas as pd
from pathlib import Path
import joblib

# ====== A MODIFIER ======
TAG_EVENTS_CSV = r"C:\Users\amira\OneDrive\Documents\Master 2\PFE\git\MindVoice-AI\modele_fusion_eda_bvp\tag_events_fusion_v2.csv"
OUT_DIR = r"C:\Users\amira\OneDrive\Documents\Master 2\PFE\personalization_out"
OUT_NAME = "personal_thresholds_eda_pr.joblib"
# ========================

WIN_SEC = 10     # fenêtre 60s
FS = 1           # ton CSV: 1 ligne / seconde
WIN = WIN_SEC * FS

EDA_CANDIDATES = ["eda_scl_usiemens", "eda"]
PR_CANDIDATES  = ["pulse_rate_bpm", "pulse_rate", "pr", "heart_rate_bpm", "hr"]
LABEL_COL = "label"

ALLOWED = {"stress", "neutre"}

def to_float_series(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .str.replace("\ufeff", "", regex=False)
         .str.strip()
         .str.replace(",", ".", regex=False)
         .replace({"": np.nan, "nan": np.nan, "None": np.nan})
         .astype(float)
    )

def main():
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(TAG_EVENTS_CSV, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = df.columns.str.replace("\ufeff", "", regex=False).str.strip().str.lower()
    df = df.loc[:, ~df.columns.str.contains("^unnamed")]

    if LABEL_COL not in df.columns:
        raise ValueError(f"Colonne 'label' manquante. Colonnes={list(df.columns)}")

    eda_col = next((c for c in EDA_CANDIDATES if c in df.columns), None)
    pr_col  = next((c for c in PR_CANDIDATES  if c in df.columns), None)
    if eda_col is None or pr_col is None:
        raise ValueError(f"Je ne trouve pas EDA/PR. Colonnes={list(df.columns)}")

    df[LABEL_COL] = df[LABEL_COL].astype(str).str.strip().str.lower()
    df = df[df[LABEL_COL].isin(ALLOWED)].copy()

    df[eda_col] = to_float_series(df[eda_col])
    df[pr_col]  = to_float_series(df[pr_col])
    df = df.dropna(subset=[eda_col, pr_col, LABEL_COL]).reset_index(drop=True)

    print("Rows usable:", len(df))
    print("Counts:", df[LABEL_COL].value_counts().to_dict())

    # ----- fenêtrage -----
    eda = df[eda_col].to_numpy(dtype=np.float32)
    pr  = df[pr_col].to_numpy(dtype=np.float32)
    lab = df[LABEL_COL].to_numpy()

    n_win = len(df) // WIN
    if n_win == 0:
        raise ValueError("0 fenêtre générée. Ajoute des données ou réduis WIN_SEC.")

    eda_mean, pr_mean, y_win = [], [], []
    for k in range(n_win):
        a, b = k * WIN, (k + 1) * WIN
        w_lab = lab[a:b]
        vals, cnts = np.unique(w_lab, return_counts=True)
        y = vals[np.argmax(cnts)]

        eda_mean.append(float(np.mean(eda[a:b])))
        pr_mean.append(float(np.mean(pr[a:b])))
        y_win.append(y)

    eda_mean = np.array(eda_mean, dtype=np.float32)
    pr_mean  = np.array(pr_mean, dtype=np.float32)
    y_win    = np.array(y_win)

    # ----- normalisation perso (sur tes fenêtres) -----
    mu_eda, sd_eda = float(eda_mean.mean()), float(eda_mean.std() + 1e-8)
    mu_pr,  sd_pr  = float(pr_mean.mean()),  float(pr_mean.std() + 1e-8)

    z_eda = (eda_mean - mu_eda) / sd_eda
    z_pr  = (pr_mean  - mu_pr)  / sd_pr

    alpha, beta = 1.0, 1.0
    S = alpha * z_eda + beta * z_pr

    S_stress = S[y_win == "stress"]
    S_neutre = S[y_win == "neutre"]

    if len(S_stress) == 0 or len(S_neutre) == 0:
        raise ValueError("Il faut au moins 1 fenêtre stress ET 1 fenêtre neutre pour calculer les seuils.")

    # seuils “par classe” (pas de décision ici)
    # neutre: seuil haut typique
    neutre_high = float(np.percentile(S_neutre, 90))
    # stress: seuil bas typique
    stress_low  = float(np.percentile(S_stress, 10))

    print("\n--- PERSONAL THRESHOLDS (NO DECISION) ---")
    print("mu/std EDA:", mu_eda, sd_eda)
    print("mu/std PR :", mu_pr, sd_pr)
    print("neutre_high (P90 neutre):", neutre_high)
    print("stress_low  (P10 stress):", stress_low)
    print("alpha,beta:", alpha, beta)

    out_path = Path(OUT_DIR) / OUT_NAME
    joblib.dump(
        {
            "eda_col": eda_col,
            "pr_col": pr_col,
            "win_sec": WIN_SEC,
            "fs": FS,
            "alpha": alpha,
            "beta": beta,
            "mu_eda": mu_eda,
            "sd_eda": sd_eda,
            "mu_pr": mu_pr,
            "sd_pr": sd_pr,
            "neutre_high": neutre_high,
            "stress_low": stress_low,
            "classes": ["neutre", "stress"],
            "source_csv": TAG_EVENTS_CSV,
        },
        out_path
    )
    print("\nSaved ->", out_path.resolve())

if __name__ == "__main__":
    main()
