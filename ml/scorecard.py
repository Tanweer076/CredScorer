"""Convert a probability of default (PD) into a 0-1000 credit score.

Standard bank scorecard scaling ("points to double the odds"):
- BASE_SCORE points at BASE_ODDS good:bad odds (600 points at 50:1)
- every PDO extra points doubles the odds of being good (+40 points = twice as safe)
"""
import numpy as np

BASE_SCORE = 600
BASE_ODDS = 50
PDO = 40
# Isotonic calibration can output PD = 0 for the safest group ("no defaults seen there"),
# which is not the same as zero risk. Floor PD at 0.1% so the best score is about 773.
MIN_PD, MAX_PD = 0.001, 0.999

FACTOR = PDO / np.log(2)
OFFSET = BASE_SCORE - FACTOR * np.log(BASE_ODDS)


def pd_to_score(pd_value):
    """Works on a single number or a numpy array."""
    p = np.clip(pd_value, MIN_PD, MAX_PD)  # also avoids dividing by zero at PD = 0 or 1
    odds = (1 - p) / p
    score = np.clip(OFFSET + FACTOR * np.log(odds), 0, 1000)
    return np.rint(score).astype(int) if np.ndim(score) else int(round(float(score)))


def score_to_pd(score):
    """Inverse, handy for explaining thresholds: what PD does a score of 700 mean?"""
    odds = np.exp((np.asarray(score, dtype=float) - OFFSET) / FACTOR)
    return 1 / (1 + odds)