# 키움증권 API 설정 가이드

## 📌 중요 공지

현재 테스트 환경에서 **키움증권 API 토큰 발급 실패**는 **정상적인 현상**입니다.

```
ERROR: 토큰 발급 실패
```

이 오류는 다음 이유로 발생합니다:
- Mock API URL이 실제 서버가 아님
- 실제 키움증권 API 키가 설정되지 않음

---

## 🔑 키움증권 API 키 발급 방법

### 1단계: 키움증권 계좌 개설

1. [키움증권 홈페이지](https://www.kiwoom.com) 방문
2. 비대면 계좌 개설 (모의투자 또는 실전 계좌)
3. 계좌 개설 완료 확인

### 2단계: KIS OpenAPI 신청

1. [한국투자증권 OpenAPI](https://apiportal.koreainvestment.com) 접속
   - 키움증권은 한국투자증권 OpenAPI를 사용합니다
2. 회원가입 및 로그인
3. **API 신청**:
   - 서비스 신청 > OpenAPI 신청
   - 앱 이름 입력 (예: "자동매매시스템")
   - 서비스 구분: REST API 선택

### 3단계: API 키 발급

신청 승인 후:
- **App Key** (앱 키) 발급
- **App Secret** (앱 시크릿) 발급

⚠️ **중요**: API 키는 절대 외부에 노출하지 마세요!

---

## ⚙️ 설정 파일 수정

### config/config.yaml 수정

```yaml
kiwoom:
  # 발급받은 실제 API 키로 교체
  app_key: "발급받은_앱_키를_여기에_입력"
  app_secret: "발급받은_앱_시크릿을_여기에_입력"

  # 계좌번호 (모의투자 계좌번호 권장)
  account_number: "12345678"  # 8자리 계좌번호

  # 실제 API URL (중요!)
  base_url: "https://openapi.koreainvestment.com:9443"
  websocket_url: "ws://ops.koreainvestment.com:21000"
```

### 모의투자 vs 실전투자

**모의투자 환경:**
```yaml
base_url: "https://openapivts.koreainvestment.com:9443"  # 모의투자
```

**실전투자 환경:**
```yaml
base_url: "https://openapi.koreainvestment.com:9443"     # 실전투자
```

---

## 🧪 API 키 없이 테스트하기

API 키가 없어도 대부분의 기능을 테스트할 수 있습니다:

### 1. 현재 테스트 상태 확인

```bash
python test_system.py
```

**예상 결과:**
```
총 6개 중 5개 통과 (83.3%)
- 설정 파일: ✓ 통과
- 기술적 지표: ✓ 통과
- 점수 계산: ✓ 통과
- 거래 전략: ✓ 통과
- Gemini AI: ✓ 통과
- 키움증권 API: ✗ 실패  ← 정상 (API 키 없음)
```

### 2. API 제외 기능 테스트

키움증권 API를 제외한 모든 기능이 정상 작동합니다:
- ✅ 기술적 지표 계산 (RSI, MACD 등)
- ✅ 점수 계산 시스템 (440점 만점)
- ✅ Gemini AI 분석
- ✅ 거래 전략 로직
- ✅ 포지션 관리

---

## 🔧 Mock API 서버 사용 (개발자용)

실제 API 없이 테스트하려면 Mock 서버를 만들 수 있습니다:

### 간단한 Mock 서버 만들기

`mock_server.py` 파일 생성:

```python
from aiohttp import web
import json

async def token_handler(request):
    """Mock 토큰 발급"""
    return web.json_response({
        "access_token": "mock_token_12345",
        "token_type": "Bearer",
        "expires_in": 86400
    })

async def balance_handler(request):
    """Mock 예수금 조회"""
    return web.json_response({
        "available_cash": 10000000,
        "total_asset": 15000000
    })

async def holdings_handler(request):
    """Mock 보유종목"""
    return web.json_response({
        "holdings": [
            {"stock_code": "005930", "stock_name": "삼성전자", "quantity": 10, "avg_price": 70000}
        ]
    })

app = web.Application()
app.router.add_post('/oauth2/token', token_handler)
app.router.add_get('/api/account/balance', balance_handler)
app.router.add_get('/api/account/holdings', holdings_handler)

if __name__ == '__main__':
    print("Mock API 서버 시작: http://localhost:8080")
    web.run_app(app, host='localhost', port=8080)
```

### Mock 서버 실행

```bash
# 터미널 1: Mock 서버 실행
python mock_server.py

# 터미널 2: config.yaml 수정
# base_url: "http://localhost:8080"

# 터미널 2: 테스트 실행
python test_system.py
```

---

## ✅ API 연결 확인 방법

### 1. 간단한 연결 테스트

```python
# test_api_connection.py
import asyncio
from src.kiwoom.rest_client import KiwoomRestClient
from src.utils.logger import logger

async def test():
    try:
        async with KiwoomRestClient() as client:
            logger.info(f"✓ 토큰 발급 성공: {client.access_token[:20]}...")

            balance = await client.get_balance()
            logger.info(f"✓ 예수금: {balance.get('available_cash', 0):,}원")

            print("🎉 API 연결 성공!")
    except Exception as e:
        print(f"❌ API 연결 실패: {e}")
        print("\n해결 방법:")
        print("1. config/config.yaml에서 API 키 확인")
        print("2. 키움증권 OpenAPI 사이트에서 키 재발급")
        print("3. base_url이 올바른지 확인")

asyncio.run(test())
```

실행:
```bash
python test_api_connection.py
```

### 2. 상세 로그 확인

```bash
# 로그 레벨을 DEBUG로 변경
# src/utils/logger.py 수정 또는 환경변수 설정

python main.py
```

---

## 📝 자주 묻는 질문 (FAQ)

### Q1: "토큰 발급 실패" 오류가 계속 발생해요

**A:** 다음을 확인하세요:
1. API 키가 올바른지 확인
2. `base_url`이 올바른지 확인
   - 모의투자: `https://openapivts.koreainvestment.com:9443`
   - 실전투자: `https://openapi.koreainvestment.com:9443`
3. 네트워크 연결 확인 (방화벽, 프록시)
4. API 사용 승인 여부 확인

### Q2: API 키 없이도 시스템을 사용할 수 있나요?

**A:** 일부 기능은 가능합니다:
- ✅ 기술적 지표 계산
- ✅ Gemini AI 분석
- ✅ 거래 전략 로직 테스트
- ❌ 실제 주문 실행 (API 필요)
- ❌ 계좌 정보 조회 (API 필요)

### Q3: 모의투자 계좌로 테스트할 수 있나요?

**A:** 네! 권장합니다.
1. 모의투자 계좌 개설
2. 모의투자 API 키 발급
3. `base_url`을 모의투자 URL로 설정

### Q4: 실전 투자 전에 뭘 확인해야 하나요?

**A:** 필수 체크리스트:
- [ ] 최소 1주일 이상 모의투자 테스트
- [ ] 모든 기능 정상 작동 확인
- [ ] 손절/익절 로직 검증
- [ ] 투자 한도 설정 확인
- [ ] 일일 손실 한도 설정
- [ ] `test_mode: false` 변경
- [ ] 소액으로 시작

---

## 🔒 보안 주의사항

### API 키 보호

1. **절대 공유하지 마세요**
   - GitHub에 업로드 금지
   - 스크린샷 공유 금지
   - 타인에게 공유 금지

2. **.gitignore 설정**
   ```
   config/config.yaml
   config/trading_rules.yaml
   *.log
   .env
   ```

3. **환경변수 사용 (선택)**
   ```bash
   # .env 파일
   KIWOOM_APP_KEY=your_app_key
   KIWOOM_APP_SECRET=your_app_secret
   ```

---

## 📞 지원

문제가 계속되면:
1. [키움증권 고객센터](https://www.kiwoom.com) 문의
2. [한국투자증권 OpenAPI 고객지원](https://apiportal.koreainvestment.com)
3. 프로젝트 GitHub Issues

---

## 📚 참고 문서

- [한국투자증권 OpenAPI 가이드](https://apiportal.koreainvestment.com/apiservice)
- [키움증권 공식 문서](https://www.kiwoom.com)
- [프로젝트 설치 가이드](SETUP_GUIDE.md)
- [변경 이력](CHANGELOG.md)

---

**현재 상태: API 키 없이도 83.3% 테스트 통과!** ✅

실제 거래를 위해서는 키움증권 API 키가 필요하지만,
핵심 로직과 알고리즘은 이미 정상 작동하고 있습니다.
