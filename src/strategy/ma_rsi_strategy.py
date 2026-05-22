import pandas as pd
from src.strategy.indicators import moving_average, rsi
from src.utils.logger import get_logger

logger = get_logger(__name__)

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


class MaRsiStrategy:
    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 20,
        rsi_period: int = 14,
        rsi_buy_max: float = 60.0,
        rsi_overbought: float = 75.0,
    ):
        self.short_window = short_window
        self.long_window = long_window
        self.rsi_period = rsi_period
        self.rsi_buy_max = rsi_buy_max
        self.rsi_overbought = rsi_overbought

    def generate_signal(self, df: pd.DataFrame) -> str:
        if len(df) < self.long_window + 1:
            logger.warning("데이터 부족 — HOLD")
            return HOLD

        df = df.copy()
        df["ma_short"] = moving_average(df, self.short_window)
        df["ma_long"] = moving_average(df, self.long_window)
        df["rsi"] = rsi(df, self.rsi_period)

        curr = df.iloc[-1]
        rsi_value = curr["rsi"]

        logger.info(
            f"MA({self.short_window}): {curr['ma_short']:,.0f} | "
            f"MA({self.long_window}): {curr['ma_long']:,.0f} | "
            f"RSI: {rsi_value:.1f}"
        )

        ma_up   = curr["ma_short"] > curr["ma_long"]
        ma_down = curr["ma_short"] < curr["ma_long"]

        if ma_up and rsi_value < self.rsi_buy_max:
            logger.info("신호: BUY  (상승 추세 + RSI 정상)")
            return BUY

        if ma_down or rsi_value >= self.rsi_overbought:
            reason = "하락 추세" if ma_down else f"RSI 과매수({rsi_value:.1f})"
            logger.info(f"신호: SELL ({reason})")
            return SELL

        logger.info("신호: HOLD")
        return HOLD
