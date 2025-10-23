#!/bin/bash

# 키움증권 API curl 테스트 스크립트
# Mock API 서버 연결 및 응답 확인

echo "============================================================"
echo "키움증권 API curl 테스트"
echo "============================================================"
echo ""

# API 설정
APP_KEY="hpgmwXghUAL5-NciJDy9AU7_fj0IbFc4S4gJxM-WbmM"
APP_SECRET="VQTkpTT0gWaSdOcL7XTvPeIPi4BhNyYDBDho68VD5gI"
BASE_URL="https://mockapi.kiwoom.com"

echo "설정:"
echo "  Base URL: $BASE_URL"
echo "  App Key: ${APP_KEY:0:20}..."
echo ""

# 1. 서버 연결 테스트
echo "============================================================"
echo "1. 서버 연결 테스트"
echo "============================================================"
echo ""

echo "ping 테스트..."
ping -c 3 mockapi.kiwoom.com 2>&1 || echo "ping 실패 (정상일 수 있음)"
echo ""

echo "HTTP HEAD 요청..."
curl -I "$BASE_URL" 2>&1
echo ""

# 2. OAuth 토큰 발급 테스트
echo "============================================================"
echo "2. OAuth 토큰 발급 테스트"
echo "============================================================"
echo ""

TOKEN_ENDPOINT="$BASE_URL/oauth2/token"
echo "URL: $TOKEN_ENDPOINT"
echo ""

echo "요청 전송 중..."
RESPONSE=$(curl -v -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/json;charset=UTF-8" \
  -H "api-id: au10001" \
  -d "{
    \"grant_type\": \"client_credentials\",
    \"appkey\": \"$APP_KEY\",
    \"secretkey\": \"$APP_SECRET\"
  }" 2>&1)

echo "$RESPONSE"
echo ""

# Content-Type 확인
CONTENT_TYPE=$(echo "$RESPONSE" | grep -i "content-type:" | head -1)
echo "Content-Type: $CONTENT_TYPE"
echo ""

# HTML 응답 확인
if echo "$RESPONSE" | grep -q "<!DOCTYPE\|<html\|<HTML"; then
    echo "⚠️  경고: HTML 응답이 감지되었습니다!"
    echo "Mock API 서버가 정상 작동하지 않습니다."
    echo ""
    echo "응답 내용 (처음 500자):"
    echo "$RESPONSE" | tail -n +1 | head -c 500
    echo ""
fi

# JSON 응답 확인
if echo "$RESPONSE" | grep -q '"token"'; then
    echo "✅ JSON 응답 확인 - 토큰 발급 성공!"
    TOKEN=$(echo "$RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    echo "토큰: ${TOKEN:0:30}..."
    echo ""
fi

# 3. 대체 엔드포인트 테스트
echo "============================================================"
echo "3. 대체 엔드포인트 테스트"
echo "============================================================"
echo ""

ENDPOINTS=(
    "/oauth2/token"
    "/api/oauth2/token"
    "/v1/oauth2/token"
    "/auth/token"
)

for endpoint in "${ENDPOINTS[@]}"; do
    url="$BASE_URL$endpoint"
    echo "테스트: $url"

    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    echo "  HTTP 상태: $STATUS"

    if [ "$STATUS" != "000" ]; then
        CONTENT=$(curl -s "$url" | head -c 200)
        echo "  응답: $CONTENT..."
    fi
    echo ""
done

# 4. 운영 API 서버 테스트
echo "============================================================"
echo "4. 운영 API 서버 연결 테스트"
echo "============================================================"
echo ""

PROD_URL="https://api.kiwoom.com"
echo "URL: $PROD_URL"
echo ""

echo "연결 테스트..."
curl -I "$PROD_URL" 2>&1 | head -20
echo ""

# 5. 요약 및 권장사항
echo "============================================================"
echo "5. 요약 및 권장사항"
echo "============================================================"
echo ""

if echo "$RESPONSE" | grep -q "<!DOCTYPE\|<html"; then
    echo "❌ Mock API 서버가 HTML을 반환합니다."
    echo ""
    echo "해결 방법:"
    echo "1. config/config.yaml을 열고:"
    echo "   base_url: \"https://api.kiwoom.com\"  # 운영 API로 변경"
    echo ""
    echo "2. 또는 키움증권에 Mock API 서버 상태 문의:"
    echo "   - 고객센터: 1544-5000"
    echo "   - OpenAPI 문의: https://www.kiwoom.com"
    echo ""
elif echo "$RESPONSE" | grep -q '"token"'; then
    echo "✅ API 연결 정상!"
    echo "토큰 발급이 성공적으로 완료되었습니다."
    echo ""
else
    echo "⚠️  API 응답을 확인할 수 없습니다."
    echo "위의 로그를 확인하여 문제를 파악하세요."
    echo ""
fi

echo "============================================================"
echo "테스트 완료"
echo "============================================================"
