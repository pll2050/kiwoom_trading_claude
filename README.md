# 🤖 키움증권 AI 자동매매 시스템

> Gemini AI와 동적 리스크 관리를 갖춘 지능형 자동 주식 거래 시스템

## 📋 프로젝트 개요

키움증권 REST API와 WebSocket을 활용하여 **Gemini AI 기반 자동 증권거래 시스템**을 구축한 프로젝트입니다.

### 주요 기능

- ✅ **OAuth 인증** - 자동 토큰 발급 및 갱신
- ✅ **3단계 종목 스캐닝**
  - Fast Scan (10초): 거래량/가격 기본 스크리닝 → 50종목
  - Deep Scan (1분): 외국인/기관/호가 분석 → 20종목
  - AI Scan (5분): Gemini 심층 분석 → 5종목 매수 추천
- ✅ **10가지 평가 기준** - 440점 만점 스코어링 시스템
- ✅ **Gemini AI 분석** - 종목 상승 가능성 평가 및 매매 의사결정
- ✅ **자동 매매 실행** - 매수/매도 주문 자동 실행
- ✅ **동적 리스크 관리** - 원금 대비 잔고 비율에 따라 전략 자동 조정
- ✅ **실시간 모니터링** - 10초마다 계좌, 포지션, 손익 자동 조회
- ✅ **WebSocket 실시간** - 현재가, 체결, 잔고 실시간 수신

### 💼 동적 리스크 관리 (핵심 기능)

원금 대비 잔고 비율에 따라 자동으로 투자 전략을 조정합니다:

| 원금 대비 | 모드 | 최대 포지션 | 종목당 투자 | 손절/익절 | AI 신뢰도 |
|---------|------|----------|----------|---------|---------|
| **100% 이상** | 🚀 공격적 (수익) | 12개 | 6% | -2.5% / +7% | 70% |
| **90-100%** | ✅ 정상 | 10개 | 5% | -3% / +5% | 75% |
| **80-90%** | ⚠️ 보수적 | 7개 | 4% | -2% / +4% | 80% |
| **80% 미만** | 🛑 매우 보수적 | 5개 | 3% | -1.5% / +3% | 85% |

**💡 핵심 원리**
- 수익이 나면 더 공격적으로 투자
- 손실이 누적되면 자동으로 보수적 전환
- 원금을 보호하면서도 수익 기회를 놓치지 않음

## 🏗️ 프로젝트 구조

```
kiwoom_trading_claude/
├── config/                     # 설정 파일
│   ├── config.yaml            # API 키, 원금, 동적 리스크 관리 설정
│   ├── config.yaml.example    # 설정 파일 예제
│   ├── trading_rules.yaml     # 거래 규칙
│   └── scanning_rules.yaml    # 스캔 규칙
├── src/
│   ├── kiwoom/                # 키움증권 API
│   │   ├── rest_client.py     # REST API (Rate Limiting 포함)
│   │   └── websocket_client.py # WebSocket (LOGIN 인증)
│   ├── gemini/                # Gemini AI
│   │   └── ai_trader.py       # AI 종목 분석
│   ├── scanner/               # 종목 스캐닝
│   │   ├── stock_scanner.py   # 3단계 스캔 (Fast/Deep/AI)
│   │   └── scoring.py         # 10가지 기준 점수 계산
│   ├── strategy/              # 거래 전략
│   │   ├── trading_strategy.py       # 매수/매도 전략
│   │   └── dynamic_risk_manager.py   # 동적 리스크 관리 ⭐
│   ├── indicators/            # 기술적 지표
│   │   └── technical_indicators.py   # RSI, MACD, 이동평균
│   └── utils/                 # 유틸리티
│       ├── logger.py          # 로깅
│       └── config_loader.py   # 설정 로더
├── docs/                      # 문서
│   ├── KIWOOM_API_REFERENCE.md
│   ├── TRADING_PROCESS.md
│   └── STOCK_SCANNING_STRATEGY.md
├── main.py                    # 메인 실행 파일
├── requirements.txt
├── .gitignore
└── README.md
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 디렉토리 생성
mkdir logs
```

### 2. 설정 파일 수정

```bash
# 설정 파일 예제 복사
cp config/config.yaml.example config/config.yaml
```

`config/config.yaml` 파일을 열어 다음 정보를 입력하세요:

