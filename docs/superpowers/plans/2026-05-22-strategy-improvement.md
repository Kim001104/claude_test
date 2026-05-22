# 전략 개선 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매수 신호 빈도를 높이기 위해 MA 상태 기반 조건으로 완화하고, 5분 감시와 중복되는 익절 로직을 제거하며, 손절 임계값을 넓힌다.

**Architecture:** 3개 파일을 순서대로 수정한다. (1) `ma_rsi_strategy.py` — 매수/매도 조건 변경, (2) `risk_manager.py` — 익절 파라미터 제거, (3) `trader.py` — 손절 상수 변경 및 RiskManager 호출 정리. 각 변경마다 테스트 먼저 작성 후 구현한다.

**Tech Stack:** Python 3.10, pandas, pytest, unittest.mock

---

### Task 1: 매수/매도 조건 변경 (`ma_rsi_strategy.py`)

**Files:**
- Modify: `src/strategy/ma_rsi_strategy.py`
- Modify: `tests/test_strategy.py`

**변경 요약:**
- 매수: 골든크로스 발생 순간 → 단기MA > 장기MA 상태 유지 중, RSI 상한 70 → 60
- 매도: 데드크로스 발생 순간 → 단기MA < 장기MA 상태, RSI 기준 70 → 75
- `rsi_buy_max` 파라미터 추가로 매수/매도 RSI 기준 분리

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_strategy.py` 하단에 아래 테스트 추가:

```python
from unittest.mock import patch

def _make_dummy_df(n=25):
    return pd.DataFrame({
        "close": [100.0] * n,
        "open":  [100.0] * n,
        "high":  [100.0] * n,
        "low":   [100.0] * n,
        "volume":[1000.0] * n,
    })

def test_buy_when_ma_up_and_rsi_below_60():
    """단기MA > 장기MA 상태 + RSI 50 → BUY"""
    strategy = MaRsiStrategy(short_window=5, long_window=20,
                             rsi_buy_max=60.0, rsi_overbought=75.0)
    df = _make_dummy_df(25)
    with patch("src.strategy.ma_rsi_strategy.moving_average") as mock_ma, \
         patch("src.strategy.ma_rsi_strategy.rsi") as mock_rsi:
        mock_ma.side_effect = [
            pd.Series([110.0] * 25),  # ma_short
            pd.Series([100.0] * 25),  # ma_long
        ]
        mock_rsi.return_value = pd.Series([50.0] * 25)
        signal = strategy.generate_signal(df)
    assert signal == "BUY"

def test_no_buy_when_rsi_above_60():
    """단기MA > 장기MA 상태지만 RSI 65 → HOLD"""
    strategy = MaRsiStrategy(short_window=5, long_window=20,
                             rsi_buy_max=60.0, rsi_overbought=75.0)
    df = _make_dummy_df(25)
    with patch("src.strategy.ma_rsi_strategy.moving_average") as mock_ma, \
         patch("src.strategy.ma_rsi_strategy.rsi") as mock_rsi:
        mock_ma.side_effect = [
            pd.Series([110.0] * 25),
            pd.Series([100.0] * 25),
        ]
        mock_rsi.return_value = pd.Series([65.0] * 25)
        signal = strategy.generate_signal(df)
    assert signal == "HOLD"

def test_sell_when_ma_down():
    """단기MA < 장기MA 상태 → SELL"""
    strategy = MaRsiStrategy(short_window=5, long_window=20,
                             rsi_buy_max=60.0, rsi_overbought=75.0)
    df = _make_dummy_df(25)
    with patch("src.strategy.ma_rsi_strategy.moving_average") as mock_ma, \
         patch("src.strategy.ma_rsi_strategy.rsi") as mock_rsi:
        mock_ma.side_effect = [
            pd.Series([90.0] * 25),   # ma_short < ma_long
            pd.Series([100.0] * 25),
        ]
        mock_rsi.return_value = pd.Series([50.0] * 25)
        signal = strategy.generate_signal(df)
    assert signal == "SELL"

