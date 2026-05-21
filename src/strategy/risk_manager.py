import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

SELL = "SELL"
HOLD = "HOLD"


class RiskManager:
    def __init__(self, take_profit: float = 0.02, trailing_stop: float = 0.02):
        self.take_profit = take_profit
        self.trailing_stop = trailing_stop

    def check(self, avg_buy_price: float, df: pd.DataFrame) -> str:
        current_price = df.iloc[-1]["close"]

        above_buy = df["close"][df["close"] >= avg_buy_price]
        trailing_high = float(above_buy.max()) if not above_buy.empty else avg_buy_price

        if current_price >= avg_buy_price * (1 + self.take_profit):
            logger.info(f"익절 신호: 현재가 {current_price:,.0f} / 매수가 {avg_buy_price:,.0f} (+{self.take_profit*100:.0f}%)")
            return SELL

        if current_price <= trailing_high * (1 - self.trailing_stop):
            logger.info(f"트레일링 스탑: 현재가 {current_price:,.0f} / 고점 {trailing_high:,.0f} (-{self.trailing_stop*100:.0f}%)")
            return SELL

        logger.info(f"리스크 HOLD: 현재가 {current_price:,.0f} / 고점 {trailing_high:,.0f} / 매수가 {avg_buy_price:,.0f}")
        return HOLD
