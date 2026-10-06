"""Build feature tables from the raw Kaggle CSVs and save them as parquet.

Run from the ml folder:  python prepare_data.py
"""
import time
from pathlib import Path

from features import build_features

RAW = Path("data/raw")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

for source, target in [("application_train.csv", "train_features.parquet"),
                       ("application_test.csv", "test_features.parquet")]:
    start = time.time()
    print(f"Building features from {source} ...")
    X = build_features(RAW, source)
    X.to_parquet(OUT / target)
    print(f"  saved {OUT / target}: {X.shape[0]:,} rows x {X.shape[1]} columns "
          f"in {time.time() - start:.0f}s")

train = __import__("pandas").read_parquet(OUT / "train_features.parquet")
print(f"\nDefault rate (TARGET=1): {train['TARGET'].mean():.2%}")
print("Share of missing values per feature (top 10):")
print(train.drop(columns="TARGET").isna().mean().sort_values(ascending=False).head(10).round(3).to_string())