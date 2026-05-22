import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from src.strategy.risk_manager import RiskManager, SELL, HOLD


def _make_df(closes: list) -> pd.DataFrame:
    return pd.DataFrame({"close": closes})


def test_trailing_stop():
    rm = RiskManager(trailing_stop=0.02)
    # 고점 110, 현재 107 → 107 <= 110 * 0.98 = 107.8 → SELL
    df = _make_df([100, 105, 110, 107])
    assert rm.check(avg_buy_price=100.0, df=df) == SELL


def test_hold():
    rm = RiskManager(trailing_stop=0.02)
    # 익절 없음, 트레일링 스탑 미달
    df = _make_df([100, 101, 101, 101])
    assert rm.check(avg_buy_price=100.0, df=df) == HOLD


def test_trailing_high_fallback_when_always_at_loss():
    rm = RiskManager(trailing_stop=0.02)
    # 매수가 100 이상인 종가 없음 → trailing_high = avg_buy_price = 100
    # 현재가 97 <= 100 * 0.98 = 98 → SELL
    df = _make_df([95, 96, 97, 97])
    assert rm.check(avg_buy_price=100.0, df=df) == SELL


def test_trailing_high_fallback_hold():
    rm = RiskManager(trailing_stop=0.02)
    # trailing_high = avg_buy_price = 100, 현재가 99 > 98 → HOLD
    df = _make_df([95, 96, 98, 99])
    assert rm.check(avg_buy_price=100.0, df=df) == HOLD


def test_trailing_stop_boundary_above():
    rm = RiskManager(trailing_stop=0.02)
    # 고점 110, 현재 108.9 → 108.9 > 110 * 0.98 = 107.8 → HOLD
    df = _make_df([100, 105, 110, 108.9])
    assert rm.check(avg_buy_price=100.0, df=df) == HOLD
