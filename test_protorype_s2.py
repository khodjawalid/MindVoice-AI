from pathlib import Path
import pickle
import numpy as np
import joblib


# ====== CONFIG ======
PKL_PATH = Path(r"C:/Users/amira/OneDrive/Documents/Master 2/PFE/base_donnees/S2/S2.pkl")
MODEL_PATH = Path("prototype_eda_rf.joblib")

FS_WRIST = 4
WIN_SEC = 60
WIN = FS_WRIST * WIN_SEC  # 240

THRESH = 0.6  # seuil de décision


# ====== UTILS ======
def load_pkl(p: Path):
    with open(p, "rb") as f:
        return pickle.load(f, encoding="latin1")

def extract_features_eda(x: np.ndarray) -> np.ndarray:
    dx = np.diff(x)
    return np.array([
        np.mean(x),
        np.std(x),
        np.min(x),
        np.max(x),
        np.max(x) - np.min(x),
        (x[-1] - x[0]) / len(x),
        np.mean(np.abs(dx)),
    ], dtype=float)

if __name__ == "__main__":
    assert PKL_PATH.exists(), f"PKL introuvable: {PKL_PATH}"
    assert MODEL_PATH.exists(), f"Modèle introuvable: {MODEL_PATH} (lance train_prototype_s2.py d'abord)"

    data = load_pkl(PKL_PATH)
    eda = data["signal"]["wrist"]["EDA"].flatten()

    model = joblib.load(MODEL_PATH)


    start = len(eda)//2
    start = start - (start % WIN)
    xw = eda[start:start+WIN]

    feats = extract_features_eda(xw).reshape(1, -1)

 
    p_stress = float(model.predict_proba(feats)[0][1])
    score_0_100 = round(p_stress * 100, 1)

    decision = "STRESS" if p_stress >= THRESH else "NON-STRESS"

    print(f"Window: [{start} .. {start+WIN}] ({WIN_SEC}s)")
    print(f"Stress probability: {p_stress:.3f}")
    print(f"Stress score: {score_0_100}/100")
    print(f"Decision (threshold {THRESH}): {decision}")
