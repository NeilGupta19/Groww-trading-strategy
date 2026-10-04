# F&O Stock Calendar Spread Backtest — Full Pipeline

Backtests calendar spreads (near-month vs next-month futures) across F&O
stocks, with corporate-action-adjusted prices, transaction costs, and
Sharpe/drawdown/Calmar analytics. Jan 2023 – Dec 2024.

## Pipeline (matches `run_backtest.py` step by step)
1. **Instruments master** — `src/instruments.py` loads the Groww instruments
   CSV and derives the F&O stock universe.
2. **Futures OHLCV history** — `src/futures_history.py` + `src/contract_universe.py`
   fetch near/far leg daily candles for every month, for every stock.
3. **Corporate actions** — `src/corporate_actions.py` pulls dividends/splits
   from NSE's corporate-actions feed (Groww's API doesn't expose this data).
4. **Forward-adjustment factors** — same file: builds a per-action
   multiplicative factor (split ratio, or dividend-implied factor).
5. **Adjust futures prices** — same file: applies those factors *forward*
   from each action's ex-date (raw history before the action is left
   untouched; everything after is scaled to stay continuous with it —
   see the docstring in `corporate_actions.py` for the full convention,
   since this is the *opposite* direction from typical "back-adjustment").
6. **Near/Far pairs** — `src/contract_universe.py` builds the monthly
   contract-pair calendar.
7. **Spread** — `src/spread_builder.py`: Far − Near, on adjusted close.
8. **60-day rolling z-score** — `src/zscore.py`.
9. **Entry/exit signals** — `src/signals.py`.
10. **Forced exit near expiry** — same file, `ROLL_BUFFER_DAYS` before near-leg expiry.
11. **Reconstruct next pair** — handled automatically by the monthly
    contract-pair loop in `contract_universe.py`.
12. **Daily MTM P&L** — `src/pnl.py`.
13. **Gross exposure** — same file.
14. **Return series** — same file.
15. **Transaction costs** — `src/costs.py`, netted into daily P&L in `pnl.py`.
16. **Sharpe / MDD / Calmar** — `src/analytics.py`.
17. **Equity curve + drawdown plot** — same file.

## Setup
```bash
pip install growwapi pyotp pandas numpy matplotlib requests
```
1. Fill in `config/credentials.py` with your TOTP API key/secret.
2. Nothing to download manually — `run_backtest.py` calls
   `groww.get_all_instruments()` on its own and caches the result to
   `instruments.csv` in the project root (path set in `config/settings.py`).
   Delete that cached file if you want a fresh pull on a later run.
3. For a first test run, set `UNDERLYING_SYMBOLS` in `config/settings.py`
   to a handful of liquid stocks instead of the full auto-discovered
   universe — the full run is API-call-heavy (24 months × 2 legs × every
   F&O stock) and will take a long time / risk rate limits otherwise.

## Run
```bash
python3 run_backtest.py
```

## Things to verify before trusting the output
I don't have network access to groww.in or nseindia.com from this
environment, so none of this has been run against live data — these are
the specific places to check on your first real run:

- **`groww.CANDLE_INTERVAL_DAY`** and the exact shape of
  `get_historical_candles()` / `get_contracts()` responses — print one
  real response each and adjust `futures_history.py` / `contract_universe.py`
  if they differ from what's assumed.
- **NSE corporate-actions response schema** — `corporate_actions.py`
  assumes a `subject` free-text field and an `ex_date` field; NSE's exact
  JSON keys should be confirmed against a live response, and the regex
  parsing in `_parse_split_ratio` / `_parse_dividend_amount` is heuristic —
  spot-check parsed factors against a few known real events (e.g. a stock
  you know underwent a recent split) before trusting the adjusted series.
- **Instruments CSV column names** — confirm `segment`, `instrument_type`,
  `underlying_symbol`, `groww_symbol`, `lot_size`, `expiry_date` match your
  downloaded file exactly.
- **Transaction cost rates in `config/settings.py`** — STT, exchange
  transaction charges, and stamp duty rates are periodically revised by
  SEBI/NSE; the values here are approximate starting points, not
  guaranteed current.
- **Adjustment direction** — double-check the forward-adjustment
  convention described in `corporate_actions.py` actually matches what you
  want before combining this data with any other back-adjusted series you
  may already have (e.g. in your main NSE system) — mixing conventions
  silently produces wrong spread values.
- **Liquidity filtering** — not yet implemented; thinly-traded F&O stocks
  may need to be excluded from the universe before trusting signals.

## Outputs
- `data/raw/{SYMBOL}_{near,far}_raw.csv` — unadjusted stitched leg data
- `data/corporate_actions/{SYMBOL}_actions.csv` — raw corporate actions pulled per stock
- `data/processed/{SYMBOL}_{near,far}_adj.csv` — forward-adjusted leg data
- `data/results/{SYMBOL}_results.csv` — full daily backtest table per stock
- `data/results/portfolio_results.csv` — combined portfolio daily P&L/returns
- `data/results/equity_curve_drawdown.png` — equity curve + drawdown plot
