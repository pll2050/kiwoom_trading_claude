# 🔧 문제 해결 가이드

키움증권 AI 자동매매 시스템 사용 중 발생할 수 있는 문제와 해결 방법입니다.

## 📋 목차

1. [API 연결 오류](#api-연결-오류)
2. [인증 오류](#인증-오류)
3. [데이터 조회 오류](#데이터-조회-오류)
4. [주문 실행 오류](#주문-실행-오류)
5. [WebSocket 오류](#websocket-오류)
6. [기타 오류](#기타-오류)

---

## API 연결 오류

### ❌ `message='Attempt to decode JSON with unexpected mimetype: text/html'`

**에러 메시지 예시**:
```
2025-10-23 03:15:02.188 | ERROR | 토큰 발급 실패: 400,
message='Attempt to decode JSON with unexpected mimetype: text/html',
url='https://mockapi.kiwoom.com/oauth2/token'
```

**원인**:
Mock API 서버가 JSON 대신 HTML을 응답하고 있습니다. 다음 중 하나의 이유입니다:
1. Mock API 서버가 다운되었거나 점검 중
2. Mock API 서버가 더 이상 제공되지 않음
3. API 엔드포인트가 변경됨
4. URL이 잘못 설정됨

**해결 방법**:

#### 1단계: API 연결 테스트

```bash
# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows

# API 연결 테스트 실행
python test_api_connection.py
```

테스트 스크립트가 실제 서버 응답을 보여줍니다.

#### 2단계: config.yaml 수정 - 운영 API로 변경

**방법 A: Mock API 대신 운영 API 사용 (권장)**

```bash
nano config/config.yaml
```

다음과 같이 수정:

```yaml
kiwoom:
  app_key: "YOUR_ACTUAL_APP_KEY"
  app_secret: "YOUR_ACTUAL_APP_SECRET"
  account_number: "YOUR_ACCOUNT_NUMBER"

  # Mock API 주석 처리
  # base_url: "https://mockapi.kiwoom.com"
  # websocket_url: "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"

  # 운영 API 사용
  base_url: "https://api.kiwoom.com"
  websocket_url: "wss://api.kiwoom.com:10000/api/dostk/websocket"

trading:
  # ⚠️ 중요: 처음엔 반드시 테스트 모드로!
  test_mode: true
```

**⚠️ 주의사항**:
- 운영 API는 **실제 거래가 실행**됩니다!
- 반드시 `test_mode: true`로 설정하세요
- 실전 투자 전에 충분히 테스트하세요

**방법 B: 키움증권에 문의**

Mock API 서버 상태를 확인하세요:
- 키움증권 고객센터: 1544-5000
- OpenAPI 문의: https://www.kiwoom.com/h/customer/download/VOpenApiInfoView

#### 3단계: 재시작

```bash
# 프로그램 재시작
python main.py
```

---

### ❌ `Connection refused`, `Timeout`

**에러 메시지 예시**:
```
Cannot connect to host api.kiwoom.com:443 ssl:default
Connection refused
Timeout
```

**원인**:
1. 인터넷 연결 문제
2. 방화벽 차단
3. API 서버 다운

**해결 방법**:

#### 1. 네트워크 연결 확인

```bash
# 인터넷 연결 테스트
ping -c 4 8.8.8.8

# 키움증권 API 서버 연결 테스트
ping api.kiwoom.com

# DNS 확인
nslookup api.kiwoom.com
```

#### 2. 방화벽 확인 (Linux)

```bash
# UFW 상태 확인
sudo ufw status

# 아웃바운드 HTTPS 허용
sudo ufw allow out 443/tcp
```

#### 3. 프록시 설정 확인

프록시를 사용하는 경우:

```bash
# 환경변수 확인
echo $HTTP_PROXY
echo $HTTPS_PROXY

# 프록시 해제 (임시)
unset HTTP_PROXY
unset HTTPS_PROXY
```

#### 4. API 서버 상태 확인

```bash
# curl로 API 서버 접근 테스트
curl -I https://api.kiwoom.com

# 또는
curl -v https://api.kiwoom.com/oauth2/token
```

---

### ❌ `SSL: CERTIFICATE_VERIFY_FAILED`

**에러 메시지 예시**:
```
SSL: CERTIFICATE_VERIFY_FAILED
certificate verify failed: unable to get local issuer certificate
```

**원인**:
SSL 인증서 검증 실패

**해결 방법**:

#### Linux/Ubuntu

```bash
# CA 인증서 업데이트
sudo apt update
sudo apt install --reinstall ca-certificates -y

# Python certifi 재설치
pip install --upgrade certifi

# 시스템 시간 확인 (중요!)
date
# 시간이 잘못되었다면 수정
sudo timedatectl set-ntp true
```

#### Windows

```powershell
# certifi 재설치
pip install --upgrade certifi

# 시스템 시간 확인
Get-Date
```

#### MacOS

```bash
# 인증서 설치
/Applications/Python\ 3.11/Install\ Certificates.command

# 또는
pip install --upgrade certifi
```

---

## 인증 오류

### ❌ `401 Unauthorized`, `Invalid API Key`

**에러 메시지 예시**:
```
HTTP 401: Unauthorized
Invalid API Key
Access denied
```

**원인**:
1. API 키가 잘못됨
2. API 키가 만료됨
3. API 키 권한 부족

**해결 방법**:

#### 1. API 키 재확인

```bash
# config.yaml 확인
cat config/config.yaml | grep -A 3 "kiwoom:"
```

올바른 형식:
```yaml
kiwoom:
  app_key: "PSxxxxxxxxxxxxxxxxxxxxxx"
  app_secret: "xxxxxxxxxxxxxxxxxx"
  account_number: "12345678901"
```

#### 2. API 키 재발급

1. 키움증권 OpenAPI 홈페이지 접속
2. API 키 관리 메뉴
3. 기존 키 삭제 후 신규 발급
4. `config/config.yaml`에 새 키 입력

#### 3. API 키 권한 확인

키움증권 API 관리 페이지에서:
- 국내주식 권한 확인
- 계좌 조회 권한 확인
- 주문 권한 확인

---

### ❌ `403 Forbidden`

**에러 메시지 예시**:
```
HTTP 403: Forbidden
IP not allowed
```

**원인**:
IP 주소 화이트리스트 미등록

**해결 방법**:

#### 1. 현재 IP 확인

```bash
# 외부 IP 확인
curl ifconfig.me
# 또는
curl ipinfo.io/ip
```

#### 2. 키움증권 API 설정에 IP 등록

1. 키움증권 OpenAPI 관리 페이지 접속
2. IP 화이트리스트에 서버 IP 추가
3. 설정 저장 후 5-10분 대기

#### 3. 재시도

```bash
python main.py
```

---

## 데이터 조회 오류

### ❌ `Rate limit exceeded`, `429 Too Many Requests`

**에러 메시지 예시**:
```
HTTP 429: Too Many Requests
Rate limit exceeded
초당 요청 제한 초과
```

**원인**:
API 호출 빈도 제한 초과 (키움증권: 초당 1회)

**해결 방법**:

#### 1. 설정 파일 확인

프로그램이 자동으로 1초 간격을 유지하도록 설계되어 있습니다.

```python
# src/kiwoom/rest_client.py에서 자동 처리
await asyncio.sleep(1)  # 1초 대기
```

#### 2. 수동 지연 추가 (필요시)

`config/scanning_rules.yaml`:

```yaml
scanning:
  intervals:
    fast_scan: 300      # 5분 (300초)
    deep_scan: 600      # 10분 (600초)
    ai_analysis: 900    # 15분 (900초)
```

간격을 늘려서 API 호출 빈도를 줄이세요.

#### 3. 재시도 로직 확인

프로그램은 429 에러 시 자동으로 재시도합니다:

```python
# 최대 3회 재시도
# 각 재시도 사이 1초 대기
```

---

### ❌ `Empty response`, `No data returned`

**에러 메시지 예시**:
```
Empty response from API
No holdings found
```

**원인**:
1. 장 마감 후 데이터 조회
2. 계좌에 실제 데이터 없음
3. API 권한 문제

**해결 방법**:

#### 1. 거래 시간 확인

```python
# 한국 증시 거래 시간
09:00 - 15:30 (평일만)
```

장 중에만 실시간 데이터가 업데이트됩니다.

#### 2. 계좌 상태 확인

키움증권 HTS/MTS에서:
- 계좌 잔고 확인
- 보유 종목 확인
- 예수금 확인

#### 3. API 응답 로그 확인

```bash
# 로그에서 API 응답 확인
tail -f logs/trading.log | grep "API 응답"
```

---

## 주문 실행 오류

### ❌ `Order rejected`, `Insufficient funds`

**에러 메시지 예시**:
```
주문 거부: 잔고 부족
Insufficient funds
매수 가능 금액 초과
```

**원인**:
1. 예수금 부족
2. `max_investment_per_stock` 설정 과다
3. 계좌 출금 가능액 부족

**해결 방법**:

#### 1. 예수금 확인

```bash
# 프로그램 실행 로그에서 확인
grep "예수금" logs/trading.log
```

#### 2. 투자 금액 조정

`config/config.yaml`:

```yaml
trading:
  initial_capital: 500000000      # 5억원
  max_investment_per_stock: 25000000  # 2,500만원 (5%)

  # 예수금이 1억원이라면:
  max_investment_per_stock: 10000000  # 1,000만원 (10%)
```

#### 3. 동적 리스크 관리 확인

프로그램이 자동으로 예수금 내에서 투자합니다:

```python
# 현재 자본금 기준으로 포지션 크기 계산
qty = risk_manager.calculate_position_size(current_capital, price)
```

---

### ❌ `Order timeout`

**에러 메시지 예시**:
```
주문 타임아웃
Order execution timeout
```

**원인**:
1. 네트워크 지연
2. API 서버 응답 지연
3. 거래량 과다로 체결 지연

**해결 방법**:

#### 1. 타임아웃 설정 늘리기

`src/kiwoom/rest_client.py`:

```python
# 현재: 120초 (2분)
timeout = aiohttp.ClientTimeout(total=120)

# 늘리기: 300초 (5분)
timeout = aiohttp.ClientTimeout(total=300)
```

#### 2. 주문 방식 변경

지정가 → 시장가:

```python
# 시장가 주문 (즉시 체결)
result = await self.api_client.order_buy(
    code, qty, price, order_type="market"
)
```

#### 3. 네트워크 확인

```bash
# API 서버 응답 시간 측정
time curl -I https://api.kiwoom.com
```

---

## WebSocket 오류

### ❌ `WebSocket connection failed`

**에러 메시지 예시**:
```
WebSocket connection failed
Connection closed unexpectedly
```

**원인**:
1. WebSocket URL 잘못됨
2. 인증 토큰 만료
3. 네트워크 불안정

**해결 방법**:

#### 1. WebSocket URL 확인

`config/config.yaml`:

```yaml
kiwoom:
  websocket_url: "wss://api.kiwoom.com:10000/api/dostk/websocket"
```

#### 2. 로그인 인증 확인

WebSocket은 REST API 토큰으로 로그인 필요:

```python
# 자동 로그인
await self.ws_client.login()
```

#### 3. 재연결 로직

프로그램이 자동으로 재연결을 시도합니다:

```python
# 연결 끊김 시 5초 후 재연결
await asyncio.sleep(5)
await self.ws_client.reconnect()
```

---

### ❌ `Subscription failed`

**에러 메시지 예시**:
```
구독 실패
Subscription rejected
```

**원인**:
1. 로그인 안 함
2. 잘못된 종목 코드
3. 구독 한도 초과

**해결 방법**:

#### 1. 로그인 상태 확인

```python
# WebSocket 로그인 후 구독
await ws_client.login()
await ws_client.subscribe_current_price(stock_code)
```

#### 2. 종목 코드 검증

```python
# 6자리 숫자
stock_code = "005930"  # 삼성전자 (올바름)
stock_code = "005930.KS"  # 잘못됨
```

#### 3. 구독 수 제한

동시 구독 가능한 종목 수를 확인하고 제한하세요.

---

## 기타 오류

### ❌ `MemoryError`, 시스템 멈춤

**원인**:
메모리 부족

**해결 방법**:

#### Linux/Ubuntu

```bash
# 현재 메모리 확인
free -h

# 스왑 메모리 추가 (2GB)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 적용
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### Windows

작업 관리자에서 메모리 사용량 확인 후:
- 불필요한 프로그램 종료
- 가상 메모리 늘리기

---

### ❌ `ModuleNotFoundError`, `ImportError`

**에러 메시지 예시**:
```
ModuleNotFoundError: No module named 'aiohttp'
ImportError: cannot import name 'xxx'
```

**원인**:
Python 패키지 미설치 또는 버전 불일치

**해결 방법**:

```bash
# 가상환경 활성화 확인
which python3
# /path/to/kiwoom_trading_claude/venv/bin/python3 이어야 함

# 가상환경 활성화
source venv/bin/activate

# 패키지 재설치
pip install -r requirements.txt

# 특정 패키지 재설치
pip install --upgrade aiohttp

# 캐시 삭제 후 재설치
pip cache purge
pip install -r requirements.txt
```

---

### ❌ `Permission denied`

**에러 메시지 예시**:
```
Permission denied: 'config/config.yaml'
Permission denied: 'logs/trading.log'
```

**원인**:
파일/디렉토리 권한 문제

**해결 방법**:

```bash
# 프로젝트 디렉토리 소유권 변경
sudo chown -R $USER:$USER ~/kiwoom_trading_claude

# 실행 권한 부여
chmod +x main.py

# 로그 디렉토리 권한
chmod 755 logs/
```

---

## 💡 일반적인 문제 해결 순서

문제가 발생하면 다음 순서로 확인하세요:

### 1. 로그 확인
```bash
# 최근 로그 확인
tail -n 100 logs/trading.log

# 에러 로그만 필터링
grep ERROR logs/trading.log

# 실시간 로그
tail -f logs/trading.log
```

### 2. 설정 파일 검증
```bash
# YAML 문법 확인
python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# API 키 확인
cat config/config.yaml | grep -A 5 "kiwoom:"
```

### 3. 네트워크 테스트
```bash
# API 연결 테스트
python test_api_connection.py

# 네트워크 확인
ping api.kiwoom.com
```

### 4. 재시작
```bash
# 프로그램 종료
Ctrl+C

# 가상환경 재활성화
source venv/bin/activate

# 재시작
python main.py
```

### 5. 클린 재설치
```bash
# 가상환경 삭제
rm -rf venv

# 재생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 재시작
python main.py
```

---

## 🆘 추가 지원

위 방법으로 해결되지 않으면:

1. **GitHub Issues**: https://github.com/pll2050/kiwoom_trading_claude/issues
   - 에러 로그 첨부
   - 실행 환경 정보 (OS, Python 버전)
   - 재현 방법 설명

2. **키움증권 고객센터**
   - 전화: 1544-5000
   - OpenAPI 전용: https://www.kiwoom.com

3. **로그 수집**
   ```bash
   # 전체 로그 저장
   python main.py > full_log.txt 2>&1

   # 시스템 정보
   python --version
   pip list
   uname -a  # Linux
   ```

---

**문제가 해결되길 바랍니다! 🎉**
