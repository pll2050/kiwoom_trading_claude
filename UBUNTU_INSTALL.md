# 🐧 우분투 서버 설치 가이드

키움증권 AI 자동매매 시스템을 우분투 서버에 설치하는 방법을 안내합니다.

## 📋 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [사전 준비](#사전-준비)
3. [설치 과정](#설치-과정)
4. [설정](#설정)
5. [실행](#실행)
6. [시스템 서비스 등록](#시스템-서비스-등록)
7. [모니터링](#모니터링)
8. [문제 해결](#문제-해결)

---

## 시스템 요구사항

### 최소 사양
- **OS**: Ubuntu 20.04 LTS 이상
- **CPU**: 2 Core 이상
- **RAM**: 4GB 이상
- **Storage**: 20GB 이상
- **Network**: 안정적인 인터넷 연결 필수

### 권장 사양
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 4 Core 이상
- **RAM**: 8GB 이상
- **Storage**: 50GB 이상 (SSD 권장)
- **Network**: 100Mbps 이상

---

## 사전 준비

### 1. API 키 발급

설치하기 전에 다음 API 키를 준비하세요:

- **키움증권 API**
  - 앱 키 (App Key)
  - 앱 시크릿 (App Secret)
  - 계좌번호
  - 발급: [키움증권 OpenAPI 홈페이지](https://www.kiwoom.com/h/customer/download/VOpenApiInfoView)

- **Google Gemini API**
  - API 키
  - 발급: [Google AI Studio](https://makersuite.google.com/app/apikey)

### 2. 서버 접속

```bash
ssh username@your-server-ip
```

---

## 설치 과정

### 1단계: 시스템 업데이트

```bash
# 패키지 목록 업데이트
sudo apt update

# 시스템 패키지 업그레이드
sudo apt upgrade -y
```

### 2단계: Python 3.11+ 설치

우분투 22.04는 Python 3.10이 기본이므로 3.11+를 설치합니다.

```bash
# Python 설치 확인
python3 --version

# Python 3.11 설치 (Ubuntu 22.04+)
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# pip 설치
sudo apt install python3-pip -y

# Python 3.11을 기본으로 설정 (선택사항)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

또는 deadsnakes PPA 사용 (Ubuntu 20.04):

```bash
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y
```

### 3단계: Git 설치

```bash
sudo apt install git -y
git --version
```

### 4단계: 필수 시스템 패키지 설치

```bash
# 빌드 도구 설치
sudo apt install build-essential -y

# SSL/TLS 라이브러리
sudo apt install libssl-dev libffi-dev -y

# 기타 유틸리티
sudo apt install curl wget vim tmux htop -y
```

### 5단계: 프로젝트 클론

```bash
# 홈 디렉토리로 이동
cd ~

# 프로젝트 클론
git clone https://github.com/pll2050/kiwoom_trading_claude.git

# 프로젝트 디렉토리로 이동
cd kiwoom_trading_claude
```

### 6단계: Python 가상환경 생성

```bash
# 가상환경 생성
python3.11 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip
```

### 7단계: Python 패키지 설치

```bash
# requirements.txt에서 패키지 설치
pip install -r requirements.txt

# 설치 확인
pip list
```

예상 설치 시간: 3-5분

---

## 설정

### 1단계: 설정 파일 생성

```bash
# 설정 파일 복사
cp config/config.yaml.example config/config.yaml

# 권한 설정 (중요: 다른 사용자가 못 보게)
chmod 600 config/config.yaml
```

### 2단계: API 키 설정

```bash
# nano 또는 vim으로 설정 파일 편집
nano config/config.yaml
```

**필수 수정 항목**:

```yaml
kiwoom:
  app_key: "YOUR_KIWOOM_APP_KEY"          # ← 키움 앱 키 입력
  app_secret: "YOUR_KIWOOM_APP_SECRET"    # ← 키움 앱 시크릿 입력
  account_number: "YOUR_ACCOUNT_NUMBER"   # ← 계좌번호 입력

gemini:
  api_key: "YOUR_GEMINI_API_KEY"          # ← Gemini API 키 입력

trading:
  initial_capital: 500000000              # ← 초기 투자금 (5억원)
  max_investment_per_stock: 25000000     # ← 종목당 최대 투자 (2,500만원)
  test_mode: true                        # ← 처음엔 true로 테스트 (실전: false)
```

**저장 및 종료**:
- nano: `Ctrl+X` → `Y` → `Enter`
- vim: `Esc` → `:wq` → `Enter`

### 3단계: 설정 검증

```bash
# 설정 파일 문법 체크
python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# 에러가 없으면 OK!
```

---

## 실행

### 방법 1: 직접 실행 (테스트용)

```bash
# 가상환경 활성화 (비활성화되었을 경우)
source venv/bin/activate

# 프로그램 실행
python3 main.py

# 중지: Ctrl+C
```

### 방법 2: tmux를 이용한 백그라운드 실행

```bash
# tmux 세션 생성
tmux new -s trading_clause

# 가상환경 활성화
source venv/bin/activate

# 프로그램 실행
python3 main.py

# tmux에서 나가기 (프로그램은 계속 실행)
# Ctrl+B 누른 후 D

# tmux 세션 다시 들어가기
tmux attach -t trading_clause

# tmux 세션 종료
tmux kill-session -t trading_clause
```

### 방법 3: nohup을 이용한 백그라운드 실행

```bash
# 가상환경 활성화
source venv/bin/activate

# 백그라운드 실행 (로그는 nohup.out에 저장)
nohup python3 main.py > trading_clause.log 2>&1 &

# PID 확인
echo $!

# 실행 중인 프로세스 확인
ps aux | grep main.py

# 프로세스 종료 (PID는 위에서 확인)
kill <PID>
```

### 방법 4: screen을 이용한 실행

```bash
# screen 설치
sudo apt install screen -y

# screen 세션 생성
screen -S trading

# 가상환경 활성화 및 실행
source venv/bin/activate
python3 main.py

# screen에서 나가기: Ctrl+A 누른 후 D
# screen 다시 들어가기: screen -r trading
# screen 종료: exit 또는 Ctrl+D
```

---

## 시스템 서비스 등록

프로그램을 시스템 서비스로 등록하면 서버 재부팅 시 자동으로 시작됩니다.

### 1단계: 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/kiwoom-trading.service
```

**파일 내용**:

```ini
[Unit]
Description=Kiwoom AI Trading System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/kiwoom_trading_claude
Environment="PATH=/home/your-username/kiwoom_trading_claude/venv/bin"
ExecStart=/home/your-username/kiwoom_trading_claude/venv/bin/python3 main.py

# 재시작 정책
Restart=on-failure
RestartSec=10s

# 로그 설정
StandardOutput=append:/home/your-username/kiwoom_trading_claude/logs/trading.log
StandardError=append:/home/your-username/kiwoom_trading_claude/logs/error.log

# 보안 설정
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**⚠️ 주의**: `your-username`을 실제 사용자명으로 변경하세요!

```bash
# 사용자명 확인
whoami

# 홈 디렉토리 확인
echo $HOME
```

### 2단계: 로그 디렉토리 생성

```bash
mkdir -p ~/kiwoom_trading_claude/logs
```

### 3단계: 서비스 등록 및 시작

```bash
# systemd 설정 리로드
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable kiwoom-trading.service

# 서비스 시작
sudo systemctl start kiwoom-trading.service

# 서비스 상태 확인
sudo systemctl status kiwoom-trading.service
```

### 4단계: 서비스 관리 명령어

```bash
# 시작
sudo systemctl start kiwoom-trading

# 중지
sudo systemctl stop kiwoom-trading

# 재시작
sudo systemctl restart kiwoom-trading

# 상태 확인
sudo systemctl status kiwoom-trading

# 로그 확인
sudo journalctl -u kiwoom-trading -f

# 자동 시작 비활성화
sudo systemctl disable kiwoom-trading
```

---

## 모니터링

### 실시간 로그 확인

```bash
# 서비스 로그
sudo journalctl -u kiwoom-trading -f

# 파일 로그 (설정한 경우)
tail -f ~/kiwoom_trading_claude/logs/trading.log

# 에러 로그
tail -f ~/kiwoom_trading_claude/logs/error.log
```

### 시스템 리소스 모니터링

```bash
# CPU, 메모리 사용량
htop

# 디스크 사용량
df -h

# 네트워크 연결 상태
netstat -tulpn | grep python

# 프로세스 확인
ps aux | grep python
```

### 로그 파일 크기 관리

로그가 계속 쌓이므로 logrotate를 설정하세요:

```bash
sudo nano /etc/logrotate.d/kiwoom-trading
```

**파일 내용**:

```
/home/your-username/kiwoom_trading_claude/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0640 your-username your-username
}
```

```bash
# logrotate 테스트
sudo logrotate -f /etc/logrotate.d/kiwoom-trading
```

---

## 문제 해결

### 1. Python 패키지 설치 오류

**증상**: `pip install` 시 에러 발생

**해결**:
```bash
# pip 업그레이드
pip install --upgrade pip setuptools wheel

# 캐시 삭제 후 재설치
pip cache purge
pip install -r requirements.txt
```

### 2. SSL 인증서 오류

**증상**: `SSL: CERTIFICATE_VERIFY_FAILED`

**해결**:
```bash
# ca-certificates 업데이트
sudo apt install --reinstall ca-certificates -y

# Python certifi 재설치
pip install --upgrade certifi
```

### 3. 메모리 부족

**증상**: `MemoryError` 또는 프로그램 강제 종료

**해결**:
```bash
# 스왑 메모리 추가 (2GB 예시)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 적용
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 확인
free -h
```

### 4. 포트 충돌

**증상**: `Address already in use`

**해결**:
```bash
# 포트 사용 프로세스 확인 (예: 8000번 포트)
sudo lsof -i :8000

# 프로세스 종료
sudo kill -9 <PID>
```

### 5. 권한 오류

**증상**: `Permission denied`

**해결**:
```bash
# 프로젝트 디렉토리 소유권 변경
sudo chown -R $USER:$USER ~/kiwoom_trading_claude

# 실행 권한 부여
chmod +x ~/kiwoom_trading_claude/main.py
```

### 6. 가상환경 활성화 안됨

**증상**: `(venv)` 프롬프트가 안 보임

**해결**:
```bash
# 가상환경 삭제 후 재생성
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 7. 서비스가 자동 시작 안됨

**증상**: 서버 재부팅 후 서비스 미실행

**해결**:
```bash
# 서비스 상태 확인
sudo systemctl status kiwoom-trading

# enable 상태 확인
sudo systemctl is-enabled kiwoom-trading

# 활성화
sudo systemctl enable kiwoom-trading

# 설정 파일 검증
sudo systemd-analyze verify kiwoom-trading.service
```

### 8. API 연결 오류

**증상**: `Connection refused`, `Timeout`

**해결**:
```bash
# 네트워크 연결 확인
ping -c 4 8.8.8.8

# DNS 확인
nslookup api.kiwoom.com

# 방화벽 확인 (UFW 사용 시)
sudo ufw status

# 아웃바운드 연결 허용
sudo ufw allow out 443/tcp
```

---

## 보안 권장사항

### 1. 설정 파일 보호

```bash
# config.yaml 권한 설정 (본인만 읽기/쓰기)
chmod 600 config/config.yaml

# logs 디렉토리 권한
chmod 700 logs/
```

### 2. 방화벽 설정

```bash
# UFW 설치 및 활성화
sudo apt install ufw -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable

# 상태 확인
sudo ufw status
```

### 3. SSH 보안

```bash
# SSH 포트 변경 (예: 22 → 2222)
sudo nano /etc/ssh/sshd_config
# Port 2222

# SSH 재시작
sudo systemctl restart sshd
```

### 4. 자동 업데이트 설정

```bash
# unattended-upgrades 설치
sudo apt install unattended-upgrades -y

# 활성화
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## 업데이트

### 코드 업데이트

```bash
cd ~/kiwoom_trading_claude

# 변경사항 확인
git status

# 최신 코드 가져오기
git pull origin main

# 패키지 업데이트
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 서비스 재시작
sudo systemctl restart kiwoom-trading
```

### Python 패키지 업데이트

```bash
source venv/bin/activate

# 모든 패키지 업데이트
pip list --outdated
pip install --upgrade <package_name>

# requirements.txt 업데이트
pip freeze > requirements.txt
```

---

## 유용한 명령어 모음

```bash
# 프로젝트 디렉토리로 빠르게 이동
echo "alias trading='cd ~/kiwoom_trading_claude && source venv/bin/activate'" >> ~/.bashrc
source ~/.bashrc

# 이제 어디서든 'trading' 명령으로 이동 가능
trading

# 로그 실시간 확인 (컬러 적용)
alias trading-log='sudo journalctl -u kiwoom-trading -f --no-pager'

# 서비스 상태 빠른 확인
alias trading-status='sudo systemctl status kiwoom-trading'

# 서비스 재시작
alias trading-restart='sudo systemctl restart kiwoom-trading'
```

---

## 성능 최적화

### 1. Python 최적화

```bash
# 가상환경 활성화
source venv/bin/activate

# 최적화 모드로 실행 (-O 옵션)
python3 -O main.py
```

### 2. 시스템 최적화

```bash
# CPU governor 설정 (성능 우선)
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 영구 적용
sudo apt install cpufrequtils -y
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils
```

### 3. 네트워크 최적화

```bash
# TCP 파라미터 조정
sudo sysctl -w net.ipv4.tcp_keepalive_time=60
sudo sysctl -w net.ipv4.tcp_keepalive_intvl=10
sudo sysctl -w net.ipv4.tcp_keepalive_probes=6

# 영구 적용
sudo nano /etc/sysctl.conf
# 다음 추가:
# net.ipv4.tcp_keepalive_time=60
# net.ipv4.tcp_keepalive_intvl=10
# net.ipv4.tcp_keepalive_probes=6

sudo sysctl -p
```

---

## 백업 및 복구

### 백업

```bash
# 설정 파일 백업
cp config/config.yaml config/config.yaml.backup.$(date +%Y%m%d)

# 전체 프로젝트 백업 (로그 제외)
cd ~
tar -czf kiwoom_trading_backup_$(date +%Y%m%d).tar.gz \
    --exclude='kiwoom_trading_claude/venv' \
    --exclude='kiwoom_trading_claude/logs' \
    --exclude='kiwoom_trading_claude/__pycache__' \
    kiwoom_trading_claude/

# 백업 파일 확인
ls -lh kiwoom_trading_backup_*.tar.gz
```

### 복구

```bash
# 백업 파일 압축 해제
tar -xzf kiwoom_trading_backup_YYYYMMDD.tar.gz

# 가상환경 재생성
cd kiwoom_trading_claude
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 지원

문제가 발생하면:

1. **GitHub Issues**: https://github.com/pll2050/kiwoom_trading_claude/issues
2. **로그 확인**: `sudo journalctl -u kiwoom-trading -n 100`
3. **설정 재확인**: `cat config/config.yaml`

---

## 체크리스트

설치 완료 후 확인:

- [ ] Python 3.11+ 설치 완료
- [ ] 프로젝트 클론 완료
- [ ] 가상환경 생성 및 패키지 설치
- [ ] config.yaml 설정 완료 (API 키 입력)
- [ ] 테스트 실행 성공 (`python3 main.py`)
- [ ] 시스템 서비스 등록 (선택사항)
- [ ] 로그 확인 가능
- [ ] 백업 설정 완료

---

**설치 완료! 🎉**

이제 우분투 서버에서 키움증권 AI 자동매매 시스템을 운영할 수 있습니다.

**⚠️ 주의사항**:
- 처음엔 반드시 `test_mode: true`로 테스트하세요
- 실전 투자 전에 모의투자로 충분히 검증하세요
- 정기적으로 로그를 확인하고 시스템을 모니터링하세요
