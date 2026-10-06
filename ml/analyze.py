"""Score distribution, decision thresholds and SHAP explanations for the trained model.

Run from the ml folder after train.py:  python analyze.py
"""
import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import train_test_split

from scorecard import pd_to_score, score_to_pd

ARTIFACTS = Path("artifacts")
SEED = 42
TARGET_APPROVE_DEFAULT_RATE = 0.03  # auto-approved group may have at most 3% defaulters
TARGET_REJECT_DEFAULT_RATE = 0.20   # auto-rejected group must have at least 20% defaulters


def test_split(X, y):
    """Recreate exactly the same test set as train.py (same proportions and seed)."""
    _, X_rest, _, y_rest = train_test_split(X, y, test_size=0.35, stratify=y, random_state=SEED)
    _, X_rest, _, y_rest = train_test_split(X_rest, y_rest, test_size=25 / 35, stratify=y_rest, random_state=SEED)
    _, X_test, _, y_test = train_test_split(X_rest, y_rest, test_size=0.6, stratify=y_rest, random_state=SEED)
    return X_test, y_test


def score_bands(scores, y) -> pd.DataFrame:
    edges = [0, 350, 400, 450, 500, 550, 600, 650, 700, 750, 1001]
    labels = [f"{a}-{b - 1}" for a, b in zip(edges[:-1], edges[1:])]
    band = pd.cut(scores, bins=edges, labels=labels, right=False)
    table = pd.DataFrame({"band": band, "default": y.to_numpy()}).groupby("band", observed=False)["default"]
    out = pd.DataFrame({"applicants": table.size(), "default_rate": table.mean()})
    out["share"] = out["applicants"] / out["applicants"].sum()
    return out[["applicants", "share", "default_rate"]]


def pick_thresholds(scores, y) -> dict:
    """Approve as many people as possible while keeping the approved group's default rate
    under TARGET_APPROVE_DEFAULT_RATE; reject only where the rejected group's default rate
    is at least TARGET_REJECT_DEFAULT_RATE. Everyone in between goes to manual review."""
    y = y.to_numpy()
    candidates = np.arange(300, 901, 5)
    approve_min = next((int(t) for t in candidates
                        if (scores >= t).any() and y[scores >= t].mean() <= TARGET_APPROVE_DEFAULT_RATE), 900)
    reject_max = next((int(t) for t in candidates[::-1]
                       if (scores < t).any() and y[scores < t].mean() >= TARGET_REJECT_DEFAULT_RATE), 300)
    reject_max = min(reject_max, approve_min)
    approved, rejected = scores >= approve_min, scores < reject_max
    review = ~approved & ~rejected
    rate = lambda mask: float(y[mask].mean()) if mask.any() else None  # noqa: E731
    return {
        "approve_min_score": approve_min,
        "reject_max_score": reject_max,
        "approve_share": float(approved.mean()), "approve_default_rate": rate(approved),
        "review_share": float(review.mean()), "review_default_rate": rate(review),
        "reject_share": float(rejected.mean()), "reject_default_rate": rate(rejected),
    }


def main() -> None:
    bundle = joblib.load(ARTIFACTS / "model.joblib")
    features = bundle["features"]
    data = pd.read_parquet("data/processed/train_features.parquet")
    X_test, y_test = test_split(data[features], data["TARGET"])

    pd_test = bundle["model"].predict_proba(X_test)[:, 1]
    scores = pd_to_score(pd_test)

    print("Score distribution on the test set")
    print(score_bands(scores, y_test).to_string(formatters={"share": "{:.1%}".format,
                                                           "default_rate": "{:.1%}".format}))
    print(f"\nMedian score {np.median(scores):.0f} | 10th pct {np.percentile(scores, 10):.0f} "
          f"| 90th pct {np.percentile(scores, 90):.0f}")

    t = pick_thresholds(scores, y_test)
    print(f"\nSuggested thresholds (targets: approved <= {TARGET_APPROVE_DEFAULT_RATE:.0%} defaults, "
          f"rejected >= {TARGET_REJECT_DEFAULT_RATE:.0%} defaults)")
    print(f"  approve if score >= {t['approve_min_score']}  (PD about {score_to_pd(t['approve_min_score']):.1%})"
          f"  -> {t['approve_share']:.1%} of applicants, default rate {t['approve_default_rate'] or 0:.1%}")
    print(f"  reject  if score <  {t['reject_max_score']}  (PD about {score_to_pd(t['reject_max_score']):.1%})"
          f"  -> {t['reject_share']:.1%} of applicants, default rate {t['reject_default_rate'] or 0:.1%}")
    if t["reject_share"] == 0:
        print("  (no score range reaches the reject target, so nobody is auto-rejected; they go to review)")
    print(f"  manual review in between -> {t['review_share']:.1%} of applicants, "
          f"default rate {t['review_default_rate'] or 0:.1%}")
    (ARTIFACTS / "thresholds.json").write_text(json.dumps(t, indent=2))

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(scores[y_test.to_numpy() == 0], bins=60, alpha=0.6, density=True, label="repaid")
    ax.hist(scores[y_test.to_numpy() == 1], bins=60, alpha=0.6, density=True, label="defaulted")
    for x, name in [(t["reject_max_score"], "reject below"), (t["approve_min_score"], "approve from")]:
        ax.axvline(x, color="black", linestyle="--")
        ax.text(x, ax.get_ylim()[1] * 0.9, f" {name} {x}", fontsize=8)
    ax.set_xlabel("credit score (0-1000)")
    ax.set_title("Score distribution on test set")
    ax.legend()
    fig.savefig(ARTIFACTS / "score_distribution.png", dpi=120, bbox_inches="tight")

    # SHAP: explain the uncalibrated booster. Calibration only rescales PD monotonically,
    # so which factors push risk up or down stays the same.
    sample = X_test.sample(n=min(2000, len(X_test)), random_state=SEED)
    explanation = shap.TreeExplainer(bundle["booster"])(sample)
    plt.figure()
    shap.plots.bar(explanation, max_display=15, show=False)
    plt.savefig(ARTIFACTS / "shap_importance.png", dpi=120, bbox_inches="tight")
    plt.figure()
    shap.plots.beeswarm(explanation, max_display=15, show=False)
    plt.savefig(ARTIFACTS / "shap_beeswarm.png", dpi=120, bbox_inches="tight")

    print("\nTop 10 features by mean |SHAP| (how much each moves the risk on average):")
    importance = pd.Series(np.abs(explanation.values).mean(axis=0), index=features).sort_values(ascending=False)
    print(importance.head(10).round(3).to_string())

    print("\nExample explanations (positive = raises risk, negative = lowers risk):")
    sample_pd = bundle["model"].predict_proba(sample)[:, 1]
    for i in [int(np.argmin(sample_pd)), int(np.argmax(sample_pd))]:
        contrib = pd.Series(explanation.values[i], index=features).sort_values(key=abs, ascending=False).head(3)
        print(f"  applicant {sample.index[i]}: PD {sample_pd[i]:.1%}, score {pd_to_score(sample_pd[i])}")
        for name, value in contrib.items():
            raw = sample.iloc[i][name]
            shown = f"{raw:.3g}" if isinstance(raw, (int, float, np.number)) else str(raw)
            print(f"     {name:<22} = {shown:<14} SHAP {value:+.3f}")
    print("\nSaved thresholds.json, score_distribution.png, shap_importance.png, shap_beeswarm.png in artifacts/")


if __name__ == "__main__":
    main()