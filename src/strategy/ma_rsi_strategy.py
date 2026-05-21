import pandas as pd
from src.strategy.indicators import moving_average, rsi
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 신호 상수
BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


class MaRsiStrategy:
    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 20,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
    ):
        self.short_window = short_window
        self.long_window = long_window
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    def generate_signal(self, df: pd.DataFrame) -> str:
        """
        df: pyupbit.get_ohlcv() 로 받은 캔들 데이터
        반환: BUY / SELL / HOLD
        """
        if len(df) < self.long_window + 1:
            logger.warning("데이터 부족 — HOLD")
            return HOLD

        df = df.copy()
        df["ma_short"] = moving_average(df, self.short_window)
        df["ma_long"] = moving_average(df, self.long_window)
        df["rsi"] = rsi(df, self.rsi_period)

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        ma_cross_up   = prev["ma_short"] <= prev["ma_long"] and curr["ma_short"] > curr["ma_long"]
        ma_cross_down = prev["ma_short"] >= prev["ma_long"] and curr["ma_short"] < curr["ma_long"]

        rsi_value = curr["rsi"]

        logger.info(
            f"MA({self.short_window}): {curr['ma_short']:,.0f} | "
            f"MA({self.long_window}): {curr['ma_long']:,.0f} | "
            f"RSI: {rsi_value:.1f}"
        )

        if ma_cross_up and rsi_value < self.rsi_overbought:
            logger.info("신호: BUY  (골든크로스 + RSI 정상)")
            return BUY

        if ma_cross_down or rsi_value >= self.rsi_overbought:
            reason = "데드크로스" if ma_cross_down else f"RSI 과매수({rsi_value:.1f})"
            logger.info(f"신호: SELL ({reason})")
            return SELL

        logger.info("신호: HOLD")
        return HOLD