```yaml
kiwoom:
  app_key: "YOUR_KIWOOM_APP_KEY"
  app_secret: "YOUR_KIWOOM_APP_SECRET"
  account_number: "YOUR_ACCOUNT_NUMBER"

gemini:
  api_key: "YOUR_GEMINI_API_KEY"

trading:
  initial_capital: 500000000  # 초기 원금 (5억원)
  test_mode: true  # 실전 투자 시 false로 변경

  # 동적 리스크 관리
  dynamic_risk_management:
    enabled: true  # 활성화
```

### 3. 실행

```bash
python main.py
```

## 📊 스캐닝 시스템

### 10가지 평가 기준 (440점 만점)

1. **거래량 급증** (60점) - 전일 대비 300% 이상
2. **가격 급등락** (45점) - +3% 이상, 고가 근접
3. **외국인/기관** (70점) - 연속 순매수, 대량 매수
4. **호가 강도** (35점) - 매수호가 우위
5. **체결강도** (40점) - 120% 이상
6. **거래원** (30점) - 주요 증권사 순매수
7. **프로그램** (35점) - 프로그램 순매수
8. **기술적지표** (65점) - RSI, MACD, 이동평균
9. **테마/뉴스** (40점) - 핫 테마, 검색 급등
10. **VI 분석** (20점) - 변동성완화장치 패턴

### 등급 분류

- **S등급** (350점+): 매우 강력한 매수 신호
- **A등급** (280~349): 강력한 매수 신호
- **B등급** (200~279): 중간 매수 신호
- **C등급** (150~199): 약한 매수 신호

## 🤖 Gemini AI 분석

### 분석 항목

- 단기 상승 가능성 (%)
- 매수/매도/관망 추천
- 예상 목표가
- 리스크 수준
- 신뢰도 (0~1)
- 상세 분석 근거

### AI 의사결정 기준

- 신뢰도 70% 이상
- 상승 확률 60% 이상
- 리스크 레벨 MEDIUM 이하

## ⚙️ 설정

### trading_rules.yaml

```yaml
# 손절/익절
profit_loss:
  stop_loss_percentage: -3.0
  take_profit_percentage: 5.0

# 거래 시간
trading_hours:
  market_open: "09:00:00"
  new_buy_close: "15:00:00"
```

### scanning_rules.yaml

```yaml
# 스캔 주기
intervals:
  fast_scan: 10      # 10초
  deep_scan: 60      # 1분
  ai_analysis: 300   # 5분

# 필터링
filters:
  min_trading_value: 1000000000  # 10억
```

## 📝 로깅

로그는 `logs/` 디렉토리에 날짜별로 저장됩니다:

- 파일: `logs/2025-01-21.log`
- 로테이션: 10MB마다
- 보관: 최대 30개 파일

## 🔒 보안 주의사항

1. **API 키 보호**: `.gitignore`에 `config/*.yaml` 추가
2. **테스트 모드**: 실전 투자 전 충분한 테스트
3. **투자 한도**: 종목당/일일 최대 투자금액 설정
4. **손실 제한**: 손절가 필수 설정

## 📚 주요 문서

- [API 레퍼런스](docs/KIWOOM_API_REFERENCE.md) - 200개+ API 상세 정리
- [트레이딩 프로세스](docs/TRADING_PROCESS.md) - 전체 거래 흐름도
- [스캐닝 전략](docs/STOCK_SCANNING_STRATEGY.md) - 종목 발굴 시스템

## 🛠️ 기술 스택

- **Python 3.8+**
- **aiohttp** - 비동기 HTTP 클라이언트
- **google-generativeai** - Gemini API
- **PyYAML** - 설정 파일 파싱
- **loguru** - 로깅
- **pandas, numpy** - 데이터 처리
- **ta** - 기술적 지표

## ⚠️ 면책 조항

이 프로젝트는 교육 및 연구 목적으로 제작되었습니다. 실제 투자에 사용할 경우 발생하는 손실에 대해 책임지지 않습니다.

- 투자의 최종 책임은 투자자 본인에게 있습니다
- 충분한 테스트 없이 실전 투자하지 마세요
- AI의 판단이 항상 정확하지는 않습니다

## 📄 라이선스

MIT License

## 🤝 기여

이슈 및 Pull Request 환영합니다!

---

Made with ❤️ by Claude Code
