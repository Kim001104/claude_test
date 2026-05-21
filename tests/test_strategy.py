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
