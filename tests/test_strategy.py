import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pyupbit
from src.strategy.ma_rsi_strategy import MaRsiStrategy
from src.strategy.indicators import moving_average, rsi

def test_signal():
    df = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=50)
    strategy = MaRsiStrategy(short_window=5, long_window=20)
    signal = strategy.generate_signal(df)
    print(f"\n현재 BTC 신호: {signal}")
    assert signal in ("BUY", "SELL", "HOLD")

def test_indicators():
    df = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=50)
    ma5  = moving_average(df, 5).iloc[-1]
    ma20 = moving_average(df, 20).iloc[-1]
    rsi_val = rsi(df, 14).iloc[-1]
    print(f"MA5:  {ma5:,.0f}원")
    print(f"MA20: {ma20:,.0f}원")
    print(f"RSI:  {rsi_val:.2f}")
    assert 0 < rsi_val < 100

if __name__ == "__main__":
    test_indicators()
    test_signal()
    print("\n모든 전략 테스트 통과")


import pandas as pd
from unittest.mock import patch


def _make_dummy_df(n=25):
    return pd.DataFrame({
        "close": [100.0] * n,
        "open":  [100.0] * n,
        "high":  [100.0] * n,
        "low":   [100.0] * n,
        "volume":[1000.0] * n,
    })


def test_buy_when_ma_up_and_rsi_below_60():
    """단기MA > 장기MA 상태 + RSI 50 → BUY"""
    strategy = MaRsiStrategy(short_window=5, long_window=20,
                             rsi_buy_max=60.0, rsi_overbought=75.0)
    df = _make_dummy_df(25)
    with patch("src.strategy.ma_rsi_strategy.moving_average") as mock_ma, \
         patch("src.strategy.ma_rsi_strategy.rsi") as mock_rsi:
        mock_ma.side_effect = [
            pd.Series([110.0] * 25),  # ma_short
            pd.Series([100.0] * 25),  # ma_long
        ]
        mock_rsi.return_value = pd.Series([50.0] * 25)
        signal = strategy.generate_signal(df)
    assert signal == "BUY"


def test_no_buy_when_rsi_above_60():
    """단기MA > 장기MA 상태지만 RSI 65 → HOLD"""
    strategy = MaRsiStrategy(short_window=5, long_window=20,
                             rsi_buy_max=60.0, rsi_overbought=75.0)
    df = _make_dummy_df(25)
    with patch("src.strategy.ma_rsi_strategy.moving_average") as mock_ma, \
         patch("src.strategy.ma_rsi_strategy.rsi") as mock_rsi:
        mock_ma.side_effect = [
            pd.Series([110.0] * 25),
            pd.Series([100.0] * 25),
        ]
        mock_rsi.return_value = pd.Series([65.0] * 25)
        signal = strategy.generate_signal(df)
    assert signal == "HOLD"


def test_sell_when_ma_down():
    """단기MA < 장기MA 상태 → SELL"""
    strategy = MaRsiStrategy(short_window=5, long_window=20,
                             rsi_buy_max=60.0, rsi_overbought=75.0)
    df = _make_dummy_df(25)
    with patch("src.strategy.ma_rsi_strategy.moving_average") as mock_ma, \
         patch("src.strategy.ma_rsi_strategy.rsi") as mock_rsi:
        mock_ma.side_effect = [
            pd.Series([90.0] * 25),   # ma_short < ma_long
            pd.Series([100.0] * 25),
        ]
        mock_rsi.return_value = pd.Series([50.0] * 25)
        signal = strategy.generate_signal(df)
    assert signal == "SELL"


def test_sell_when_rsi_overbought():
    """RSI 80 >= 75 → SELL (MA 상태 무관)"""
    strategy = MaRsiStrategy(short_window=5, long_window=20,
                             rsi_buy_max=60.0, rsi_overbought=75.0)
    df = _make_dummy_df(25)
    with patch("src.strategy.ma_rsi_strategy.moving_average") as mock_ma, \
         patch("src.strategy.ma_rsi_strategy.rsi") as mock_rsi:
        mock_ma.side_effect = [
            pd.Series([110.0] * 25),  # ma_short > ma_long (상승 추세)
            pd.Series([100.0] * 25),
        ]
        mock_rsi.return_value = pd.Series([80.0] * 25)
        signal = strategy.generate_signal(df)
    assert signal == "SELL"
