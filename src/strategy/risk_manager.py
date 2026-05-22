import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

SELL = "SELL"
HOLD = "HOLD"


class RiskManager:
    def __init__(self, trailing_stop: float = 0.02):
        self.trailing_stop = trailing_stop

    def check(self, avg_buy_price: float, df: pd.DataFrame) -> str:
        if df.empty:
            logger.warning("데이터 없음 — HOLD 반환")
            return HOLD
        current_price = df.iloc[-1]["close"]

        recent = df["close"].iloc[-20:]
        above_buy = recent[recent >= avg_buy_price]
        trailing_high = float(above_buy.max()) if not above_buy.empty else avg_buy_price

        if current_price <= trailing_high * (1 - self.trailing_stop):
            logger.info(f"트레일링 스탑: 현재가 {current_price:,.0f} / 고점 {trailing_high:,.0f} (-{self.trailing_stop*100:.0f}%)")
            return SELL

        logger.info(f"리스크 HOLD: 현재가 {current_price:,.0f} / 고점 {trailing_high:,.0f} / 매수가 {avg_buy_price:,.0f}")
        return HOLD