def test_sell_when_rsi_overbought():
    """RSI 80 >= 75 → SELL (MA 상태 무관)"""
    strategy = MaRsiStrategy(short_window=5, long_window=20,
                             rsi_buy_max=60.0, rsi_overbought=75.0)
    df = _make_dummy_df(25)
    with patch("src.strategy.ma_rsi_strategy.moving_average") as mock_ma, \
         patch("src.strategy.ma_rsi_strategy.rsi") as mock_rsi:
        mock_ma.side_effect = [
            pd.Series([110.0] * 25),  # ma_short > ma_long (상승 추세)
            pd.Series([100.0] * 25),
        ]
        mock_rsi.return_value = pd.Series([80.0] * 25)
        signal = strategy.generate_signal(df)
    assert signal == "SELL"
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
python -m pytest tests/test_strategy.py::test_buy_when_ma_up_and_rsi_below_60 -v
```

Expected: `FAILED` — `MaRsiStrategy.__init__() got an unexpected keyword argument 'rsi_buy_max'`

- [ ] **Step 3: `ma_rsi_strategy.py` 구현 변경**

`src/strategy/ma_rsi_strategy.py` 전체를 아래로 교체:

```python
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
        rsi_oversold: float = 30.0,
    ):
        self.short_window = short_window
        self.long_window = long_window
        self.rsi_period = rsi_period
        self.rsi_buy_max = rsi_buy_max
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

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
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
python -m pytest tests/test_strategy.py -v
```

Expected: 모든 테스트 `PASSED`

- [ ] **Step 5: 커밋**

```bash
git add src/strategy/ma_rsi_strategy.py tests/test_strategy.py
git commit -m "feat: MA 상태 기반 매수/매도 조건으로 변경 (RSI 매수 60, 매도 75)"
```

---

### Task 2: RiskManager 익절 제거 (`risk_manager.py`)

**Files:**
- Modify: `src/strategy/risk_manager.py`
- Modify: `tests/test_risk_manager.py`

**변경 요약:**
- `take_profit` 파라미터 및 익절 체크 로직 제거
- 트레일링 스탑 로직만 유지
- 익절은 `check_price_alarm()` (5분 감시)에서 전담

- [ ] **Step 1: 테스트에서 익절 관련 항목 제거 후 생성자 변경**

`tests/test_risk_manager.py`를 아래로 교체:

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from src.strategy.risk_manager import RiskManager, SELL, HOLD


def _make_df(closes: list) -> pd.DataFrame:
    return pd.DataFrame({"close": closes})


def test_trailing_stop():
    rm = RiskManager(trailing_stop=0.02)
    # 고점 110, 현재 107 → 107 <= 110 * 0.98 = 107.8 → SELL
    df = _make_df([100, 105, 110, 107])
    assert rm.check(avg_buy_price=100.0, df=df) == SELL


def test_hold():
    rm = RiskManager(trailing_stop=0.02)
    # 익절 없음, 트레일링 스탑 미달
    df = _make_df([100, 101, 101, 101])
    assert rm.check(avg_buy_price=100.0, df=df) == HOLD


def test_trailing_high_fallback_when_always_at_loss():
    rm = RiskManager(trailing_stop=0.02)
    # 매수가 100 이상인 종가 없음 → trailing_high = avg_buy_price = 100
    # 현재가 97 <= 100 * 0.98 = 98 → SELL
    df = _make_df([95, 96, 97, 97])
    assert rm.check(avg_buy_price=100.0, df=df) == SELL


def test_trailing_high_fallback_hold():
    rm = RiskManager(trailing_stop=0.02)
    # trailing_high = avg_buy_price = 100, 현재가 99 > 98 → HOLD
    df = _make_df([95, 96, 98, 99])
    assert rm.check(avg_buy_price=100.0, df=df) == HOLD


def test_trailing_stop_boundary_above():
    rm = RiskManager(trailing_stop=0.02)
    # 고점 110, 현재 108.9 → 108.9 > 110 * 0.98 = 107.8 → HOLD
    df = _make_df([100, 105, 110, 108.9])
    assert rm.check(avg_buy_price=100.0, df=df) == HOLD
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
python -m pytest tests/test_risk_manager.py -v
```

Expected: `FAILED` — `RiskManager.__init__() got an unexpected keyword argument` 또는 기존 테스트 실패

- [ ] **Step 3: `risk_manager.py` 구현 변경**

`src/strategy/risk_manager.py` 전체를 아래로 교체:

```python
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
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
python -m pytest tests/test_risk_manager.py -v
```

Expected: 5개 테스트 모두 `PASSED`

- [ ] **Step 5: 커밋**

```bash
git add src/strategy/risk_manager.py tests/test_risk_manager.py
git commit -m "feat: RiskManager 익절 로직 제거 — 5분 감시로 통합"
```

---

### Task 3: 손절 완화 및 RiskManager 호출 정리 (`trader.py`)

**Files:**
- Modify: `src/trader/trader.py`

**변경 요약:**
- `FAST_STOP_LOSS` 0.03 → 0.05
- `RiskManager()` 생성자에서 `take_profit` 인수 제거 (이미 없어졌으므로 호환 확인)

- [ ] **Step 1: `trader.py` 상수 및 생성자 수정**

`src/trader/trader.py`에서 아래 두 줄 변경:

변경 전:
```python
FAST_TAKE_PROFIT = 0.02  # +2% 즉시 익절
FAST_STOP_LOSS   = 0.03  # -3% 즉시 손절
```

변경 후:
```python
FAST_TAKE_PROFIT = 0.02  # +2% 즉시 익절
FAST_STOP_LOSS   = 0.05  # -5% 즉시 손절
```

- [ ] **Step 2: 전체 테스트 실행 → PASS 확인**

```bash
python -m pytest tests/ -v
```

Expected: 전체 테스트 `PASSED`

- [ ] **Step 3: 커밋**

```bash
git add src/trader/trader.py
git commit -m "feat: 손절 임계값 -3% → -5% 완화"
```

---

### Task 4: 서버 배포

- [ ] **Step 1: 원격 저장소에 push**

```bash
git push
```

- [ ] **Step 2: 서버 SSH 접속 후 반영**

```bash
ssh -i c:\claude_test\ssh-key-2026-05-21.key ubuntu@144.24.67.154
```

```bash
cd claude_test
git pull
pkill -f "python main.py"
source venv/bin/activate
nohup python main.py &
tail -f nohup.out
```

Expected: `"봇 시작. 5분 감시 + 한국 시간..."` 로그 확인
