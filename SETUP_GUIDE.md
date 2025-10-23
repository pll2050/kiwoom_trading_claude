# 키움증권 자동 거래 시스템 - 설치 및 실행 가이드

## 📋 목차
1. [시스템 요구사항](#시스템-요구사항)
2. [설치 방법](#설치-방법)
3. [설정 방법](#설정-방법)
4. [테스트 실행](#테스트-실행)
5. [시스템 실행](#시스템-실행)
6. [문제 해결](#문제-해결)

---

## 시스템 요구사항

### 필수 요구사항
- **Python**: 3.8 이상
- **운영체제**: Windows 10/11 (권장), Linux, macOS
- **메모리**: 최소 4GB RAM
- **저장공간**: 최소 1GB

### API 요구사항
- 키움증권 API 계정 (앱 키, 앱 시크릿)
- Google Gemini API 키
- 키움증권 계좌번호 (모의투자 또는 실전 계좌)

---

## 설치 방법

### 1단계: 프로젝트 클론 또는 다운로드

```bash
# Git 사용 시
git clone <repository_url>
cd kiwoom_trading_claude

# 또는 ZIP 파일 다운로드 후 압축 해제
```

### 2단계: Python 패키지 설치

```bash
# 필수 패키지 설치
pip install loguru websockets aiohttp PyYAML google-generativeai python-dotenv ta

# pandas와 numpy는 이미 설치되어 있으면 스킵 가능
pip install pandas numpy
```

**설치 확인:**
```bash
python -c "import loguru, websockets, aiohttp, yaml, google.generativeai, ta; print('모든 패키지 설치 완료!')"
```

---

## 설정 방법

### 1. 키움증권 API 설정

1. 키움증권 OpenAPI 사이트에서 앱 키/시크릿 발급
2. `config/config.yaml` 파일 열기
3. 다음 정보 입력:

```yaml
kiwoom:
  app_key: "YOUR_KIWOOM_APP_KEY"           # 발급받은 앱 키
  app_secret: "YOUR_KIWOOM_APP_SECRET"     # 발급받은 앱 시크릿
  account_number: "YOUR_ACCOUNT_NUMBER"    # 계좌번호
  base_url: "https://openapi.koreainvestment.com:9443"
  websocket_url: "ws://ops.koreainvestment.com:21000"
```

### 2. Gemini API 설정

1. [Google AI Studio](https://makersuite.google.com/app/apikey)에서 API 키 발급
2. `config/config.yaml`에 입력:

```yaml
gemini:
  api_key: "YOUR_GEMINI_API_KEY"
  model: "gemini-1.5-pro-latest"
```

### 3. 거래 설정

`config/config.yaml`에서 투자 한도 설정:

```yaml
trading:
  max_investment_per_stock: 1000000  # 종목당 최대 100만원
  max_daily_loss: 500000             # 일일 최대 손실 50만원
  test_mode: true                    # 테스트 모드 (필수!)
```

### 4. 손절/익절 설정

`config/trading_rules.yaml`에서 조정:

```yaml
profit_loss:
  stop_loss_percentage: -3.0    # 손절: -3%
  take_profit_percentage: 5.0   # 익절: +5%

risk_management:
  max_positions: 10              # 최대 10개 종목 보유
```

---

## 테스트 실행

### 시스템 테스트

```bash
python test_system.py
```

**예상 결과:**
```
============================================================
테스트 결과 요약
============================================================
설정 파일: ✓ 통과
기술적 지표: ✓ 통과
점수 계산: ✓ 통과
거래 전략: ✓ 통과
Gemini AI: ✓ 통과
키움증권 API: ✗ 실패  # API 키가 올바르면 통과
============================================================
총 6개 중 5개 통과 (83.3%)
============================================================
```

**주의:** 키움증권 API 테스트는 실제 API 키가 필요합니다.

---

## 시스템 실행

### 1. 테스트 모드로 실행 (권장)

```bash
python main.py
```

**테스트 모드 특징:**
- 실제 주문 실행하지 않음
- 모든 로직은 정상 작동
- 매수/매도 신호만 로그로 출력
- 안전한 시뮬레이션

### 2. 실전 모드로 실행 (주의!)

⚠️ **실전 투자 전 필수 확인사항:**

1. **충분한 테스트**
   - 최소 1주일 이상 테스트 모드 실행
   - 모든 기능 정상 작동 확인
   - 손익 시뮬레이션 결과 확인

2. **설정 확인**
   - 투자 한도가 적절한지 확인
   - 손절/익절 비율 확인
   - 계좌 잔고 확인

3. **실전 모드 활성화**
   ```yaml
   trading:
     test_mode: false  # false로 변경
   ```

4. **시스템 실행**
   ```bash
   python main.py
   ```

### 실행 중 로그 확인

```bash
# 로그 파일 위치: logs/2025-01-21.log
tail -f logs/$(date +%Y-%m-%d).log
```

---

## 시스템 기능

### 자동 실행되는 기능

1. **Fast Scan (10초마다)**
   - 거래량/가격 기본 스크리닝
   - 상위 50개 종목 선별

2. **Deep Scan (1분마다)**
   - 외국인/기관 매매 분석
   - 10가지 기준 점수 계산
   - 200점 이상 종목 선별

3. **AI Scan (5분마다)**
   - Gemini AI 심층 분석
   - 매수 추천 종목 도출
   - 신뢰도 70% 이상만 선택

4. **실시간 모니터링**
   - WebSocket 현재가 수신
   - 포지션 손익 체크 (10초마다)
   - 자동 손절/익절 실행

5. **포트폴리오 요약 (5분마다)**
   - 총 포지션 수
   - 평가손익/실현손익
   - 수익률

---

## 문제 해결

### Q1: "ModuleNotFoundError: No module named 'loguru'"

**해결:**
```bash
pip install loguru websockets aiohttp PyYAML google-generativeai python-dotenv ta
```

### Q2: pandas 설치 오류 (Windows)

**해결:** 미리 컴파일된 버전 사용
```bash
pip install pandas --prefer-binary
```

### Q3: "토큰 발급 실패" 오류

**원인:**
- API 키가 잘못됨
- API 서버 연결 불가

**해결:**
1. `config/config.yaml`의 `app_key`, `app_secret` 확인
2. 키움증권 OpenAPI 사이트에서 API 상태 확인
3. 네트워크 연결 확인

### Q4: Gemini AI 모델 오류

**오류 메시지:**
```
404 models/gemini-1.5-pro-latest is not found
```

**해결:**
```yaml
gemini:
  model: "gemini-pro"  # 또는 "gemini-1.5-pro"
```

### Q5: 시스템이 주문을 실행하지 않음

**확인사항:**
1. `test_mode: false`로 설정되어 있는지 확인
2. 거래 시간인지 확인 (09:00~15:00)
3. 일일 손실 한도 초과 여부 확인
4. 최대 포지션 수 초과 여부 확인

### Q6: WebSocket 연결 오류

**해결:**
1. `websocket_url` 확인
2. 방화벽 설정 확인
3. 네트워크 프록시 설정 확인

---

## 로그 확인

### 로그 파일 위치
```
logs/
├── 2025-01-21.log  # 날짜별 로그
├── 2025-01-22.log
└── ...
```

### 주요 로그 메시지

**정상 작동:**
```
[INFO] 키움증권 REST API 클라이언트 초기화
[INFO] 토큰 발급 성공
[INFO] WebSocket 연결 성공
[INFO] Fast Scan 결과: 50개
[INFO] 매수 추천: 3개
```

**주의:**
```
[WARNING] 매수 불가 (삼성전자): 거래시간 외
[WARNING] 가격 정보 없음: SK하이닉스
```

**오류:**
```
[ERROR] API 오류: 401 Unauthorized
[ERROR] 매수 실패 (LG전자): Insufficient funds
```

---

## 안전 수칙

### 🔴 반드시 지켜야 할 사항

1. **테스트 모드 충분히 사용**
   - 최소 1주일 이상 테스트
   - 모든 상황 시뮬레이션

2. **소액으로 시작**
   - 처음엔 적은 금액으로 시작
   - 시스템 안정성 확인 후 증액

3. **일일 모니터링**
   - 최소 하루 1회 로그 확인
   - 비정상 동작 즉시 중단

4. **손실 한도 엄수**
   - `max_daily_loss` 적절히 설정
   - 한도 도달 시 자동 중단

5. **백업 및 기록**
   - 중요 설정 파일 백업
   - 거래 내역 별도 저장

---

## 지원

문제가 발생하면:
1. 로그 파일 확인 (`logs/`)
2. [CHANGELOG.md](CHANGELOG.md) 참조
3. [README.md](README.md) 문서 확인
4. GitHub Issues에 문의

---

## 면책 조항

⚠️ **중요:**
- 이 시스템은 교육 및 연구 목적으로 제작되었습니다
- 실제 투자 손실에 대해 책임지지 않습니다
- 투자의 최종 책임은 투자자 본인에게 있습니다
- AI의 판단이 항상 정확하지는 않습니다
- 충분한 테스트 없이 실전 투자하지 마세요

---

**설치 및 실행 가이드 v1.0**
마지막 업데이트: 2025-01-21
