"""
Step 12/13/14: Daily MTM P&L, gross exposure, and the return series —
using the symbol's actual lot size for each contract month and net of
transaction costs.
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings
from src import costs


def attach_lot_size(df, fno_futures_df, symbol_lookup_fn):
    df["lot_size"] = df.apply(
        lambda r: symbol_lookup_fn(fno_futures_df, r["contract_expiry_near"]), axis=1
    )
    df["lot_size"] = df["lot_size"].ffill().bfill()
    return df


def compute_pnl(df):
    lots = settings.NUM_LOTS_PER_LEG

    df["spread_change"] = df["spread"].diff().fillna(0)
    df["gross_daily_pnl"] = (
        df["position"].shift(1).fillna(0) * df["spread_change"] * df["lot_size"] * lots
    )

    df = costs.apply_transaction_costs(df)
    df["daily_pnl"] = df["gross_daily_pnl"] - df["transaction_cost"]
    df["cumulative_pnl"] = df["daily_pnl"].cumsum()

    df["notional_near"] = df["close_adj_near"] * df["lot_size"] * lots
    df["notional_far"] = df["close_adj_far"] * df["lot_size"] * lots
    df["gross_exposure"] = df["notional_near"] + df["notional_far"]

    df["daily_return"] = df["daily_pnl"] / df["gross_exposure"].replace(0, np.nan)
    df["daily_return"] = df["daily_return"].fillna(0)
    df["cumulative_return"] = (1 + df["daily_return"]).cumprod() - 1

    return df
