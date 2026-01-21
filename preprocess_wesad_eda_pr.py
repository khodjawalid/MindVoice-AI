from pathlib import Path
import pickle
import numpy as np
import joblib

# -------- CONFIG --------
#DATA_DIR = Path(r"C:\Users\amira\OneDrive\Documents\Master 2\PFE\base_donnees")  # S2.pkl ... S17.pkl
#OUT_DATASET = Path("outputs/wesad_wrist_eda_pr_dataset.joblib")
DATA_DIR = Path("/Users/manelmoulahcene/Desktop/modele_fusion_eda_bvp/WESAD")
OUT_DATASET = Path("outputs/wesad_wrist_eda_pr_dataset.joblib")

FS_EDA = 4
FS_LABEL = 700
RATIO = FS_LABEL // FS_EDA  # 175

WIN_SEC = 60
WIN = FS_EDA * WIN_SEC      # 240

VALID_LABELS = {1, 2, 3, 4}  # baseline, stress, amusement, meditation
STRESS_LABEL = 2


# -------- FEATURES --------
def extract_features_1d(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float64)
    mean = x.mean()
    std = x.std()
    mn = x.min()
    mx = x.max()
    rng = mx - mn
    t = np.arange(len(x))
    slope = np.polyfit(t, x, 1)[0] if len(x) > 1 else 0.0
    mad = np.mean(np.abs(np.diff(x))) if len(x) > 1 else 0.0
    return np.array([mean, std, mn, mx, rng, slope, mad], dtype=np.float32)


FEATURE_NAMES = (
    [f"eda_{n}" for n in ["mean", "std", "min", "max", "range", "slope", "mean_abs_diff"]]
    + [f"pr_{n}"  for n in ["mean", "std", "min", "max", "range", "slope", "mean_abs_diff"]]
)


# -------- HELPERS --------
def load_pkl(p: Path) -> dict:
    with open(p, "rb") as f:
        return pickle.load(f, encoding="latin1")


