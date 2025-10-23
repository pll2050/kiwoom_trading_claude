# 키움증권 자동 증권거래 시스템 - 프로젝트 요구사항

## 프로젝트 개요
키움증권 REST API와 WebSocket을 활용하여 Gemini AI와 연동한 자동 증권거래 시스템 구축

## 기술 스택
- Python 3.8+
- 키움증권 REST API
- WebSocket (실시간 시세 데이터)
- Google Gemini API
- asyncio (비동기 처리)

## 프로젝트 구조
```
kiwoom_trading_claude/
├── config/
│   ├── config.yaml          # API 키, 설정값
│   ├── trading_rules.yaml   # 거래 규칙 설정
│   └── scanning_rules.yaml  # 종목 스캐닝 설정
├── src/
│   ├── kiwoom/
│   │   ├── __init__.py
│   │   ├── rest_client.py   # REST API 클라이언트
│   │   └── websocket_client.py  # WebSocket 클라이언트
│   ├── gemini/
│   │   ├── __init__.py
│   │   └── ai_trader.py     # Gemini AI 트레이딩 로직
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── stock_scanner.py # 종목 스캐닝 엔진
│   │   ├── scoring.py       # 점수 계산 시스템
│   │   └── indicators.py    # 기술적 지표 계산
│   ├── strategy/
│   │   ├── __init__.py
│   │   └── trading_strategy.py  # 거래 전략
│   └── utils/
│       ├── __init__.py
│       └── logger.py        # 로깅 유틸리티
├── helper/
│   ├── __init__.py
│   └── pdf_reader.py        # PDF 읽기 유틸
├── docs/
│   ├── KIWOOM_API_REFERENCE.md    # API 레퍼런스
│   ├── TRADING_PROCESS.md         # 트레이딩 프로세스
│   └── STOCK_SCANNING_STRATEGY.md # 스캐닝 전략
├── main.py                  # 메인 실행 파일
├── requirements.txt
└── README.md
```

## 주요 기능 요구사항

### 1. 키움증권 REST API 연동 (src/kiwoom/rest_client.py)

#### 1.1 OAuth 인증
- au10001: 접근토큰 발급
- au10002: 접근토큰 폐기

#### 1.2 계좌 조회 기능
**예수금/자산 조회**
- kt00001: 예수금상세현황 조회
- kt00003: 추정자산 조회
- kt00010: 주문인출가능금액 조회

**잔고/보유종목 조회**
- kt00005: 체결잔고 조회
- kt00018: 계좌평가잔고내역 조회
- kt00004: 계좌평가현황 조회

**수익률 조회**
- ka01690: 일별잔고수익률 조회
- ka10085: 계좌수익률 조회
- kt00016: 일별계좌수익률상세현황 조회
- ka10072: 일자별종목별실현손익 조회(일자)
- ka10073: 일자별종목별실현손익 조회(기간)
- ka10074: 일자별실현손익 조회
- ka10077: 당일실현손익상세 조회

**주문/체결 조회**
- ka10075: 미체결 조회
- ka10076: 체결 조회
- ka10088: 미체결 분할주문 상세 조회
- kt00007: 계좌별주문체결내역상세 조회
- kt00009: 계좌별주문체결현황 조회

#### 1.3 주식 주문 기능
- 매수/매도 주문 실행
- 주문 정정/취소
- 주문 가능 수량 조회

#### 1.4 시세 조회 기능
- ka10004: 주식호가 조회
- ka10005: 주식일주월시분 조회
- ka10079-10083: 차트 조회 (틱/분봉/일봉/주봉/월봉)
- 실시간 시세 조회

#### 1.5 공통 기능
- 에러 핸들링 및 재시도 로직
- API 호출 속도 제한 관리
- 응답 데이터 검증

### 2. WebSocket 실시간 데이터 수신 (src/kiwoom/websocket_client.py)
- 실시간 주가 데이터 수신
- 실시간 체결 정보 수신
- 호가 정보 수신
- 자동 재연결 기능
- 데이터 큐 관리

### 3. 종목 스캐닝 시스템 (src/scanner/)

#### 3.1 스캐닝 엔진 (stock_scanner.py)
- Fast Scan: 10초마다 거래량/가격 기본 스크리닝
- Deep Scan: 1분마다 외국인/기관/호가 상세 분석
- AI Scan: 5분마다 Gemini 심층 분석

#### 3.2 점수 계산 시스템 (scoring.py)
**10가지 평가 기준** (총 440점 만점)
- 거래량 급증 (60점): 전일대비 300% 이상
- 가격 급등락 (45점): +3% 이상, 고가 근접
- 외국인/기관 (70점): 연속 순매수, 대량 매수
- 호가 강도 (35점): 매수호가 우위
- 체결강도 (40점): 120% 이상
- 거래원 (30점): 주요 증권사 순매수
- 프로그램 (35점): 프로그램 순매수
- 기술적지표 (65점): RSI, MACD, 이동평균
- 테마/뉴스 (40점): 핫 테마, 검색 급등
- VI 분석 (20점): 변동성완화장치 패턴

**등급 분류**
- S등급 (350점+): 매우 강력한 매수 신호
- A등급 (280~349): 강력한 매수 신호
- B등급 (200~279): 중간 매수 신호
- C등급 (150~199): 약한 매수 신호

#### 3.3 기술적 지표 계산 (indicators.py)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- 이동평균선 (5일/20일/60일/120일)
- 볼린저밴드
- 스토캐스틱
- 거래량 이동평균

### 4. Gemini AI 트레이딩 로직 (src/gemini/ai_trader.py)
- 시장 데이터 분석
- 스캐닝 결과 심층 분석
- 매수/매도 결정
- 리스크 관리
- 포트폴리오 최적화
- 프롬프트 엔지니어링으로 안전한 거래 로직 구현

### 5. 거래 전략 (src/strategy/trading_strategy.py)
- 스캐닝 결과 기반 매매 전략
- 매수/매도 신호 생성
- 손절/익절 로직
- 포지션 크기 계산

### 6. 메인 실행 로직 (main.py)
- 종목 스캐닝 시스템 통합
- 비동기 이벤트 루프
- 실시간 데이터 모니터링
- AI 의사결정 및 주문 실행
- 로깅 및 모니터링

## 보안 고려사항
- API 키는 환경변수 또는 암호화된 설정 파일에 저장
- 거래 금액 제한 설정
- 손실 제한 (stop-loss) 필수 구현
- 테스트 모드 / 실전 모드 분리

## 설정 파일 예시

### config/config.yaml
```yaml
kiwoom:
  app_key: "YOUR_APP_KEY"
  app_secret: "YOUR_APP_SECRET"
  account_number: "YOUR_ACCOUNT"
  base_url: "https://openapi.koreainvestment.com:9443"
  websocket_url: "ws://ops.koreainvestment.com:21000"

gemini:
  api_key: "YOUR_GEMINI_API_KEY"
  model: "gemini-pro"

trading:
  max_investment_per_stock: 1000000  # 종목당 최대 투자금액 (원)
  max_daily_loss: 500000             # 일일 최대 손실 한도 (원)
  test_mode: true                    # 테스트 모드 활성화
```

## 개발 우선순위
1. 기본 프로젝트 구조 및 설정 파일 생성
2. 키움증권 REST API 클라이언트 구현
3. WebSocket 클라이언트 구현
4. Gemini AI 연동
5. 거래 전략 및 메인 로직 통합
6. 테스트 및 검증
