# RiskManager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 MA+RSI 자동매매 봇에 익절(+2%) 및 트레일링 스탑(-2%) 리스크 관리 기능을 추가한다.

**Architecture:** 리스크 판단 로직을 `RiskManager` 클래스로 분리하고, `UpbitAPI`에 평균매수가 조회 메서드를 추가한다. `Trader.run_once()`는 보유 중일 때 전략 신호 확인 전에 리스크 체크를 먼저 수행한다.

**Tech Stack:** Python, pyupbit, pandas

---

## 파일 구조

| 파일 | 역할 |
|------|------|
| `src/strategy/risk_manager.py` | 신규 — RiskManager 클래스 (익절/트레일링 스탑 판단) |
| `src/api/upbit_api.py` | 수정 — `get_avg_buy_price()` 추가 |
| `src/trader/trader.py` | 수정 — RiskManager 연동, run_once() 흐름 변경 |
| `tests/test_risk_manager.py` | 신규 — RiskManager 단위 테스트 |

---

### Task 1: RiskManager 단위 테스트 작성

**Files:**
- Create: `tests/test_risk_manager.py`

- [ ] **Step 1: 테스트 파일 생성**

```python
# tests/test_risk_manager.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest
from src.strategy.risk_manager import RiskManager

HOLD = "HOLD"
SELL = "SELL"


def _make_df(closes: list) -> pd.DataFrame:
    """테스트용 일봉 DataFrame 생성"""
    return pd.DataFrame({"close": closes})


def test_take_profit():
    rm = RiskManager(take_profit=0.02, trailing_stop=0.02)
    df = _make_df([95, 98, 100, 102])
    assert rm.check(avg_buy_price=100.0, df=df) == SELL


def test_trailing_stop():
    rm = RiskManager(take_profit=0.02, trailing_stop=0.02)
    # 고점 110, 현재 107 → 107 <= 110 * 0.98 = 107.8 → SELL
    df = _make_df([100, 105, 110, 107])
    assert rm.check(avg_buy_price=100.0, df=df) == SELL


def test_hold():
    rm = RiskManager(take_profit=0.02, trailing_stop=0.02)
    # 익절 미달, 트레일링 스탑 미달
    df = _make_df([100, 101, 101, 101])
    assert rm.check(avg_buy_price=100.0, df=df) == HOLD


def test_trailing_high_fallback_when_always_at_loss():
    rm = RiskManager(take_profit=0.02, trailing_stop=0.02)
    # 매수가 100 이상인 종가 없음 → trailing_high = avg_buy_price = 100
    # 현재가 97 <= 100 * 0.98 = 98 → SELL
    df = _make_df([95, 96, 97, 97])
    assert rm.check(avg_buy_price=100.0, df=df) == SELL


def test_trailing_high_fallback_hold():
    rm = RiskManager(take_profit=0.02, trailing_stop=0.02)
    # trailing_high = avg_buy_price = 100, 현재가 99 > 98 → HOLD
    df = _make_df([95, 96, 98, 99])
    assert rm.check(avg_buy_price=100.0, df=df) == HOLD
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```
pytest tests/test_risk_manager.py -v
```

예상 결과: `ModuleNotFoundError: No module named 'src.strategy.risk_manager'`

---

### Task 2: RiskManager 구현

**Files:**
- Create: `src/strategy/risk_manager.py`

- [ ] **Step 1: RiskManager 클래스 작성**

```python
# src/strategy/risk_manager.py
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
```

- [ ] **Step 2: 테스트 실행 — 통과 확인**

```
pytest tests/test_risk_manager.py -v
```

예상 결과: 5개 테스트 모두 PASS

- [ ] **Step 3: 커밋**

```
git add src/strategy/risk_manager.py tests/test_risk_manager.py
git commit -m "feat: RiskManager 구현 (익절 +2%, 트레일링 스탑 -2%)"
```

---

### Task 3: UpbitAPI에 get_avg_buy_price 추가

**Files:**
- Modify: `src/api/upbit_api.py`

- [ ] **Step 1: get_avg_buy_price 메서드 추가**

`src/api/upbit_api.py`의 `get_balance()` 메서드 아래에 추가:

```python
def get_avg_buy_price(self, ticker: str) -> float:
    """평균매수가 조회. 미보유 또는 오류 시 0.0 반환"""
    try:
        coin = ticker.split("-")[1]  # "KRW-BTC" → "BTC"
        price = self.upbit.get_avg_buy_price(coin)
        return float(price) if price else 0.0
    except Exception as e:
        logger.warning(f"평균매수가 조회 실패: {e}")
        return 0.0
```

- [ ] **Step 2: 동작 확인 (수동)**

파이썬 인터프리터에서:
```python
from src.api.upbit_api import UpbitAPI
api = UpbitAPI()
print(api.get_avg_buy_price("KRW-BTC"))  # 미보유 시 0.0, 보유 시 평균매수가
```

- [ ] **Step 3: 커밋**

```
git add src/api/upbit_api.py
git commit -m "feat: UpbitAPI에 get_avg_buy_price 추가"
```

---

### Task 4: Trader에 RiskManager 연동

**Files:**
- Modify: `src/trader/trader.py`

- [ ] **Step 1: trader.py 전체 교체**

```python
# src/trader/trader.py
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
```

- [ ] **Step 2: 전체 테스트 실행**

```
pytest tests/ -v
```

예상 결과: 기존 테스트 + `test_risk_manager.py` 5개 모두 PASS

- [ ] **Step 3: 커밋**

```
git add src/trader/trader.py
git commit -m "feat: Trader에 RiskManager 연동 — 보유 시 리스크 체크 우선"
```
