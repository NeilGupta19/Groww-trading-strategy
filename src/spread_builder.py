"""
Step 6/7: Load adjusted near/far leg data for a symbol, align on date, and
compute the calendar spread (using adjusted close prices).
"""

import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings


def load_adjusted_legs(symbol):
    near = pd.read_csv(f"{settings.PROCESSED_DIR}/{symbol}_near_adj.csv", parse_dates=["date"])
    far = pd.read_csv(f"{settings.PROCESSED_DIR}/{symbol}_far_adj.csv", parse_dates=["date"])
    merged = pd.merge(
        near, far, on="date", suffixes=("_near", "_far"), how="inner"
    ).sort_values("date").reset_index(drop=True)
    return merged


def compute_spread(df):
    """Spread computed on adjusted close prices, per the forward-adjustment convention."""
    df["spread"] = df["close_adj_far"] - df["close_adj_near"]
    df["spread_pct"] = df["spread"] / df["close_adj_near"]
    return df
