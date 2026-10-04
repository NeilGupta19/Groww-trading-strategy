"""
Step 15: Transaction costs. Approximate Indian F&O cost structure —
verify current rates (SEBI/exchange charges get revised periodically)
before trusting the resulting net P&L.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import settings


def cost_per_leg_trade(notional, is_buy):
    """
    Returns the estimated cost (Rs) of one leg's entry or exit trade,
    given its notional value and whether it's a buy or sell.
    """
    brokerage = settings.BROKERAGE_PER_ORDER
    exchange_txn = notional * settings.EXCHANGE_TXN_RATE
    sebi_charges = notional * settings.SEBI_CHARGES_RATE
    gst = settings.GST_RATE * (brokerage + exchange_txn)

    stt = notional * settings.STT_SELL_RATE if not is_buy else 0.0
    stamp_duty = notional * settings.STAMP_DUTY_BUY_RATE if is_buy else 0.0

    return brokerage + exchange_txn + sebi_charges + gst + stt + stamp_duty


def apply_transaction_costs(df):
    """
    Applies costs on every day the position CHANGES (entry, exit, or flip),
    since that's when actual trades occur — both legs of the spread trade
    together on each change.
    """
    df = df.copy()
    df["position_change"] = df["position"].diff().fillna(df["position"].iloc[0])

    costs = []
    for i in range(len(df)):
        change = df["position_change"].iloc[i]
        if change == 0:
            costs.append(0.0)
            continue

        # A position change means both legs trade (open or close), each leg's
        # notional based on that day's adjusted close and lot size.
        notional_near = df["close_adj_near"].iloc[i] * df["lot_size"].iloc[i] * settings.NUM_LOTS_PER_LEG
        notional_far = df["close_adj_far"].iloc[i] * df["lot_size"].iloc[i] * settings.NUM_LOTS_PER_LEG

        # direction of each leg's trade depends on whether we're entering
        # long-the-spread (buy far/sell near) or short-the-spread (sell far/buy near)
        going_long_spread = change > 0
        near_is_buy = not going_long_spread
        far_is_buy = going_long_spread

        cost = cost_per_leg_trade(notional_near, near_is_buy) + cost_per_leg_trade(notional_far, far_is_buy)
        costs.append(cost)

    df["transaction_cost"] = costs
    return df
