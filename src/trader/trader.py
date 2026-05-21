from src.api.upbit_api import UpbitAPI
from src.strategy.ma_rsi_strategy import MaRsiStrategy, BUY, SELL
from src.strategy.risk_manager import RiskManager
from src.utils.logger import get_logger
from config.settings import TRADE_COIN, INVEST_AMOUNT

logger = get_logger(__name__)


class Trader:
    def __init__(self):
        self.api = UpbitAPI()
        self.strategy = MaRsiStrategy()
        self.risk = RiskManager()
        self.ticker = TRADE_COIN

    def run_once(self):
        """전략 판단 1회 실행 후 주문"""
        logger.info(f"=== {self.ticker} 전략 판단 시작 ===")

        df = self.api.get_ohlcv(self.ticker, interval="day", count=50)
        if df is None:
            logger.error("캔들 데이터 조회 실패")
            return

        coin = self.ticker.split("-")[1]
        volume = self.api.get_balance(coin)

        if volume > 0:
            avg_buy_price = self.api.get_avg_buy_price(self.ticker)
            if avg_buy_price > 0:
                risk_signal = self.risk.check(avg_buy_price, df)
                if risk_signal == SELL:
                    self.api.sell_market_order(self.ticker, volume)
                    return

            strategy_signal = self.strategy.generate_signal(df)
            if strategy_signal == SELL:
                self.api.sell_market_order(self.ticker, volume)

        else:
            strategy_signal = self.strategy.generate_signal(df)
            if strategy_signal == BUY:
                krw_balance = self.api.get_balance("KRW")
                amount = min(INVEST_AMOUNT, krw_balance)
                if amount < 5000:
                    logger.warning(f"KRW 잔고 부족 ({krw_balance:,.0f}원) — 매수 건너뜀")
                    return
                self.api.buy_market_order(self.ticker, amount)
