"""
Builds the trading calendar for the backtest period. Rather than hardcoding
NSE holidays (which change year to year), we derive the calendar from the
actual traded dates present in the fetched data — any date the exchange
had no session simply won't appear in the candle data.
"""

import pandas as pd


def build_calendar_from_data(*date_series):
    """
    Given one or more pandas Series/Index of dates, return the sorted union
    as the effective trading calendar for that data.
    """
    all_dates = pd.concat([pd.Series(pd.to_datetime(s)) for s in date_series])
    return pd.DatetimeIndex(sorted(all_dates.unique()))


def trim_to_backtest_period(dates, start, end):
    dates = pd.DatetimeIndex(dates)
    return dates[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
