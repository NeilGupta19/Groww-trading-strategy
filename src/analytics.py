"""
Step 16/17: Sharpe ratio, max drawdown, Calmar ratio, and equity
curve / drawdown plotting.
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings


def sharpe_ratio(daily_returns):
    daily_rf = settings.RISK_FREE_RATE_ANNUAL / settings.TRADING_DAYS_PER_YEAR
    excess = daily_returns - daily_rf
    if excess.std() == 0:
        return 0.0
    return (excess.mean() / excess.std()) * np.sqrt(settings.TRADING_DAYS_PER_YEAR)


def max_drawdown(cumulative_return_series):
    equity_curve = 1 + cumulative_return_series
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    return drawdown.min(), drawdown


def calmar_ratio(cumulative_return_series, years):
    total_return = cumulative_return_series.iloc[-1]
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
    mdd, _ = max_drawdown(cumulative_return_series)
    if mdd == 0:
        return 0.0
    return cagr / abs(mdd)


def compute_summary_stats(portfolio_df, years):
    sharpe = sharpe_ratio(portfolio_df["daily_return"])
    mdd, drawdown_series = max_drawdown(portfolio_df["cumulative_return"])
    calmar = calmar_ratio(portfolio_df["cumulative_return"], years)

    return {
        "total_return_pct": portfolio_df["cumulative_return"].iloc[-1] * 100,
        "total_pnl": portfolio_df["cumulative_pnl"].iloc[-1],
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": mdd * 100,
        "calmar_ratio": calmar,
    }, drawdown_series


def plot_equity_and_drawdown(portfolio_df, drawdown_series, out_path):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, height_ratios=[2, 1])

    ax1.plot(portfolio_df["date"], portfolio_df["cumulative_return"] * 100, linewidth=1.5)
    ax1.set_title("Calendar Spread Portfolio — Equity Curve")
    ax1.set_ylabel("Cumulative Return (%)")
    ax1.grid(alpha=0.3)

    ax2.fill_between(portfolio_df["date"], drawdown_series * 100, 0, color="crimson", alpha=0.4)
    ax2.set_title("Drawdown")
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Date")
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
