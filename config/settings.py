"""
All non-secret configuration for the calendar spread backtest.
"""

# ---- Backtest period ----
BACKTEST_START = "2023-01-01"
BACKTEST_END = "2024-12-31"

EXCHANGE = "NSE"

# ---- Paths ----
INSTRUMENTS_CSV_PATH = "instruments.csv"  # auto-fetched via groww.get_all_instruments() and cached here — no manual download needed
RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
CORPORATE_ACTIONS_DIR = "data/corporate_actions"
RESULTS_DIR = "data/results"

# ---- Universe ----
INDEX_UNDERLYINGS_TO_EXCLUDE = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"}
UNDERLYING_SYMBOLS = {"INFY","INDIGO","ITC"}  # None = auto-discover all F&O stocks; or set an explicit list to restrict

# ---- Strategy parameters ----
ZSCORE_LOOKBACK_DAYS = 60
ENTRY_ZSCORE = 1.5
EXIT_ZSCORE = 0.25
ROLL_BUFFER_DAYS = 2  # force-exit this many trading days before near-leg expiry

# ---- Position sizing ----
NUM_LOTS_PER_LEG = 1

# ---- Transaction costs (approximate — verify current rates before trusting P&L) ----
# These are regulatory/exchange rates that get revised periodically by
# SEBI/NSE — check current values (e.g. on NSE's or your broker's charges
# page) before relying on these numbers for anything beyond a rough estimate.
BROKERAGE_PER_ORDER = 20.0          # flat Rs per executed order (typical discount-broker flat fee)
STT_SELL_RATE = 0.0002              # Securities Transaction Tax, sell side, futures (approx)
EXCHANGE_TXN_RATE = 0.000019        # NSE F&O transaction charges (approx)
GST_RATE = 0.18                     # on (brokerage + exchange txn charges)
STAMP_DUTY_BUY_RATE = 0.00002       # buy side (approx)
SEBI_CHARGES_RATE = 0.0000010       # negligible but included for completeness

# ---- Analytics ----
RISK_FREE_RATE_ANNUAL = 0.065  # approx Indian T-bill rate for Sharpe calc — adjust as needed
TRADING_DAYS_PER_YEAR = 252
