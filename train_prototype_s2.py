from pathlib import Path
import pickle
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib



PKL_PATH = Path(r"C:/Users/amira/OneDrive/Documents/Master 2/PFE/base_donnees/S2/S2.pkl")
MODEL_OUT = Path("prototype_eda_rf.joblib")

FS_WRIST = 4
FS_LABEL = 700
RATIO = FS_LABEL // FS_WRIST  # 175

WIN_SEC = 60
WIN = FS_WRIST * WIN_SEC  # 240

VALID_LABELS = {1, 2, 3, 4}  # baseline, stress, amusement, meditation


""
def load_pkl(p: Path):
    with open(p, "rb") as f:
        return pickle.load(f, encoding="latin1")


def downsample_labels_majority(y700: np.ndarray, target_len: int, ratio: int) -> np.ndarray:
    y4 = np.zeros(target_len, dtype=int)
    for i in range(target_len):
        start = i * ratio
        end = start + ratio
        if end > len(y700):
            return y4[:i]
        chunk = y700[start:end]
        vals, counts = np.unique(chunk, return_counts=True)
        y4[i] = int(vals[np.argmax(counts)])
    return y4


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


def build_windows_from_subject(pkl_path: Path):
    data = load_pkl(pkl_path)

    eda = data["signal"]["wrist"]["EDA"].flatten()   # 4 Hz
    y700 = data["label"].flatten()                   # 700 Hz

    y4 = downsample_labels_majority(y700, target_len=len(eda), ratio=RATIO)

    # align lengths
    n = min(len(eda), len(y4))
    eda, y4 = eda[:n], y4[:n]

    # filter usable labels only
    mask = np.isin(y4, list(VALID_LABELS))
    eda, y4 = eda[mask], y4[mask]

    # windowing
    num_win = len(eda) // WIN
    X_list, y_list = [], []
    for w in range(num_win):
        start, end = w * WIN, (w + 1) * WIN
        xw = eda[start:end]
        yw = y4[start:end]

        # window label by majority vote
        vals, counts = np.unique(yw, return_counts=True)
        y_win = int(vals[np.argmax(counts)])

        X_list.append(extract_features_eda(xw))
        y_list.append(y_win)

    X = np.vstack(X_list)
    y_multi = np.array(y_list, dtype=int)
    y_bin = (y_multi == 2).astype(int)  # 1=stress, 0=non-stress

    return X, y_bin


if __name__ == "__main__":
    assert PKL_PATH.exists(), f"PKL introuvable: {PKL_PATH}"

    X, y = build_windows_from_subject(PKL_PATH)
    print("Dataset (S2) -> X:", X.shape, "y:", y.shape, "classes:", np.unique(y, return_counts=True))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print("\nConfusion matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, digits=3))

    joblib.dump(model, MODEL_OUT)
    print(f"\nModel saved -> {MODEL_OUT.resolve()}")
