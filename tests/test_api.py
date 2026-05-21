import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pyupbit

def test_current_price():
    price = pyupbit.get_current_price("KRW-BTC")
    print(f"BTC 현재가: {price:,.0f}원")
    assert price > 0

def test_ohlcv():
    df = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=5)
    print(df)
    assert df is not None and len(df) == 5

if __name__ == "__main__":
    test_current_price()
    test_ohlcv()
    print("\n모든 테스트 통과")
