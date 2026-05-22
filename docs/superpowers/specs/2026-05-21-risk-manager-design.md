# RiskManager 설계 문서

**날짜:** 2026-05-21  
**대상 브랜치:** main

---

## 개요

기존 MA + RSI 전략 봇에 실전 리스크 관리 기능을 추가한다.  
익절(고정 +2%)과 트레일링 스탑(고점 대비 -2%)을 별도 `RiskManager` 클래스로 구현하여 전략 로직과 분리한다.

---

## 요구사항

| 항목 | 내용 |
|------|------|
| 익절 | 평균매수가 대비 +2% 이상이면 매도 |
| 트레일링 스탑 | 보유 기간 중 최고 종가 대비 -2% 이하이면 매도 |
| 실행 주기 | 하루 1번 (일봉 기준) |
| 포지션 추적 | 업비트 API (잔고 + 평균매수가) |

---

## 아키텍처

### 파일 변경 범위

| 파일 | 변경 내용 |
|------|----------|
| `src/strategy/risk_manager.py` | 신규 생성 — RiskManager 클래스 |
| `src/api/upbit_api.py` | `get_avg_buy_price()` 메서드 추가 |
| `src/trader/trader.py` | RiskManager 연동, run_once() 흐름 변경 |

---

## 컴포넌트 상세

### RiskManager (`src/strategy/risk_manager.py`)

**역할:** 보유 포지션의 익절/트레일링 스탑 판단

**인터페이스:**
```python
class RiskManager:
    def __init__(self, take_profit: float = 0.02, trailing_stop: float = 0.02)
    def check(self, avg_buy_price: float, df: pd.DataFrame) -> str  # SELL | HOLD
```

**판단 로직:**
1. `df`의 종가(close) 중 `avg_buy_price` 이상인 값들의 최댓값 → `trailing_high`
   - 해당 값이 없으면(계속 손실 중) `trailing_high = avg_buy_price` 로 폴백
2. 현재가(`df.iloc[-1]["close"]`) 기준으로:
   - `현재가 >= avg_buy_price * (1 + take_profit)` → SELL (익절)
   - `현재가 <= trailing_high * (1 - trailing_stop)` → SELL (트레일링 스탑)
   - 그 외 → HOLD

---

### UpbitAPI 추가 메서드

```python
def get_avg_buy_price(self, ticker: str) -> float:
    """평균매수가 조회. 미보유 시 0.0 반환"""
```

pyupbit의 `get_avg_buy_price(coin)` 래핑. `ticker`("KRW-BTC")에서 코인명("BTC")을 파싱하여 호출.

---

### Trader.run_once() 새 흐름

```
1. 코인 잔고 조회
2. 보유 중(volume > 0)?
   ├─ YES
   │   ├─ 평균매수가 조회 (get_avg_buy_price)
   │   ├─ RiskManager.check() 실행
   │   │   ├─ SELL → 전량 매도 후 return
   │   │   └─ HOLD → 전략 신호 확인
   │   │             ├─ SELL → 전량 매도
   │   │             └─ BUY/HOLD → 아무것도 안 함
   └─ NO
       └─ 전략 신호 확인
           └─ BUY → 시장가 매수
```

---

## 에러 처리

- `get_avg_buy_price()` 실패 또는 0 반환 시 → 리스크 체크 건너뜀, 로그 경고
- OHLCV 데이터 부족 시 → RiskManager HOLD 반환

---

## 테스트 범위

- `RiskManager.check()`: 익절 조건, 트레일링 스탑 조건, HOLD 조건 단위 테스트
- `Trader.run_once()`: 보유/미보유 분기 통합 흐름 확인
