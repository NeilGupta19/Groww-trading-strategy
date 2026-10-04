"""
Starter test for the z-score module. Add more tests per module as the
pipeline stabilizes (signals, corporate-action factor parsing, and pnl
are the highest-value ones to cover next, since bugs there are easy to
miss and expensive if wrong).
"""

import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.zscore import compute_zscore


def test_zscore_basic():
    series = pd.Series([1, 2, 3, 4, 5, 4, 3, 2, 1, 2, 3, 4, 5])
    z = compute_zscore(series, window=5)
    # first 4 values should be NaN (not enough data for the rolling window)
    assert z.iloc[:4].isna().all()
    # after the window fills, we should get real numbers
    assert not pd.isna(z.iloc[-1])


if __name__ == "__main__":
    test_zscore_basic()
    print("test_zscore_basic passed")
