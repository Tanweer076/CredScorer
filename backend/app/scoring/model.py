"""Load the trained model once and use it to score and explain."""
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from app.scoring.scorecard import pd_to_score

log = logging.getLogger(__name__)


class Scorer:
    def __init__(self, bundle: dict):
        self.model = bundle["model"]  # calibrated: gives the PD
        self.booster = bundle["booster"]  # raw XGBoost: gives SHAP values
        self.features: list[str] = bundle["features"]
        self.categories: dict[str, list[str]] = bundle["categories"]
        self.version: str = bundle["version"]

    @classmethod
    def load(cls, path: str) -> "Scorer | None":
        if not Path(path).exists():
            log.warning("Model file %s not found; scoring endpoints will return 503", path)
            return None
        scorer = cls(joblib.load(path))
        log.info("Loaded model version %s from %s", scorer.version, path)
        return scorer

    def to_frame(self, row: dict) -> pd.DataFrame:
        data = {}
        for name in self.features:
            value = row.get(name)
            if name in self.categories:
                data[name] = pd.Categorical([value], categories=self.categories[name])
            else:
                data[name] = [np.nan if value is None else float(value)]
        return pd.DataFrame(data)

    def score(self, row: dict) -> dict:
        X = self.to_frame(row)
        pd_value = float(self.model.predict_proba(X)[0, 1])
        # TreeSHAP values straight from XGBoost (same numbers as the shap library),
        # limited to the trees the model actually uses after early stopping.
        dmatrix = xgb.DMatrix(X, enable_categorical=True)
        contribs = self.booster.get_booster().predict(
            dmatrix, pred_contribs=True, iteration_range=(0, self.booster.best_iteration + 1))[0]
        shap_values = dict(zip(self.features, contribs[:-1].tolist()))  # last column is the bias
        return {"pd": pd_value, "score": pd_to_score(pd_value), "shap": shap_values}