import torch
print(torch.__version__)
#print(torch.randn(2,3))
import pickle 
import numpy as np
from pathlib import Path
#import matplotlib.pyplot as plt

PKL_PATH = Path(r"C:\Users\amira\OneDrive\Documents\Master 2\PFE\base_donnees\S2\S2.pkl")

with open(PKL_PATH, "rb") as f:
    data = pickle.load(f, encoding="latin1")


print("Keys:", data.keys())
print("Wrist keys:", data["signal"]["wrist"].keys())
print("Chest keys:", data["signal"]["chest"].keys())

eda_wrist = data["signal"]["wrist"]["EDA"].flatten()
labels700 = data["label"].flatten()

print("EDA wrist shape:", eda_wrist.shape)
print("labels700 shape:", labels700.shape)
print("labels uniques:", np.unique(labels700))


#passage de 700Hz à 4Hz + filtrage 
import numpy as np

eda = data["signal"]["wrist"]["EDA"].flatten()     # 4 Hz
labels700 = data["label"].flatten()               # 700 Hz

RATIO = 175  # 700/4

def downsample_labels_majority(y700, ratio, target_len):
    y4 = np.zeros(target_len, dtype=int)
    for i in range(target_len):
        start = i * ratio
        end = start + ratio
        if end > len(y700):
            y4 = y4[:i]
            break
        chunk = y700[start:end]
        vals, counts = np.unique(chunk, return_counts=True)
        y4[i] = vals[np.argmax(counts)]
    return y4

labels4 = downsample_labels_majority(labels700, RATIO, target_len=len(eda))

# aligner au cas où
n = min(len(eda), len(labels4))
eda = eda[:n]
labels4 = labels4[:n]

# garder seulement labels utiles (1..4)
mask = np.isin(labels4, [1, 2, 3, 4])
eda = eda[mask]
labels4 = labels4[mask]

print("Bracelet EDA after filter:", eda.shape)
print("Classes:", np.unique(labels4, return_counts=True))


# fenêtrage + features EDA 
FS = 4
WIN_SEC = 60
WIN = FS * WIN_SEC   # 240

def extract_features_eda(x):
    # x: 1 fenêtre EDA (240 points)
    dx = np.diff(x)
    feats = {
        "mean": float(np.mean(x)),
        "std": float(np.std(x)),
        "min": float(np.min(x)),
        "max": float(np.max(x)),
        "range": float(np.max(x) - np.min(x)),
        "slope": float((x[-1] - x[0]) / len(x)),          # tendance
        "mean_abs_diff": float(np.mean(np.abs(dx))),      # agitation
    }
    return feats

X_list = []
y_list = []

num_windows = len(eda) // WIN

for w in range(num_windows):
    start = w * WIN
    end = start + WIN

    xw = eda[start:end]
    yw = labels4[start:end]

    # label de la fenêtre = majority vote
    vals, counts = np.unique(yw, return_counts=True)
    y_win = int(vals[np.argmax(counts)])

    feats = extract_features_eda(xw)
    X_list.append(list(feats.values()))
    y_list.append(y_win)

feature_names = list(extract_features_eda(eda[:WIN]).keys())
X = np.array(X_list, dtype=float)
y = np.array(y_list, dtype=int)

print("Windowed dataset X:", X.shape, "y:", y.shape)
print("Feature names:", feature_names)
print("Window classes:", np.unique(y, return_counts=True))


y_bin = (y == 2).astype(int)  # 1 = stress, 0 = autres
print("Binary classes:", np.unique(y_bin, return_counts=True))
