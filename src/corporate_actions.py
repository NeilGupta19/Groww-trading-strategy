"""
Step 3/4/5: Download corporate actions (dividends, stock splits/bonuses),
build forward-adjustment factors from them, and apply those factors to
raw futures price history.

Groww's API does not expose a corporate-actions endpoint (checked against
their docs), so this pulls from NSE's own corporate-actions feed instead —
the same external-data pattern your main NSE system already uses for
bhavcopies (cookie-based session handling, since NSE's site requires a
browser-like session before its API responds).

--- Forward-adjustment convention used here ---
This applies the FORWARD adjustment method (as opposed to back-adjustment):
historical prices BEFORE a corporate action are left completely untouched
(raw, as originally recorded). Prices ON AND AFTER the action's ex-date are
scaled by a cumulative factor so the series stays continuous with what came
immediately before it. This means the adjustment factor grows over time as
more actions occur, and old data never needs to be rewritten when a new
action happens — useful for an append-only pipeline. This is the opposite
of "back-adjustment" (which instead rescales the past to match today's
price level) — if your existing NSE data pipeline uses back-adjustment,
make sure you don't mix the two conventions in the same analysis.
"""

import sys
import os
import time
import requests
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings

NSE_BASE = "https://www.nseindia.com"
NSE_CORP_ACTIONS_ENDPOINT = "/api/corporates-corporateActions"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _get_nse_session():
    session = requests.Session()
    session.headers.update(_HEADERS)
    session.get(NSE_BASE, timeout=10)  # picks up cookies needed for the API to respond
    return session


def fetch_corporate_actions(symbol, from_date, to_date, session=None):
    """
    Fetch raw corporate actions for one symbol between from_date and to_date
    (format: DD-MM-YYYY, per NSE's convention). Returns a DataFrame with
    at least: symbol, ex_date, subject (free-text description of the action).

    NOTE: NSE's response schema shifts occasionally — print one raw response
    and adjust the column mapping below if this breaks.
    """
    session = session or _get_nse_session()
    params = {
        "index": "equities",
        "symbol": symbol,
        "from_date": from_date,
        "to_date": to_date,
    }
    resp = session.get(NSE_BASE + NSE_CORP_ACTIONS_ENDPOINT, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data)
    time.sleep(0.5)  # avoid hammering NSE's site
    return df


def _parse_split_ratio(subject_text):
    """
    Extracts a (new, old) share ratio from NSE's free-text 'subject' field
    for split/bonus actions, e.g. "Face Value Split (Sub-Division) - From
    Rs 10/- Per Share To Rs 2/-" or "Bonus 1:1". Returns None if not parseable
    — inspect unmatched rows manually, since NSE's phrasing isn't fully
    standardized.
    """
    import re
    text = subject_text.lower()

    bonus_match = re.search(r"bonus\s*(\d+)\s*:\s*(\d+)", text)
    if bonus_match:
        new_shares_per_old = int(bonus_match.group(1)) + int(bonus_match.group(2))
        old_shares = int(bonus_match.group(2))
        return new_shares_per_old, old_shares  # e.g. bonus 1:1 -> 2 new for 1 old

    split_match = re.search(r"rs\.?\s*(\d+(?:\.\d+)?)\s*/?-?\s*.*to\s*rs\.?\s*(\d+(?:\.\d+)?)", text)
    if split_match:
        old_face_value = float(split_match.group(1))
        new_face_value = float(split_match.group(2))
        if new_face_value > 0:
            return old_face_value, new_face_value  # e.g. 10 -> 2 means 5 new shares per old

    return None


def _parse_dividend_amount(subject_text):
    import re
    match = re.search(r"dividend.*?rs\.?\s*(\d+(?:\.\d+)?)", subject_text.lower())
    if match:
        return float(match.group(1))
    return None


def build_action_factors(actions_df, price_df):
    """
    Given raw corporate actions (with 'ex_date' and 'subject') and the raw
    price series for the same symbol (needs 'date' and 'close'), compute a
    per-action multiplicative factor:
      - Split/bonus: factor = new_shares / old_shares
      - Dividend: factor = prev_close / (prev_close - dividend_amount)
    Returns a DataFrame: ex_date, action_type, factor
    """
    price_df = price_df.sort_values("date").reset_index(drop=True)
    rows = []

    for _, action in actions_df.iterrows():
        ex_date = pd.to_datetime(action["ex_date"])
        subject = str(action.get("subject", ""))

        split_ratio = _parse_split_ratio(subject)
        if split_ratio:
            new_shares, old_shares = split_ratio
            factor = new_shares / old_shares
            rows.append({"ex_date": ex_date, "action_type": "SPLIT_OR_BONUS", "factor": factor})
            continue

        dividend = _parse_dividend_amount(subject)
        if dividend:
            prior_rows = price_df[price_df["date"] < ex_date]
            if prior_rows.empty:
                continue
            prev_close = prior_rows.iloc[-1]["close"]
            if prev_close <= dividend:
                continue  # avoid divide-by-zero/negative on bad data
            factor = prev_close / (prev_close - dividend)
            rows.append({"ex_date": ex_date, "action_type": "DIVIDEND", "factor": factor})

    return pd.DataFrame(rows).sort_values("ex_date").reset_index(drop=True)


def apply_forward_adjustment(price_df, factors_df):
    """
    Applies the forward-adjustment factors to a raw OHLC price DataFrame
    (needs a 'date' column and open/high/low/close columns). Returns a copy
    with adjusted price columns added (suffix '_adj').
    """
    df = price_df.copy().sort_values("date").reset_index(drop=True)

    cumulative_factor = pd.Series(1.0, index=df.index)
    for _, action in factors_df.iterrows():
        mask = df["date"] >= action["ex_date"]
        cumulative_factor.loc[mask] *= action["factor"]

    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[f"{col}_adj"] = df[col] * cumulative_factor

    df["adjustment_factor"] = cumulative_factor
    return df


def get_and_save_actions(symbol):
    os.makedirs(settings.CORPORATE_ACTIONS_DIR, exist_ok=True)
    from_date = pd.Timestamp(settings.BACKTEST_START).strftime("%d-%m-%Y")
    to_date = pd.Timestamp(settings.BACKTEST_END).strftime("%d-%m-%Y")

    actions = fetch_corporate_actions(symbol, from_date, to_date)
    out_path = f"{settings.CORPORATE_ACTIONS_DIR}/{symbol}_actions.csv"
    actions.to_csv(out_path, index=False)
    return actions
