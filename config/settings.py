import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")

TRADE_COIN = "KRW-BTC"   # 거래할 코인
INVEST_AMOUNT = 10000     # 1회 투자금액 (원)
