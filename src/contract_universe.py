"""
Step 6 / Step 11: Build near/far calendar-spread contract pairs for a
symbol across the whole backtest period, and reconstruct the next pair
each time the near leg rolls off (monthly).
"""

import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings


def month_range(start_date, end_date):
    periods = pd.period_range(start=start_date, end=end_date, freq="M")
    for p in periods:
        yield p.year, p.month


def get_contract_pair(groww, symbol, year, month):
    """
    Returns a dict describing the near/far contract pair active for this
    calendar month, or None if expiry data isn't available (e.g. symbol
    wasn't in F&O yet that month).
    """
    expiries_this = groww.get_expiries(
        exchange=settings.EXCHANGE, underlying_symbol=symbol, year=year, month=month
    )["expiries"]
    if not expiries_this:
        return None

    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    expiries_next = groww.get_expiries(
        exchange=settings.EXCHANGE, underlying_symbol=symbol, year=next_year, month=next_month
    )["expiries"]
    if not expiries_next:
        return None

    near_expiry = expiries_this[0]
    far_expiry = expiries_next[0]

    near_contracts = groww.get_contracts(
        exchange=settings.EXCHANGE, underlying_symbol=symbol, expiry_date=near_expiry
    )
    far_contracts = groww.get_contracts(
        exchange=settings.EXCHANGE, underlying_symbol=symbol, expiry_date=far_expiry
    )
    near_contract = near_contracts[0] if isinstance(near_contracts, list) else near_contracts
    far_contract = far_contracts[0] if isinstance(far_contracts, list) else far_contracts

    return {
        "year": year,
        "month": month,
        "near_expiry": near_expiry,
        "far_expiry": far_expiry,
        "near_groww_symbol": near_contract["groww_symbol"],
        "far_groww_symbol": far_contract["groww_symbol"],
    }


def build_contract_calendar(groww, symbol):
    """
    Returns a list of monthly contract-pair dicts covering the whole
    backtest period for one symbol. Reconstructing the pair every month is
    exactly the "roll to the next calendar pair" step — since each pair is
    only valid until the near leg's expiry.
    """
    pairs = []
    for year, month in month_range(settings.BACKTEST_START, settings.BACKTEST_END):
        pair = get_contract_pair(groww, symbol, year, month)
        if pair is not None:
            pairs.append(pair)
    return pairs
