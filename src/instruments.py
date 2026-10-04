"""
Step 1: Download/load the instruments master and derive the F&O stock
universe plus lookup helpers (groww_symbol, lot_size per contract).
"""

import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings


def load_instruments_master(groww, use_cache=True):
    """
    Fetch the full instruments master directly via the SDK
    (groww.get_all_instruments()) — no manual download needed. Optionally
    caches a local copy so repeated runs on the same day don't re-fetch it.

    Columns per Groww's documented schema: exchange, exchange_token,
    trading_symbol, groww_symbol, name, instrument_type, segment, series,
    isin, underlying_symbol, underlying_exchange_token, expiry_date,
    strike_price, lot_size, tick_size, freeze_quantity, is_reserved,
    buy_allowed, sell_allowed.
    """
    if use_cache and os.path.exists(settings.INSTRUMENTS_CSV_PATH):
        return pd.read_csv(settings.INSTRUMENTS_CSV_PATH)

    instruments_df = groww.get_all_instruments()
    instruments_df.to_csv(settings.INSTRUMENTS_CSV_PATH, index=False)
    return instruments_df


def get_fno_futures(instruments_df):
    return instruments_df[
        (instruments_df["segment"] == "FNO") & (instruments_df["instrument_type"] == "FUT")
    ].copy()


def get_stock_universe(instruments_df):
    """Returns the list of F&O stock underlying symbols (indices excluded)."""
    if settings.UNDERLYING_SYMBOLS is not None:
        return settings.UNDERLYING_SYMBOLS

    fno_futures = get_fno_futures(instruments_df)
    all_underlyings = fno_futures["underlying_symbol"].dropna().unique().tolist()
    return [s for s in all_underlyings if s not in settings.INDEX_UNDERLYINGS_TO_EXCLUDE]


def lookup_lot_size(fno_futures_df, groww_symbol):
    match = fno_futures_df[fno_futures_df["groww_symbol"] == groww_symbol]
    if match.empty:
        return None
    return match["lot_size"].iloc[0]
