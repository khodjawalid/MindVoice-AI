from pathlib import Path
import joblib
import numpy as np

from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report, confusion_matrix
from xgboost import XGBClassifier

DATASET_PATH = Path("outputs/wesad_wrist_eda_pr_dataset.joblib")
MODEL_OUT = Path("models/wrist_eda_pr_global_xgb.joblib")


def main():
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)

    ds = joblib.load(DATASET_PATH)
    X, y, groups = ds["X"], ds["y"], ds["groups"]

    print("Loaded dataset:", X.shape, np.unique(y, return_counts=True))
    print("Feature names:", ds.get("feature_names", None))

    # split par sujets
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y, groups=groups))
    X_train, y_train = X[tr], y[tr]
    X_test,  y_test  = X[te], y[te]

    # class imbalance
    pos = int((y_train == 1).sum())
    neg = int((y_train == 0).sum())
    scale_pos_weight = (neg / max(pos, 1))
    print(f"Train pos={pos} neg={neg} scale_pos_weight={scale_pos_weight:.3f}")

    # CPU par défaut (stable partout)
    model = XGBClassifier(
        n_estimators=800,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        tree_method="hist"
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\nConfusion matrix:\n", confusion_matrix(y_test, y_pred))
    print("\nReport:\n", classification_report(y_test, y_pred, digits=3))

    y_proba = model.predict_proba(X_test)[:, 1]
    print("Proba stress (test) : min/mean/max =",
      float(y_proba.min()), float(y_proba.mean()), float(y_proba.max()))
    print("Exemples proba:", np.round(y_proba[:10], 3))

    joblib.dump({"model": model, "feature_names": ds.get("feature_names", None)}, MODEL_OUT)
    print("\nModel saved ->", MODEL_OUT.resolve())


if __name__ == "__main__":
    main()



