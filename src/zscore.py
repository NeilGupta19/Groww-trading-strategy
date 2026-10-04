"""
Step 8: 60-day rolling z-score of the calendar spread.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings


def compute_zscore(spread_series, window=None):
    window = window or settings.ZSCORE_LOOKBACK_DAYS
    rolling = spread_series.rolling(window)
    mean = rolling.mean()
    std = rolling.std()
    return (spread_series - mean) / std
