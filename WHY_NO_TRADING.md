# 🔍 매수/매도가 실행되지 않는 이유 분석

## 📋 목차
1. [분석 요약](#분석-요약)
2. [매수가 실행되지 않는 7가지 이유](#매수가-실행되지-않는-7가지-이유)
3. [매도가 실행되지 않는 이유](#매도가-실행되지-않는-이유)
4. [실행 흐름도](#실행-흐름도)
5. [해결 방법](#해결-방법)

---

## 분석 요약

**현재 로그 상황**:
```
13:05:32 | Fast Scan → 50개
13:05:26 | 계좌 조회 (예수금: 500,000,000원)
13:05:31 | 포트폴리오 요약 (포지션 수: 0개)
```

**AI Scan 로그가 없음!** → **매수 신호가 생성되지 않음**

---

## 매수가 실행되지 않는 7가지 이유

### ✅ 체크리스트

매수가 실행되려면 **모든 조건이 충족**되어야 합니다:

#### 1️⃣ **AI Scan이 실행되어야 함**

**코드**: [main.py:186-222](main.py#L186-L222)

```python
async def _ai_scan_loop(self, interval: int):
    await asyncio.sleep(10)  # 10초 대기 후 시작
    while self.is_running:
        logger.info(f"[{datetime.now():%H:%M:%S}] AI Scan")
        # ... AI 분석 ...
        await asyncio.sleep(interval)  # 300초(5분) 대기
```

**현재 상태**: ❌ AI Scan 로그 없음

**원인**:
- AI Scan은 프로그램 시작 후 **10초 후**에 첫 실행
- 이후 **300초(5분)마다** 반복 실행
- 로그가 없다면 아직 10초가 지나지 않았거나, AI Scan이 에러로 중단됨

**확인 방법**:
```bash
# AI Scan 로그 검색
grep "AI Scan" logs/trading.log

# AI Scan 에러 검색
grep -A 5 "AI Scan 오류" logs/trading.log
```

**설정 위치**: `config/scanning_rules.yaml`
```yaml
intervals:
  ai_analysis: 300  # 5분 (300초)
```

---

#### 2️⃣ **test_mode가 false여야 함**

**코드**: [main.py:217](main.py#L217)

```python
if not self.config['trading']['test_mode'] and buy_recs:
    await self._execute_trades(buy_recs[:5])
```

**현재 상태**: ⚠️ `test_mode: true` (설정 확인 필요)

**의미**:
- `test_mode: true` → 매수 추천만 로그에 출력, **실제 주문 안 함**
- `test_mode: false` → 실제 주문 실행

**확인 방법**:
```bash
grep "test_mode" config/config.yaml
```

**설정 위치**: `config/config.yaml`
```yaml
trading:
  test_mode: true   # ← false로 변경하면 실제 매매
```

⚠️ **주의**: 실전 투자 전에 충분히 테스트하세요!

---

#### 3️⃣ **거래 시간이어야 함 (09:00 ~ 14:50)**

**코드**: [src/strategy/trading_strategy.py:187-193](src/strategy/trading_strategy.py#L187-L193)

```python
def _check_trading_time(self) -> bool:
    now = datetime.now().time()
    market_open = datetime.strptime(self.market_open, "%H:%M:%S").time()
    new_buy_close = datetime.strptime(self.new_buy_close, "%H:%M:%S").time()
    return market_open <= now <= new_buy_close
```

**현재 상태**: ⚠️ 로그 시간 13:05 → ✅ 거래 가능 시간

**거래 시간**:
- **매수 가능**: 09:00:00 ~ 14:50:00 (평일만)
- **매도 가능**: 09:00:00 ~ 15:30:00
- **주말/공휴일**: 거래 불가

**확인 방법**:
```bash
# 현재 시간 확인
date

# 평일 확인 (0=월요일, 6=일요일)
python3 -c "from datetime import datetime; print(datetime.now().weekday())"
```

**설정 위치**: `config/trading_rules.yaml`
```yaml
trading_hours:
  market_open: "09:00:00"
  new_buy_close: "14:50:00"
  market_close: "15:30:00"
```

---

#### 4️⃣ **Deep Scan에서 200점 이상 종목이 있어야 함**

**코드**: [src/strategy/trading_strategy.py:46](src/strategy/trading_strategy.py#L46)

```python
checks = {
    'score_check': stock_data.get('total_score', 0) >= 200,
    # ...
}
```

**현재 상태**: ❓ Deep Scan 로그 확인 필요

**의미**:
- Fast Scan → Deep Scan → **200점 이상 종목만** AI 분석
- 200점 미만이면 AI 분석 대상에서 제외

**확인 방법**:
```bash
# Deep Scan 결과 확인
grep "Deep Scan" logs/trading.log

# 200점 이상 종목 확인
grep -E "[2-9][0-9]{2}점|[3-9][0-9]{2}점" logs/trading.log
```

**설정 위치**: `config/scanning_rules.yaml`
```yaml
grading:
  ai_analysis_min_score: 200  # 최소 점수
  s_grade: 350
  a_grade: 280
  b_grade: 200
```

---

#### 5️⃣ **AI가 BUY를 추천해야 함**

**코드**: [main.py:199-203](main.py#L199-L203)

```python
buy_recs = [
    s for s in ai_result
    if s['ai_analysis'].get('recommendation') == 'BUY'
    and s['ai_analysis'].get('confidence', 0) >= min_confidence
]
```

**조건**:
- **추천**: `BUY` (HOLD, SELL은 제외)
- **신뢰도**: 70% 이상 (동적 리스크 관리로 조정)
- **확률**: 60% 이상

**코드**: [src/strategy/trading_strategy.py:53-57](src/strategy/trading_strategy.py#L53-L57)

```python
checks['ai_check'] = (
    ai_analysis.get('recommendation') == 'BUY' and
    ai_analysis.get('confidence', 0) >= 0.7 and
    ai_analysis.get('probability', 0) >= 60
)
```

**현재 상태**: ❓ AI Scan 결과 확인 필요

**확인 방법**:
```bash
# AI 매수 추천 확인
grep "매수 추천" logs/trading.log

# BUY 추천 상세
grep -A 5 "\[매수\]" logs/trading.log
```

**AI가 BUY를 추천하지 않는 이유**:
- 시장 상황이 좋지 않음 (하락장, 변동성 큰 장세)
- 기술적 지표가 좋지 않음
- 외국인/기관 매수세가 약함
- 뉴스/테마가 부정적

---

#### 6️⃣ **포지션 한도에 여유가 있어야 함**

**코드**: [src/strategy/trading_strategy.py:44](src/strategy/trading_strategy.py#L44)

```python
'position_limit': len(self.positions) < self.max_positions,
```

**현재 상태**: ✅ 포지션 0개 (한도 내)

**최대 포지션 수** (동적 리스크 관리):
- **공격적 (수익)**: 12개
- **정상**: 10개
- **보수적**: 7개
- **매우 보수적**: 5개

**확인 방법**:
```bash
# 현재 포지션 수 확인
grep "포지션 수:" logs/trading.log | tail -1
```

**설정 위치**: `config/config.yaml`
```yaml
dynamic_risk_management:
  profit_mode:
    max_positions: 12
  normal_mode:
    max_positions: 10
  # ...
```

---

#### 7️⃣ **일일 손실 한도를 초과하지 않아야 함**

**코드**: [src/strategy/trading_strategy.py:45](src/strategy/trading_strategy.py#L45)

```python
'daily_loss_limit': self.daily_realized_pnl > -self.max_daily_loss,
```

**현재 상태**: ✅ 실현손익 0원

**의미**:
- 하루 동안 실현 손실이 한도를 초과하면 **당일 매수 중단**
- 예: 한도 1,000만원, 손실 1,000만원 → 매수 불가

**확인 방법**:
```bash
# 실현손익 확인
grep "실현손익" logs/trading.log | tail -1
```

**설정 위치**: `config/config.yaml`
```yaml
trading:
  max_daily_loss: 10000000  # 1,000만원
```

---

## 매도가 실행되지 않는 이유

### 📉 매도 조건

매도는 **3가지 조건 중 하나**라도 충족되면 실행됩니다:

#### 1️⃣ **손절 (STOP_LOSS)**

**코드**: [src/strategy/trading_strategy.py:72-78](src/strategy/trading_strategy.py#L72-L78)

```python
if pnl_pct <= self.stop_loss_pct:
    return {
        'decision': True,
        'reason': 'STOP_LOSS',
        'pnl_pct': pnl_pct,
        'price': current_price
    }
```

**조건**:
- 손실률이 손절 기준 이하

**동적 리스크 관리**:
- 공격적: -2.5%
- 정상: -3.0%
- 보수적: -2.0%
- 매우 보수적: -1.5%

---

#### 2️⃣ **익절 (TAKE_PROFIT)**

**코드**: [src/strategy/trading_strategy.py:81-87](src/strategy/trading_strategy.py#L81-L87)

```python
if pnl_pct >= self.take_profit_pct:
    return {
        'decision': True,
        'reason': 'TAKE_PROFIT',
        'pnl_pct': pnl_pct,
        'price': current_price
    }
```

**조건**:
- 수익률이 익절 기준 이상

**동적 리스크 관리**:
- 공격적: +7.0%
- 정상: +5.0%
- 보수적: +4.0%
- 매우 보수적: +3.0%

---

#### 3️⃣ **장 마감 임박 (MARKET_CLOSING)**

**코드**: [src/strategy/trading_strategy.py:90-96](src/strategy/trading_strategy.py#L90-L96)

```python
if self._is_market_closing():
    return {
        'decision': True,
        'reason': 'MARKET_CLOSING',
        'pnl_pct': pnl_pct,
        'price': current_price
    }
```

**조건**:
- 15:10 이후 → 모든 포지션 청산

---

### ❌ 매도가 실행되지 않는 이유

**현재 상태**: 포지션 0개 → **매도할 것이 없음**

매도가 실행되려면:
1. ✅ 보유 포지션이 있어야 함
2. ✅ 위 3가지 조건 중 하나 충족
3. ✅ WebSocket으로 실시간 현재가 수신 중

**확인 방법**:
```bash
# 매도 신호 확인
grep "매도 신호" logs/trading.log

# 매도 주문 확인
grep "매도 주문" logs/trading.log
```

---

## 실행 흐름도

```
프로그램 시작
    ↓
┌───────────────────────────────────────┐
│ 0초: Fast Scan 시작 (10초마다 반복)   │
│ 5초: Deep Scan 시작 (60초마다 반복)   │
│ 10초: AI Scan 시작 (300초마다 반복) ← 여기! │
└───────────────────────────────────────┘
    ↓
[AI Scan 실행]
    ↓
Fast Scan (50개) → Deep Scan (200점+ 필터링) → AI 분석 (상위 10개)
    ↓
AI 추천: BUY + 신뢰도 70%+ + 확률 60%+
    ↓
┌─────────────────────────────┐
│ test_mode 확인              │
│ - true: 로그만 출력         │
│ - false: 실제 주문 실행 ←  │
└─────────────────────────────┘
    ↓
[_execute_trades 실행]
    ↓
매수 조건 체크:
  ✅ 거래 시간 (09:00~14:50)
  ✅ 포지션 한도 미초과
  ✅ 일일 손실 한도 미초과
  ✅ Deep Scan 점수 200점+
  ✅ AI 신뢰도/확률 충족
    ↓
동적 리스크 관리:
  - 포지션 크기 계산
  - 현재 모드에 맞게 조정
    ↓
API 호출: order_buy()
    ↓
✅ 매수 완료!
```

---

## 해결 방법

### 🎯 단계별 해결

#### 1단계: 디버깅 실행

```bash
python debug_trading.py
```

이 스크립트가 모든 조건을 체크합니다.

---

#### 2단계: AI Scan 로그 확인

프로그램을 실행하고 **10초 대기** 후 AI Scan 로그 확인:

```bash
# 프로그램 실행
python main.py

# 다른 터미널에서 로그 확인
tail -f logs/trading.log | grep -E "AI Scan|매수"
```

**예상 로그**:
```
[13:05:42] AI Scan
매수 추천: 3개 (AI 신뢰도 70% 이상)
  [매수] 삼성전자 (005930)
    - 확률: 75%
    - 목표가: 72,000원
    - 신뢰도: 0.82
    - 이유: 외국인 순매수 + 기술적 돌파
```

---

#### 3단계: test_mode 확인

**현재 설정 확인**:
```bash
grep "test_mode" config/config.yaml
```

**출력**:
```yaml
test_mode: true   # ← 로그만 출력
```

**실제 매매를 원하면**:
```bash
nano config/config.yaml
```

변경:
```yaml
test_mode: false  # ← 실제 주문 실행
```

⚠️ **경고**: 실전 투자는 신중하게!

---

#### 4단계: 스캔 간격 조정 (선택)

AI Scan을 더 자주 실행하고 싶다면:

```bash
nano config/scanning_rules.yaml
```

변경:
```yaml
intervals:
  fast_scan: 10      # 10초
  deep_scan: 60      # 1분
  ai_analysis: 180   # 3분 (300초 → 180초)
```

---

#### 5단계: 로그 모니터링

실시간으로 매수/매도 상황을 확인:

**Windows PowerShell**:
```powershell
Get-Content logs\trading.log -Wait -Tail 100 | Select-String "AI Scan|매수|매도"
```

**Linux/Mac**:
```bash
tail -f logs/trading.log | grep -E "AI Scan|매수|매도"
```

---

## 💡 자주 묻는 질문 (FAQ)

### Q1: AI Scan이 실행되는데 매수 추천이 0개입니다.

**A**: 정상입니다. 다음 이유 때문일 수 있습니다:
- 시장 상황이 좋지 않음 (하락장, 횡보장)
- Deep Scan에서 200점 이상 종목이 없음
- AI가 모든 종목을 HOLD 또는 SELL로 판단
- 기다리면 다음 AI Scan(5분 후)에서 추천이 나올 수 있음

---

### Q2: 매수 추천은 있는데 실제 주문이 안 됩니다.

**A**: `test_mode` 설정을 확인하세요:
```bash
grep "test_mode" config/config.yaml
```

- `test_mode: true` → 로그만 출력
- `test_mode: false` → 실제 주문 실행

---

### Q3: 거래 시간인데 왜 안 되나요?

**A**: 여러 이유가 있을 수 있습니다:
1. AI Scan이 아직 실행되지 않음 (10초 대기)
2. Deep Scan 점수가 200점 미만
3. AI 신뢰도가 70% 미만
4. API 연결 오류 (Mock API 서버 문제)

`debug_trading.py`를 실행하여 정확한 원인을 파악하세요.

---

### Q4: 주말/공휴일에도 테스트할 수 있나요?

**A**: 코드를 수정하면 가능합니다:

`src/strategy/trading_strategy.py`:
```python
def _check_trading_time(self) -> bool:
    # 테스트용: 항상 True 반환
    return True

    # 원래 코드 (주석 처리)
    # now = datetime.now().time()
    # market_open = datetime.strptime(self.market_open, "%H:%M:%S").time()
    # new_buy_close = datetime.strptime(self.new_buy_close, "%H:%M:%S").time()
    # return market_open <= now <= new_buy_close
```

⚠️ **주의**: 실전 투자 전에 원래 코드로 되돌리세요!

---

### Q5: 매수는 되는데 매도가 안 됩니다.

**A**: 매도 조건을 확인하세요:
- 손실률 < 손절 기준 (-3%)
- 수익률 > 익절 기준 (+5%)
- 시간 > 15:10

조건이 충족되지 않으면 매도하지 않고 **보유(HOLD)**합니다.

포지션 모니터링 로그를 확인하세요:
```bash
grep "포지션 모니터링" logs/trading.log
```

---

## 📊 요약

### ✅ 매수 실행 조건 (모두 충족 필요)

1. ✅ AI Scan 실행 (10초 후 첫 실행, 이후 5분마다)
2. ✅ `test_mode: false` (실제 주문 실행 모드)
3. ✅ 거래 시간 (09:00~14:50, 평일)
4. ✅ Deep Scan 200점 이상
5. ✅ AI BUY 추천 (신뢰도 70%+, 확률 60%+)
6. ✅ 포지션 한도 미초과
7. ✅ 일일 손실 한도 미초과

### ✅ 매도 실행 조건 (하나만 충족하면 됨)

1. ✅ 손절: 손실 < -3%
2. ✅ 익절: 수익 > +5%
3. ✅ 장 마감: 시간 > 15:10

---

**문제 해결 순서**:

1. `python debug_trading.py` 실행
2. `python main.py` 실행
3. 10초 대기 (AI Scan 실행)
4. 로그 확인 (`tail -f logs/trading.log`)
5. 문제 발견 시 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 참고

---

**추가 지원**:
- GitHub Issues: https://github.com/pll2050/kiwoom_trading_claude/issues
- 문제 해결 가이드: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- 설치 가이드: [UBUNTU_INSTALL.md](UBUNTU_INSTALL.md)
