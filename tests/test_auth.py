import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pyupbit
from config.settings import ACCESS_KEY, SECRET_KEY

def test_auth():
    print(f"Access Key 앞 8자리: {ACCESS_KEY[:8]}...")

    upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)
    balances = upbit.get_balances()
    print(f"잔고 원본 응답: {balances}")

if __name__ == "__main__":
    test_auth()
