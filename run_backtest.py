"""
Orchestrates the full 17-step pipeline end to end.
"""

import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(__file__))
from config import settings
from src import groww_client, instruments, futures_history, spread_builder, signals, pnl, analytics


def run_symbol(groww, symbol, fno_futures_df):
    print(f"\n=== {symbol} ===")

    # Steps 2-5: download + adjust futures history
    near_adj, far_adj = futures_history.build_symbol_history(groww, symbol)
    if near_adj is None:
        print(f"  No data for {symbol}, skipping.")
        return None

    # Steps 6-7: build pairs + spread
    df = spread_builder.load_adjusted_legs(symbol)
    if len(df) < settings.ZSCORE_LOOKBACK_DAYS + 5:
        print(f"  Not enough history for {symbol}, skipping.")
        return None
    df = spread_builder.compute_spread(df)

    # Steps 8-11: z-score, signals, forced expiry exit (roll handled via monthly contract pairs)
    df = signals.generate_signals(df)

    # Lot size lookup (per contract, from instruments master)
    df["lot_size"] = df["contract_expiry_near"].apply(
        lambda exp: _lookup_lot_size_for_expiry(fno_futures_df, symbol, exp)
    )
    df["lot_size"] = df["lot_size"].ffill().bfill()

    # Steps 12-15: P&L, exposure, returns, transaction costs
    df = pnl.compute_pnl(df)

    df["symbol"] = symbol
    os.makedirs(settings.RESULTS_DIR, exist_ok=True)
    df.to_csv(f"{settings.RESULTS_DIR}/{symbol}_results.csv", index=False)

    print(f"  P&L: Rs {df['cumulative_pnl'].iloc[-1]:,.0f} | "
          f"Return: {df['cumulative_return'].iloc[-1] * 100:.2f}% | "
          f"Days in position: {(df['position'] != 0).sum()}")
    return df


def _lookup_lot_size_for_expiry(fno_futures_df, symbol, expiry_date):
    match = fno_futures_df[
        (fno_futures_df["underlying_symbol"] == symbol)
        & (fno_futures_df["expiry_date"] == expiry_date)
    ]
    if match.empty:
        return None
    return match["lot_size"].iloc[0]


def build_portfolio(all_results):
    combined = pd.concat(all_results, ignore_index=True)
    portfolio = (
        combined.groupby("date")
        .agg(daily_pnl=("daily_pnl", "sum"), gross_exposure=("gross_exposure", "sum"))
        .reset_index()
        .sort_values("date")
    )
    portfolio["cumulative_pnl"] = portfolio["daily_pnl"].cumsum()
    portfolio["daily_return"] = portfolio["daily_pnl"] / portfolio["gross_exposure"].replace(0, float("nan"))
    portfolio["daily_return"] = portfolio["daily_return"].fillna(0)
    portfolio["cumulative_return"] = (1 + portfolio["daily_return"]).cumprod() - 1
    return portfolio


def main():
    groww = groww_client.get_client()

    instruments_df = instruments.load_instruments_master(groww)
    fno_futures_df = instruments.get_fno_futures(instruments_df)
    symbols = instruments.get_stock_universe(instruments_df)
    print(f"Universe: {len(symbols)} F&O stocks")

    all_results = []
    for symbol in symbols:
        df = run_symbol(groww, symbol, fno_futures_df)
        if df is not None:
            all_results.append(df)

    if not all_results:
        print("No results — check data availability / credentials.")
        return

    # Step 16-17: portfolio-level analytics + plots
    portfolio = build_portfolio(all_results)
    os.makedirs(settings.RESULTS_DIR, exist_ok=True)
    portfolio.to_csv(f"{settings.RESULTS_DIR}/portfolio_results.csv", index=False)

    years = (pd.Timestamp(settings.BACKTEST_END) - pd.Timestamp(settings.BACKTEST_START)).days / 365.25
    stats, drawdown_series = analytics.compute_summary_stats(portfolio, years)

    print("\n--- Portfolio Summary ---")
    for k, v in stats.items():
        print(f"{k}: {v:,.2f}" if isinstance(v, (int, float)) else f"{k}: {v}")

    analytics.plot_equity_and_drawdown(
        portfolio, drawdown_series, f"{settings.RESULTS_DIR}/equity_curve_drawdown.png"
    )
    print(f"\nSaved equity curve + drawdown plot -> {settings.RESULTS_DIR}/equity_curve_drawdown.png")


if __name__ == "__main__":
    main()
