"""
Train a first-pass lodging nightly price model on Airbnb_Open_Data.csv.

Goal (client demo):
- Show measurable accuracy (MAE / RMSE / R² / MAPE)
- Produce example predictions
- Save a model artifact for reuse

This script predicts the dataset's `price` column (nightly price) using available listing attributes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import HistGradientBoostingRegressor


PRICE_RE = re.compile(r"[^\d.\-]+")


def _stable_hash_to_int(s: str) -> int:
    # Deterministic hash for repeatable per-row pseudo-randomness
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return int(h)


def _to_bool01(x: Any) -> float:
    s = str(x).strip().lower()
    if s in {"true", "t", "1", "yes", "y"}:
        return 1.0
    if s in {"false", "f", "0", "no", "n"}:
        return 0.0
    return float("nan")


def parse_money_to_float(x: Any) -> float:
    if x is None:
        return float("nan")
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip()
    if not s:
        return float("nan")
    # remove currency, commas, spaces, etc.
    s = PRICE_RE.sub("", s)
    try:
        return float(s)
    except ValueError:
        return float("nan")


def safe_bool(x: Any) -> Optional[bool]:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    s = str(x).strip().lower()
    if s in {"true", "t", "1", "yes", "y"}:
        return True
    if s in {"false", "f", "0", "no", "n"}:
        return False
    return None


def parse_date_to_ordinal(x: Any) -> float:
    if x is None:
        return float("nan")
    s = str(x).strip()
    if not s:
        return float("nan")
    # Dataset seems like M/D/YYYY
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return float(dt.toordinal())
        except ValueError:
            pass
    return float("nan")


@dataclass
class Metrics:
    mae: float
    rmse: float
    r2: float
    mape: float


@dataclass
class AccuracyLike:
    within_10pct: float
    within_20pct: float
    within_50_abs: float
    within_100_abs: float
    median_abs_error: float


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Metrics:
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    # avoid division by zero
    denom = np.maximum(np.abs(y_true), 1e-6)
    mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100.0)
    return Metrics(mae=mae, rmse=rmse, r2=r2, mape=mape)


def compute_accuracy_like(y_true: np.ndarray, y_pred: np.ndarray) -> AccuracyLike:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    abs_err = np.abs(y_true - y_pred)
    pct_err = abs_err / np.maximum(np.abs(y_true), 1e-6)

    return AccuracyLike(
        within_10pct=float(np.mean(pct_err <= 0.10) * 100.0),
        within_20pct=float(np.mean(pct_err <= 0.20) * 100.0),
        within_50_abs=float(np.mean(abs_err <= 50.0) * 100.0),
        within_100_abs=float(np.mean(abs_err <= 100.0) * 100.0),
        median_abs_error=float(np.median(abs_err)),
    )


def baseline_predict_median(y_train: pd.Series, n: int) -> np.ndarray:
    # Simple baseline: always predict the training median price
    return np.full(shape=(n,), fill_value=float(np.median(y_train.to_numpy())), dtype=float)


def build_pipeline(numeric_features: List[str], categorical_features: List[str]) -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            # Dense output because HistGradientBoostingRegressor doesn't accept sparse input.
            # min_frequency reduces cardinality explosion for high-cardinality categoricals.
            ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=50, sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ],
        remainder="drop",
        sparse_threshold=0.0,
    )

    # Strong baseline for tabular data; fast and works well without heavy tuning.
    model = HistGradientBoostingRegressor(
        loss="squared_error",
        max_depth=6,
        learning_rate=0.08,
        max_iter=400,
        random_state=42,
    )

    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def load_and_prepare(
    csv_path: Path,
    *,
    include_ids: bool,
    include_service_fee: bool,
    add_mock_columns: bool,
    seed: int,
) -> Tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(csv_path, low_memory=False)

    # Target
    y = df["price"].map(parse_money_to_float)

    # Basic feature engineering grounded in available columns
    df = df.copy()
    df["service_fee_num"] = df.get("service fee", pd.Series([np.nan] * len(df))).map(parse_money_to_float)
    df["instant_bookable_bool"] = df.get("instant_bookable", pd.Series([None] * len(df))).map(safe_bool)
    df["last_review_ordinal"] = df.get("last review", pd.Series([np.nan] * len(df))).map(parse_date_to_ordinal)

    # Optional: add synthetic hotel-style columns for demos (no direct use of target price).
    if add_mock_columns:
        n = len(df)
        rng = np.random.default_rng(seed)

        review_rate = pd.to_numeric(df.get("review rate number"), errors="coerce")
        reviews_cnt = pd.to_numeric(df.get("number of reviews"), errors="coerce").fillna(0)
        reviews_per_month = pd.to_numeric(df.get("reviews per month"), errors="coerce").fillna(0)
        min_nights = pd.to_numeric(df.get("minimum nights"), errors="coerce").fillna(1)
        availability = pd.to_numeric(df.get("availability 365"), errors="coerce")
        instant_bookable = df.get("instant_bookable", pd.Series([None] * n)).map(_to_bool01)

        room_type = df.get("room type", pd.Series(["Unknown"] * n)).astype(str).fillna("Unknown")
        nb_group = df.get("neighbourhood group", pd.Series(["Unknown"] * n)).astype(str).fillna("Unknown")

        bedroom_base = np.where(room_type.str.contains("entire", case=False), 1.0, 0.0)
        bedrooms = np.clip(np.round(bedroom_base + rng.normal(0.4, 0.6, size=n)), 0, 5).astype(int)
        bathrooms = np.clip(np.round(bedrooms * 0.8 + rng.normal(0.3, 0.5, size=n)), 0, 4).astype(int)
        accommodates = np.clip(bedrooms * 2 + rng.integers(0, 3, size=n) + 1, 1, 10).astype(int)

        quality_proxy = (
            (review_rate.fillna(3.5) / 5.0) * 0.6
            + np.tanh(reviews_per_month / 2.0) * 0.2
            + np.tanh(reviews_cnt / 50.0) * 0.2
        )
        amenities_count = np.clip(
            np.round(10 + 25 * quality_proxy + rng.normal(0, 3, size=n)),
            5,
            60,
        ).astype(int)
        star_rating = np.clip(
            np.round(3.2 + 1.8 * quality_proxy + rng.normal(0, 0.3, size=n), 1),
            1.0,
            5.0,
        )

        market_tier_map: Dict[str, int] = {
            "Manhattan": 3,
            "Brooklyn": 2,
            "Queens": 2,
            "Bronx": 1,
            "Staten Island": 1,
        }
        market_tier = nb_group.map(lambda x: market_tier_map.get(str(x), 2)).astype(int)

        occ_from_avail = 1.0 - (availability.fillna(365) / 365.0)
        occupancy_rate = np.clip(0.25 + 0.60 * occ_from_avail + rng.normal(0, 0.08, size=n), 0.05, 0.98)
        demand_index = (
            0.8
            + 0.25 * (market_tier - 2)
            + 0.10 * np.nan_to_num(instant_bookable, nan=0.0)
            + 0.20 * (occupancy_rate - 0.5)
            + rng.normal(0, 0.10, size=n)
        )
        demand_index = np.clip(demand_index, 0.2, 2.0)

        lead_time_days = np.clip(np.round(rng.gamma(shape=2.0, scale=10.0, size=n)), 0, 180).astype(int)
        length_of_stay = np.clip(
            np.round(rng.gamma(shape=2.0, scale=2.0, size=n) + min_nights / 5.0),
            1,
            30,
        ).astype(int)
        weekend_share = np.clip(0.25 + rng.normal(0, 0.08, size=n), 0.05, 0.60)
        peak_season_share = np.clip(0.20 + 0.10 * (market_tier - 2) + rng.normal(0, 0.06, size=n), 0.05, 0.60)

        df["mock_bedrooms"] = bedrooms
        df["mock_bathrooms"] = bathrooms
        df["mock_accommodates"] = accommodates
        df["mock_amenities_count"] = amenities_count
        df["mock_star_rating"] = star_rating
        df["mock_market_tier"] = market_tier
        df["mock_occupancy_rate"] = occupancy_rate
        df["mock_demand_index"] = demand_index
        df["mock_lead_time_days"] = lead_time_days
        df["mock_length_of_stay"] = length_of_stay
        df["mock_weekend_share"] = weekend_share
        df["mock_peak_season_share"] = peak_season_share
        if "id" in df.columns:
            df["mock_listing_seed"] = df["id"].astype(str).map(_stable_hash_to_int)

    # Drop columns we should not use (leakage / too-free-text / identifiers)
    drop_cols = {
        "price",
        "NAME",
        "house_rules",
        "host name",
        "license",
        # raw last review (we use ordinal instead)
        "last review",
    }
    if not include_ids:
        # identifiers can let the model memorize
        drop_cols |= {"id", "host id"}
    if not include_service_fee:
        # service fee is often derived from price (target leakage risk)
        drop_cols |= {"service fee", "service_fee_num"}
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    # A little cleanup for weird blanks
    X.replace({"": np.nan, " ": np.nan}, inplace=True)

    # Remove rows with missing/invalid target
    mask = (~y.isna()) & (y > 0)
    X = X.loc[mask].reset_index(drop=True)
    y = y.loc[mask].reset_index(drop=True)

    return X, y


def infer_feature_types(X: pd.DataFrame) -> Tuple[List[str], List[str]]:
    # Explicitly treat some known fields as categorical, even if they look numeric-ish.
    force_categorical = {
        "host_identity_verified",
        "neighbourhood group",
        "neighbourhood",
        "country",
        "country code",
        "cancellation_policy",
        "room type",
        "instant_bookable",
        "instant_bookable_bool",
    }

    numeric_features: List[str] = []
    categorical_features: List[str] = []

    for col in X.columns:
        if col in force_categorical:
            categorical_features.append(col)
            continue
        if pd.api.types.is_bool_dtype(X[col]):
            categorical_features.append(col)
            continue
        if pd.api.types.is_numeric_dtype(X[col]):
            numeric_features.append(col)
            continue
        # Try to coerce object columns that are mostly numeric
        if X[col].dtype == "object":
            # If it parses to numeric for most values, keep numeric.
            coerced = pd.to_numeric(X[col], errors="coerce")
            non_na_ratio = float(coerced.notna().mean())
            if non_na_ratio >= 0.80:
                X[col] = coerced
                numeric_features.append(col)
            else:
                categorical_features.append(col)
        else:
            categorical_features.append(col)

    if "last_review_ordinal" in X.columns and "last_review_ordinal" not in numeric_features:
        numeric_features.append("last_review_ordinal")

    return numeric_features, categorical_features


def cross_val_report(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series, k: int) -> Dict[str, Any]:
    kf = KFold(n_splits=k, shuffle=True, random_state=42)
    fold_metrics: List[Metrics] = []
    fold_acc: List[AccuracyLike] = []

    for train_idx, test_idx in kf.split(X):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        pipeline.fit(X_tr, y_tr)
        preds = pipeline.predict(X_te)
        fold_metrics.append(compute_metrics(y_te.to_numpy(), preds))
        fold_acc.append(compute_accuracy_like(y_te.to_numpy(), preds))

    return {
        "k": k,
        "folds": [asdict(m) for m in fold_metrics],
        "folds_accuracy_like": [asdict(a) for a in fold_acc],
        "mean": {
            "mae": float(np.mean([m.mae for m in fold_metrics])),
            "rmse": float(np.mean([m.rmse for m in fold_metrics])),
            "r2": float(np.mean([m.r2 for m in fold_metrics])),
            "mape": float(np.mean([m.mape for m in fold_metrics])),
            "within_10pct": float(np.mean([a.within_10pct for a in fold_acc])),
            "within_20pct": float(np.mean([a.within_20pct for a in fold_acc])),
            "within_50_abs": float(np.mean([a.within_50_abs for a in fold_acc])),
            "within_100_abs": float(np.mean([a.within_100_abs for a in fold_acc])),
            "median_abs_error": float(np.mean([a.median_abs_error for a in fold_acc])),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="Airbnb_Open_Data.csv", help="Path to Airbnb CSV")
    ap.add_argument(
        "--outdir",
        default="artifacts_no_leak",
        help="Output directory for model + reports",
    )
    ap.add_argument("--test_size", type=float, default=0.2, help="Holdout split size")
    ap.add_argument("--cv", type=int, default=5, help="K-fold CV folds (0 to disable)")
    ap.add_argument(
        "--include_ids",
        action="store_true",
        help="Include listing/host IDs as features (HIGH leakage risk; can inflate accuracy).",
    )
    ap.add_argument(
        "--include_service_fee",
        action="store_true",
        help="Include service fee features (leakage risk; default: excluded).",
    )
    ap.add_argument("--clip_q_low", type=float, default=0.01, help="Lower quantile clip for target (0 disables)")
    ap.add_argument("--clip_q_high", type=float, default=0.99, help="Upper quantile clip for target (0 disables)")
    ap.add_argument("--log_target", action="store_true", help="Train on log(price) and back-transform predictions")
    ap.add_argument(
        "--add_mock_columns",
        action="store_true",
        help="Add synthetic hotel-style columns for demo (does not use target price directly).",
    )
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    args = ap.parse_args()

    csv_path = Path(args.csv).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    X, y = load_and_prepare(
        csv_path,
        include_ids=bool(args.include_ids),
        include_service_fee=bool(args.include_service_fee),
        add_mock_columns=bool(args.add_mock_columns),
        seed=int(args.seed),
    )

    # Optional target clipping to reduce extreme outliers (more stable client-facing metrics).
    if args.clip_q_low and args.clip_q_high and 0 < args.clip_q_low < args.clip_q_high < 1:
        lo = float(y.quantile(args.clip_q_low))
        hi = float(y.quantile(args.clip_q_high))
        keep = (y >= lo) & (y <= hi)
        X = X.loc[keep].reset_index(drop=True)
        y = y.loc[keep].reset_index(drop=True)
    numeric_features, categorical_features = infer_feature_types(X)
    pipeline = build_pipeline(numeric_features, categorical_features)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed
    )

    if args.log_target:
        pipeline.fit(X_train, np.log1p(y_train.to_numpy()))
        preds = np.expm1(pipeline.predict(X_test))
    else:
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
    metrics = compute_metrics(y_test.to_numpy(), preds)
    acc_like = compute_accuracy_like(y_test.to_numpy(), preds)

    # Baseline comparison (helps explain whether model is actually learning)
    baseline_preds = baseline_predict_median(y_train, n=len(y_test))
    baseline_metrics = compute_metrics(y_test.to_numpy(), baseline_preds)
    baseline_acc_like = compute_accuracy_like(y_test.to_numpy(), baseline_preds)

    # Save model
    model_path = outdir / "lodging_price_model.joblib"
    dump(
        {
            "pipeline": pipeline,
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "target": "price",
            "csv": str(csv_path),
            "log_target": bool(args.log_target),
            "clip_q_low": float(args.clip_q_low),
            "clip_q_high": float(args.clip_q_high),
            "include_ids": bool(args.include_ids),
            "include_service_fee": bool(args.include_service_fee),
        },
        model_path,
    )

    # Example predictions (client-friendly)
    sample = X_test.copy().reset_index(drop=True)
    sample_y = y_test.reset_index(drop=True)
    sample["actual_price"] = sample_y
    sample["predicted_price"] = preds
    sample["abs_error"] = np.abs(sample["actual_price"] - sample["predicted_price"])
    example_path = outdir / "example_predictions.csv"
    sample.sort_values("abs_error", ascending=False).head(50).to_csv(example_path, index=False)

    report: Dict[str, Any] = {
        "dataset_rows_used": int(len(X)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "holdout_metrics": asdict(metrics),
        "holdout_accuracy_like": asdict(acc_like),
        "baseline_holdout_metrics": asdict(baseline_metrics),
        "baseline_holdout_accuracy_like": asdict(baseline_acc_like),
        "artifacts": {
            "model": str(model_path),
            "example_predictions": str(example_path),
        },
    }

    if args.cv and args.cv >= 2:
        if args.log_target:
            kf = KFold(n_splits=args.cv, shuffle=True, random_state=42)
            fold_metrics: List[Metrics] = []
            for tr_idx, te_idx in kf.split(X):
                X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
                y_tr, y_te = y.iloc[tr_idx], y.iloc[te_idx]
                pipeline.fit(X_tr, np.log1p(y_tr.to_numpy()))
                pr = np.expm1(pipeline.predict(X_te))
                fold_metrics.append(compute_metrics(y_te.to_numpy(), pr))
            report["cross_validation"] = {
                "k": int(args.cv),
                "folds": [asdict(m) for m in fold_metrics],
                "mean": {
                    "mae": float(np.mean([m.mae for m in fold_metrics])),
                    "rmse": float(np.mean([m.rmse for m in fold_metrics])),
                    "r2": float(np.mean([m.r2 for m in fold_metrics])),
                    "mape": float(np.mean([m.mape for m in fold_metrics])),
                },
            }
        else:
            report["cross_validation"] = cross_val_report(pipeline, X, y, k=args.cv)

    report_path = outdir / "training_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Console summary (copy/paste to client)
    print("\n=== Lodging price model (holdout) ===")
    print(f"Rows used: {report['dataset_rows_used']:,}")
    print(f"MAE : {metrics.mae:,.2f}")
    print(f"RMSE: {metrics.rmse:,.2f}")
    print(f"R²  : {metrics.r2:,.4f}")
    print(f"MAPE: {metrics.mape:,.2f}%")
    print("\n=== Accuracy-like (client-friendly) ===")
    print(f"Within ±10% : {acc_like.within_10pct:,.2f}%")
    print(f"Within ±20% : {acc_like.within_20pct:,.2f}%")
    print(f"Within ±$50 : {acc_like.within_50_abs:,.2f}%")
    print(f"Within ±$100: {acc_like.within_100_abs:,.2f}%")
    print(f"Median |error|: {acc_like.median_abs_error:,.2f}")

    print("\n=== Baseline (predict median) ===")
    print(f"Baseline MAE : {baseline_metrics.mae:,.2f}")
    print(f"Baseline RMSE: {baseline_metrics.rmse:,.2f}")
    print(f"Baseline R²  : {baseline_metrics.r2:,.4f}")
    print(f"Baseline MAPE: {baseline_metrics.mape:,.2f}%")
    print(f"Baseline within ±20%: {baseline_acc_like.within_20pct:,.2f}%")
    print(f"\nSaved model: {model_path}")
    print(f"Saved report: {report_path}")
    print(f"Saved examples: {example_path}")


if __name__ == "__main__":
    main()

