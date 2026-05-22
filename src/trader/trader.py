from src.api.upbit_api import UpbitAPI
from src.strategy.ma_rsi_strategy import MaRsiStrategy, BUY, SELL
from src.strategy.risk_manager import RiskManager
from src.utils.logger import get_logger
from config.settings import TRADE_COIN, INVEST_AMOUNT

logger = get_logger(__name__)

FAST_TAKE_PROFIT = 0.02  # +2% 즉시 익절
FAST_STOP_LOSS   = 0.05  # -5% 즉시 손절


class Trader:
    def __init__(self):
        self.api = UpbitAPI()
        self.strategy = MaRsiStrategy()
        self.risk = RiskManager()
        self.ticker = TRADE_COIN

    def run_once(self):
        """전략 판단 1회 실행 후 주문"""
        logger.info(f"=== {self.ticker} 전략 판단 시작 ===")

        df = self.api.get_ohlcv(self.ticker, interval="minute180", count=50)
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
            else:
                logger.warning("평균매수가 조회 실패 — 리스크 체크 건너뜀, 전략 신호만 사용")

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

    def check_price_alarm(self):
        """5분 감시: 매수가 대비 급등/급락 시 즉시 매도"""
        coin = self.ticker.split("-")[1]
        volume = self.api.get_balance(coin)
        if volume <= 0:
            return

        avg_buy_price = self.api.get_avg_buy_price(self.ticker)
        if avg_buy_price <= 0:
            return

        current_price = self.api.get_current_price(self.ticker)
        if current_price is None:
            logger.warning("현재가 조회 실패 — 감시 스킵")
            return

        change_rate = (current_price - avg_buy_price) / avg_buy_price
        logger.info(f"[5분 감시] 현재가 {current_price:,.0f} / 매수가 {avg_buy_price:,.0f} ({change_rate*100:+.1f}%)")

        if change_rate >= FAST_TAKE_PROFIT:
            logger.info(f"[빠른 익절] {change_rate*100:+.1f}% — 즉시 매도")
            self.api.sell_market_order(self.ticker, volume)
            return

        if change_rate <= -FAST_STOP_LOSS:
            logger.info(f"[빠른 손절] {change_rate*100:+.1f}% — 즉시 매도")
            self.api.sell_market_order(self.ticker, volume)
