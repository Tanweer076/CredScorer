"""Train the CredScorer probability-of-default (PD) model.

Steps: split data -> tune XGBoost with Optuna -> train final model ->
calibrate probabilities -> evaluate on untouched test data -> save + log to MLflow.

Run from the ml folder:  python train.py --trials 30
"""
import argparse
import json
import time
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")  # save plots to files, no window
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV, CalibrationDisplay
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split

from features import CATEGORIES, FEATURES

ARTIFACTS = Path("artifacts")
SEED = 42


def ks_statistic(y_true, p) -> float:
    """Max distance between the score distributions of good and bad borrowers."""
    fpr, tpr, _ = roc_curve(y_true, p)
    return float(np.max(tpr - fpr))


def evaluate(y_true, p) -> dict:
    return {
        "roc_auc": roc_auc_score(y_true, p),
        "pr_auc": average_precision_score(y_true, p),
        "ks": ks_statistic(y_true, p),
        "brier": brier_score_loss(y_true, p),
        "mean_predicted_pd": float(np.mean(p)),
        "actual_default_rate": float(np.mean(y_true)),
    }


def base_params(scale_pos_weight: float) -> dict:
    return dict(
        n_estimators=3000,              # upper limit; early stopping picks the real number
        early_stopping_rounds=100,
        eval_metric="auc",
        tree_method="hist",
        enable_categorical=True,         # uses our pandas category columns directly
        scale_pos_weight=scale_pos_weight,  # class weight: defaulters count ~11x more
        random_state=SEED,
        n_jobs=-1,
    )


def main(n_trials: int) -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    data = pd.read_parquet("data/processed/train_features.parquet")
    X, y = data[FEATURES], data["TARGET"]

    # 65% train / 10% validation (tuning + early stopping) / 10% calibration / 15% test.
    # Each part has one job, so no step is graded on data it has already seen.
    X_train, X_rest, y_train, y_rest = train_test_split(X, y, test_size=0.35, stratify=y, random_state=SEED)
    X_valid, X_rest, y_valid, y_rest = train_test_split(X_rest, y_rest, test_size=25 / 35, stratify=y_rest, random_state=SEED)
    X_cal, X_test, y_cal, y_test = train_test_split(X_rest, y_rest, test_size=0.6, stratify=y_rest, random_state=SEED)
    print(f"train {len(X_train):,} | valid {len(X_valid):,} | calibration {len(X_cal):,} | test {len(X_test):,}")

    spw = float((y_train == 0).sum() / (y_train == 1).sum())
    print(f"scale_pos_weight (non-defaulters per defaulter): {spw:.1f}")

    def objective(trial: optuna.Trial) -> float:
        params = base_params(spw) | dict(
            learning_rate=trial.suggest_float("learning_rate", 0.02, 0.2, log=True),
            max_depth=trial.suggest_int("max_depth", 3, 8),
            min_child_weight=trial.suggest_float("min_child_weight", 1, 100, log=True),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
            reg_lambda=trial.suggest_float("reg_lambda", 1e-3, 10, log=True),
            reg_alpha=trial.suggest_float("reg_alpha", 1e-3, 10, log=True),
        )
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
        return roc_auc_score(y_valid, model.predict_proba(X_valid)[:, 1])

    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("credscorer-pd")
    with mlflow.start_run() as run:
        start = time.time()
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        print(f"Best validation ROC-AUC: {study.best_value:.4f} after {n_trials} trials ({time.time() - start:.0f}s)")

        # Final model with the best settings.
        model = xgb.XGBClassifier(**(base_params(spw) | study.best_params))
        model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)

        # Class weights make raw probabilities too high. Isotonic calibration on separate
        # data maps them back so "PD = 10%" means about 10% of such people default.
        calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="isotonic")
        calibrated.fit(X_cal, y_cal)

        raw_test = model.predict_proba(X_test)[:, 1]
        cal_test = calibrated.predict_proba(X_test)[:, 1]
        raw_metrics = evaluate(y_test, raw_test)
        metrics = evaluate(y_test, cal_test)

        print("\nTest set (never used for training, tuning or calibration):")
        print(f"{'metric':<22}{'uncalibrated':>14}{'calibrated':>14}")
        for k in metrics:
            print(f"{k:<22}{raw_metrics[k]:>14.4f}{metrics[k]:>14.4f}")

        # Reliability plot: points on the diagonal = well calibrated.
        fig, ax = plt.subplots(figsize=(6, 6))
        CalibrationDisplay.from_predictions(y_test, raw_test, n_bins=10, strategy="quantile", name="uncalibrated", ax=ax)
        CalibrationDisplay.from_predictions(y_test, cal_test, n_bins=10, strategy="quantile", name="calibrated", ax=ax)
        ax.set_title("Calibration on test set")
        fig.savefig(ARTIFACTS / "calibration.png", dpi=120, bbox_inches="tight")

        version = run.info.run_id[:8]
        bundle = {
            "model": calibrated,          # use this for PD
            "booster": model,             # use this for SHAP explanations
            "features": FEATURES,
            "categories": CATEGORIES,
            "version": version,
            "metrics": metrics,
            "best_iteration": int(model.best_iteration),
        }
        joblib.dump(bundle, ARTIFACTS / "model.joblib")
        (ARTIFACTS / "feature_list.json").write_text(json.dumps(FEATURES, indent=2))
        (ARTIFACTS / "metrics.json").write_text(json.dumps({"version": version, **metrics}, indent=2))

        mlflow.log_params(study.best_params | {"n_trials": n_trials, "scale_pos_weight": round(spw, 2),
                                               "best_iteration": int(model.best_iteration),
                                               "n_features": len(FEATURES)})
        mlflow.log_metrics({f"test_{k}": v for k, v in metrics.items()}
                           | {f"test_uncalibrated_{k}": v for k, v in raw_metrics.items()}
                           | {"valid_roc_auc": study.best_value})
        for name in ("model.joblib", "metrics.json", "calibration.png"):
            mlflow.log_artifact(str(ARTIFACTS / name))
        print(f"\nSaved artifacts/model.joblib (version {version}) and logged run to MLflow.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=30, help="number of Optuna trials")
    main(parser.parse_args().trials)