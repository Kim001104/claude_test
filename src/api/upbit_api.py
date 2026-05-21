import pyupbit
from config.settings import ACCESS_KEY, SECRET_KEY
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UpbitAPI:
    def __init__(self):
        self.upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)
        logger.info("업비트 API 연결 완료")

    # ── 시세 조회 ────────────────────────────────────────────────

    def get_current_price(self, ticker: str) -> float:
        """현재가 조회"""
        price = pyupbit.get_current_price(ticker)
        logger.info(f"[{ticker}] 현재가: {price:,.0f}원")
        return price

    def get_ohlcv(self, ticker: str, interval: str = "day", count: int = 200):
        """캔들 데이터 조회 (interval: day/minute1/minute3/minute5/minute15/minute60)"""
        return pyupbit.get_ohlcv(ticker, interval=interval, count=count)

    def get_orderbook(self, ticker: str) -> dict:
        """호가 조회"""
        return pyupbit.get_orderbook(ticker)

    # ── 잔고 조회 ────────────────────────────────────────────────

    def get_balance(self, currency: str = "KRW") -> float:
        """잔고 조회 (KRW 또는 코인 심볼 입력)"""
        balance = self.upbit.get_balance(currency)
        logger.info(f"[{currency}] 잔고: {balance:,.2f}")
        return balance

    def get_avg_buy_price(self, ticker: str) -> float:
        """평균매수가 조회. 미보유 또는 오류 시 0.0 반환"""
        try:
            coin = ticker.split("-")[1]  # "KRW-BTC" → "BTC"
            price = self.upbit.get_avg_buy_price(coin)
            return float(price) if price else 0.0
        except Exception as e:
            logger.warning(f"평균매수가 조회 실패: {e}")
            return 0.0

    # ── 주문 ─────────────────────────────────────────────────────

    def buy_market_order(self, ticker: str, amount_krw: float):
        """시장가 매수 (amount_krw: 투자 금액(원))"""
        logger.info(f"[매수] {ticker} - {amount_krw:,.0f}원")
        return self.upbit.buy_market_order(ticker, amount_krw)

    def sell_market_order(self, ticker: str, volume: float):
        """시장가 매도 (volume: 코인 수량)"""
        logger.info(f"[매도] {ticker} - {volume} 개")
        return self.upbit.sell_market_order(ticker, volume)
