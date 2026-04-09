from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    import joblib
except Exception as e:
    raise RuntimeError("Install joblib: python -m pip install joblib") from e

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except Exception as e:
    raise RuntimeError("Install scikit-learn: python -m pip install scikit-learn") from e


ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "Airbnb_Open_Data.csv"
OUT_PATH = ROOT / "backend" / "models" / "conversion_model.joblib"


def _to_float(s, default=0.0) -> float:
    try:
        x = float(s)
        if np.isnan(x):
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def build_training_frame(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    # This dataset doesn't include true bookings. We train a proxy "conversion" label:
    # available_nights_low (more booked historically) + strong reviews => higher conversion likelihood.
    feature_order = [
        "price",
        "review_rate",
        "reviews_count",
        "availability_365",
        "instant_bookable",
        "room_type_private",
        "room_type_shared",
        "room_type_entire",
    ]

    X = []
    y = []
    for _, r in df.iterrows():
        price = _to_float(r.get("price"), default=np.nan)
        rr = _to_float(r.get("review rate number"), default=3.5)
        rc = _to_float(r.get("number of reviews"), default=0.0)
        av = _to_float(r.get("availability 365"), default=200.0)
        inst = 1.0 if str(r.get("instant_bookable", "")).strip().lower() in ("true", "t", "1", "yes") else 0.0

        rt = str(r.get("room type") or "").lower()
        rt_private = 1.0 if "private" in rt else 0.0
        rt_shared = 1.0 if "shared" in rt else 0.0
        rt_entire = 1.0 if "entire" in rt else 0.0

        # Robust price parse (handle "$123")
        if isinstance(price, float) and np.isnan(price):
            ps = str(r.get("price") or "").replace("$", "").replace(",", "").strip()
            price = _to_float(ps, default=150.0)

        feats = [
            float(price),
            float(rr),
            float(rc),
            float(av),
            float(inst),
            float(rt_private),
            float(rt_shared),
            float(rt_entire),
        ]

        # Proxy conversion label (0/1)
        label = 1.0 if (av < 180 and rr >= 3.6) else 0.0
        X.append(feats)
        y.append(label)

    return np.asarray(X, dtype=float), np.asarray(y, dtype=int), feature_order


def main() -> int:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing dataset: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, low_memory=False).head(15000)
    X, y, feature_order = build_training_frame(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None
    )

    clf = Pipeline(
        steps=[
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("lr", LogisticRegression(max_iter=500)),
        ]
    )
    clf.fit(X_train, y_train)
    score = clf.score(X_test, y_test)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "feature_order": feature_order, "test_accuracy": float(score)}, str(OUT_PATH))
    print(f"Saved: {OUT_PATH}")
    print(f"Proxy test accuracy: {score:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

