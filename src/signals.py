"""
Step 9/10: Generate entry/exit signals from the spread z-score, with a
forced exit near the near-leg's expiry (roll buffer) to avoid expiry-day
liquidity/pin risk.
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings
from src.zscore import compute_zscore


def generate_signals(df):
    df["zscore"] = compute_zscore(df["spread_pct"])

    position = np.zeros(len(df))
    current = 0

    for i in range(len(df)):
        z = df["zscore"].iloc[i]
        if pd.isna(z):
            position[i] = current
            continue

        days_to_near_expiry = (
            pd.to_datetime(df["contract_expiry_near"].iloc[i]) - df["date"].iloc[i]
        ).days
        force_exit = days_to_near_expiry <= settings.ROLL_BUFFER_DAYS

        if current == 0:
            if z >= settings.ENTRY_ZSCORE:
                current = -1  # short the spread: sell far, buy near
            elif z <= -settings.ENTRY_ZSCORE:
                current = 1   # long the spread: buy far, sell near
        else:
            if force_exit or abs(z) <= settings.EXIT_ZSCORE:
                current = 0

        position[i] = current

    df["position"] = position
    return df