def downsample_mean(x: np.ndarray, factor: int) -> np.ndarray:
    n = (len(x) // factor) * factor
    if n <= 0:
        return np.array([], dtype=np.float32)
    return x[:n].reshape(-1, factor).mean(axis=1).astype(np.float32)


def _moving_average(x: np.ndarray, w: int) -> np.ndarray:#revoir 
    if w <= 1:
        return x
    w = int(w)
    kernel = np.ones(w, dtype=np.float32) / w
    return np.convolve(x, kernel, mode="same").astype(np.float32)


def bvp_to_hr_bpm(bvp: np.ndarray, fs_bvp: int = 64) -> np.ndarray:
    """
    Estime un HR (bpm) à partir du BVP via détection de pics simple .
    Retour: hr_bpm au pas d'échantillonnage du BVP (fs_bvp).
    """
    x = bvp.astype(np.float32).copy()
    if len(x) < fs_bvp * 5:
        # trop court => fallback constant
        return np.full_like(x, 75.0, dtype=np.float32)

    # 1) "detrend" léger + lissage
    x = x - _moving_average(x, w=int(fs_bvp * 1.0))       # retire tendance ~1s #supprimer la moyenne lente qui est due au mvts, respiration etc ( enlevre dérive lente)
    x = _moving_average(x, w=int(fs_bvp * 0.15))          # lisse ~150ms #enlever les micro oscillatiosn parasite (enlève bruit rapide) 

    # 2) normalisation robuste #mettre le signal sur une échelle stable 
    med = np.median(x)
    mad = np.median(np.abs(x - med)) + 1e-6
    xz = (x - med) / mad

    # 3) détection pics: max locaux + seuil + période réfractaire
    #    (on vise 40-200 bpm => 0.3s à 1.5s entre pics)
    refractory = int(0.30 * fs_bvp)  # 300ms #limite de battements par minute pour un etre humain #fs_bvp : fréquzence d'échantillonage du signal bvp 
    # seuil: on prend un quantile (évite d'être trop strict)
    thr = np.quantile(xz, 0.75) #xz est centé autour de 0 car in avait centré juste avant et 0.75 ets le seuil pour prendre que des vrais pics 

    peaks = []
    last = -10**9
    for i in range(1, len(xz) - 1): #detection de maximum local 
        if i - last < refractory:
            continue
        if xz[i] > thr and xz[i] >= xz[i - 1] and xz[i] >= xz[i + 1]:
            peaks.append(i)
            last = i

    peaks = np.array(peaks, dtype=int) #indices ou il ya les pics détéctés 

    if len(peaks) < 3: 
        # fallback si peu de pics
        return np.full_like(x, 75.0, dtype=np.float32)

    # 4) RR intervals -> bpm, puis "hold" entre pics
    rr = np.diff(peaks) / float(fs_bvp)               # en secondes #distance entre deux battements (en samples) #
    bpm_inst = 60.0 / np.clip(rr, 0.30, 1.50)         # borne 40-200 bpm environ

    hr = np.zeros(len(x), dtype=np.float32)
    # avant 1er pic: valeur initiale
    hr[:peaks[0]] = float(np.median(bpm_inst))
    for k in range(len(bpm_inst)):
        a = peaks[k]
        b = peaks[k + 1]
        hr[a:b] = float(bpm_inst[k])
    # après dernier pic
    hr[peaks[-1]:] = float(bpm_inst[-1])

    # clip final (
    hr = np.clip(hr, 40.0, 200.0).astype(np.float32) 
    return hr


def get_pr_bpm_aligned_to_eda_wrist_only(data: dict, n_eda: int) -> np.ndarray:
    """
    Wrist 
    - On prend BVP (64Hz)
    - On estime HR en bpm
    - On downsample à 4Hz (comme EDA)
    - On pad/crop à n_eda
    """
    try:
        bvp = data["signal"]["wrist"]["BVP"].flatten().astype(np.float32)  # 64 Hz
    except Exception:
        return np.zeros(n_eda, dtype=np.float32)

    hr_bpm_64 = bvp_to_hr_bpm(bvp, fs_bvp=64)          # bpm @64Hz
    pr4 = downsample_mean(hr_bpm_64, factor=16)        # 64/16=4Hz

    if len(pr4) >= n_eda:
        return pr4[:n_eda]
    if len(pr4) == 0:
        return np.zeros(n_eda, dtype=np.float32)
    return np.pad(pr4, (0, n_eda - len(pr4)), mode="edge").astype(np.float32)


# -------- CORE --------
def subject_to_windows(data: dict, subject_id: int):
    # wrist 
    eda = data["signal"]["wrist"]["EDA"].flatten()
    labels700 = data["label"].flatten()

    # align label -> wrist EDA (EDA 4Hz, label 700Hz)
    L = min(len(eda), len(labels700) // RATIO)
    eda = eda[:L]
    lab = labels700[:L * RATIO:RATIO]

    # keep only labels 1..4
    m = np.isin(lab, list(VALID_LABELS))
    eda = eda[m]
    lab = lab[m]

    # binaire stress vs non-stress
    y_point = (lab == STRESS_LABEL).astype(np.int64)

    # PR (bpm) wrist, aligné sur EDA
    pr = get_pr_bpm_aligned_to_eda_wrist_only(data, n_eda=len(eda))

    # windowing (non-overlap)
    n_win = len(eda) // WIN
    X_list, y_list, g_list = [], [], []

    for k in range(n_win):
        w_eda = eda[k * WIN:(k + 1) * WIN]
        w_pr  = pr[k * WIN:(k + 1) * WIN]

        feats = np.concatenate(
            [extract_features_1d(w_eda), extract_features_1d(w_pr)],
            axis=0
        )  # 14 features

        y_w = y_point[k * WIN:(k + 1) * WIN]
        label = int(np.mean(y_w) >= 0.5)  # majority

        X_list.append(feats)
        y_list.append(label)
        g_list.append(subject_id)

    if not X_list:
        return None, None, None

    return np.vstack(X_list), np.array(y_list), np.array(g_list)


def main():
    OUT_DATASET.parent.mkdir(parents=True, exist_ok=True)

    #pkl_files = sorted(DATA_DIR.glob("S*.pkl"))
    pkl_files = sorted(DATA_DIR.rglob("S*.pkl"))
    if not pkl_files:
        raise FileNotFoundError(f"Aucun S*.pkl trouvé dans : {DATA_DIR}")

    X_all, y_all, g_all = [], [], []

    for p in pkl_files:
        sid = int(p.stem.replace("S", ""))
        data = load_pkl(p)

        Xs, ys, gs = subject_to_windows(data, sid)
        if Xs is None:
            print(f"{p.stem}: SKIP (pas assez de données)")
            continue

        print(f"{p.stem}: X={Xs.shape} y={ys.shape} stress={ys.sum()}/{len(ys)}")
        X_all.append(Xs)
        y_all.append(ys)
        g_all.append(gs)

    X = np.vstack(X_all)
    y = np.concatenate(y_all)
    groups = np.concatenate(g_all)

    print("\nGlobal dataset:", X.shape, "classes:", np.unique(y, return_counts=True))

    joblib.dump(
        {"X": X, "y": y, "groups": groups, "feature_names": FEATURE_NAMES},
        OUT_DATASET
    )
    print("Saved ->", OUT_DATASET.resolve())


if __name__ == "__main__":
    main()
