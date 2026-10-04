"""
Step 2 & 5: Download near/far futures OHLCV history for a symbol across
the backtest period, then apply the forward-adjustment factors from
corporate_actions.py before saving processed data.
"""

import sys
import os
import time
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings
from src import contract_universe, corporate_actions


def fetch_daily_candles(groww, groww_symbol, start_time, end_time):
    response = groww.get_historical_candles(
        exchange=settings.EXCHANGE,
        segment=groww.SEGMENT_FNO,
        groww_symbol=groww_symbol,
        start_time=start_time,
        end_time=end_time,
        candle_interval=groww.CANDLE_INTERVAL_DAY,  # verify exact constant name in your SDK version
    )
    candles = response.get("candles", response)  # shape may vary — inspect once and adjust
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df[["date", "open", "high", "low", "close", "volume"]]


def fetch_leg_history(groww, symbol, contract_pairs, leg):
    """leg = 'near' or 'far'. Fetches and stitches raw candle data for one leg."""
    frames = []
    for pair in contract_pairs:
        groww_symbol = pair[f"{leg}_groww_symbol"]
        month_start = pd.Timestamp(year=pair["year"], month=pair["month"], day=1)
        month_end = month_start + pd.offsets.MonthEnd(0)

        df = fetch_daily_candles(
            groww, groww_symbol,
            month_start.strftime("%Y-%m-%d 00:00:00"),
            month_end.strftime("%Y-%m-%d 23:59:59"),
        )
        df["contract_expiry"] = pair[f"{leg}_expiry"]
        frames.append(df)
        time.sleep(0.3)

    if not frames:
        return None
    return pd.concat(frames).sort_values("date").drop_duplicates("date").reset_index(drop=True)


def build_symbol_history(groww, symbol):
    """
    Full step 2+5 pipeline for one symbol: build contract pairs, fetch raw
    near/far legs, save raw, fetch+apply corporate action adjustment, save
    processed.
    """
    os.makedirs(settings.RAW_DIR, exist_ok=True)
    os.makedirs(settings.PROCESSED_DIR, exist_ok=True)

    pairs = contract_universe.build_contract_calendar(groww, symbol)
    if not pairs:
        return None, None

    near_raw = fetch_leg_history(groww, symbol, pairs, "near")
    far_raw = fetch_leg_history(groww, symbol, pairs, "far")
    if near_raw is None or far_raw is None:
        return None, None

    near_raw.to_csv(f"{settings.RAW_DIR}/{symbol}_near_raw.csv", index=False)
    far_raw.to_csv(f"{settings.RAW_DIR}/{symbol}_far_raw.csv", index=False)

    actions = corporate_actions.get_and_save_actions(symbol)
    if actions is not None and not actions.empty:
        factors = corporate_actions.build_action_factors(actions, near_raw)
        near_adj = corporate_actions.apply_forward_adjustment(near_raw, factors)
        far_adj = corporate_actions.apply_forward_adjustment(far_raw, factors)
    else:
        near_adj, far_adj = near_raw.copy(), far_raw.copy()
        for col in ["open", "high", "low", "close"]:
            near_adj[f"{col}_adj"] = near_adj[col]
            far_adj[f"{col}_adj"] = far_adj[col]
        near_adj["adjustment_factor"] = 1.0
        far_adj["adjustment_factor"] = 1.0

    near_adj.to_csv(f"{settings.PROCESSED_DIR}/{symbol}_near_adj.csv", index=False)
    far_adj.to_csv(f"{settings.PROCESSED_DIR}/{symbol}_far_adj.csv", index=False)

    return near_adj, far_adj
