# 키움증권 API PowerShell 테스트 스크립트
# Windows용 - Mock API 서버 연결 및 응답 확인

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "키움증권 API 테스트 (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# API 설정
$APP_KEY = "hpgmwXghUAL5-NciJDy9AU7_fj0IbFc4S4gJxM-WbmM"
$APP_SECRET = "VQTkpTT0gWaSdOcL7XTvPeIPi4BhNyYDBDho68VD5gI"
$BASE_URL = "https://mockapi.kiwoom.com"

Write-Host "설정:"
Write-Host "  Base URL: $BASE_URL"
Write-Host "  App Key: $($APP_KEY.Substring(0,20))..."
Write-Host ""

# 1. 서버 연결 테스트
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "1. 서버 연결 테스트" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "ping 테스트..."
try {
    Test-Connection -ComputerName "mockapi.kiwoom.com" -Count 3 -ErrorAction Stop | Format-Table
} catch {
    Write-Host "ping 실패: $_" -ForegroundColor Yellow
}
Write-Host ""

# 2. OAuth 토큰 발급 테스트
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "2. OAuth 토큰 발급 테스트" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$TOKEN_ENDPOINT = "$BASE_URL/oauth2/token"
Write-Host "URL: $TOKEN_ENDPOINT"
Write-Host ""

# 요청 본문
$body = @{
    grant_type = "client_credentials"
    appkey = $APP_KEY
    secretkey = $APP_SECRET
} | ConvertTo-Json

# 헤더
$headers = @{
    "Content-Type" = "application/json;charset=UTF-8"
    "api-id" = "au10001"
}

Write-Host "요청 전송 중..."
Write-Host "요청 헤더: $($headers | ConvertTo-Json)"
Write-Host "요청 본문: $body"
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri $TOKEN_ENDPOINT -Method POST -Body $body -Headers $headers -ErrorAction Stop

    Write-Host "✅ 응답 수신 성공!" -ForegroundColor Green
    Write-Host "HTTP 상태: $($response.StatusCode)"
    Write-Host "Content-Type: $($response.Headers['Content-Type'])"
    Write-Host ""

    Write-Host "응답 본문:"
    Write-Host $response.Content
    Write-Host ""

    # JSON 파싱 시도
    try {
        $json = $response.Content | ConvertFrom-Json
        if ($json.token) {
            Write-Host "✅ 토큰 발급 성공!" -ForegroundColor Green
            Write-Host "토큰: $($json.token.Substring(0,30))..."
        }
    } catch {
        Write-Host "⚠️  JSON 파싱 실패" -ForegroundColor Yellow
    }

} catch {
    Write-Host "❌ 요청 실패!" -ForegroundColor Red
    Write-Host "에러: $($_.Exception.Message)"
    Write-Host ""

    # 응답 내용 확인
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()

        Write-Host "HTTP 상태: $($_.Exception.Response.StatusCode.value__)"
        Write-Host "Content-Type: $($_.Exception.Response.ContentType)"
        Write-Host ""
        Write-Host "응답 내용 (처음 500자):"
        Write-Host $responseBody.Substring(0, [Math]::Min(500, $responseBody.Length))
        Write-Host ""

        # HTML 응답 확인
        if ($responseBody -match "<!DOCTYPE|<html|<HTML") {
            Write-Host "⚠️  경고: HTML 응답이 감지되었습니다!" -ForegroundColor Red
            Write-Host "Mock API 서버가 정상 작동하지 않습니다." -ForegroundColor Red
        }
    }
}

# 3. 대체 엔드포인트 테스트
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "3. 대체 엔드포인트 테스트" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$endpoints = @(
    "/oauth2/token",
    "/api/oauth2/token",
    "/v1/oauth2/token",
    "/auth/token"
)

foreach ($endpoint in $endpoints) {
    $url = "$BASE_URL$endpoint"
    Write-Host "테스트: $url"

    try {
        $testResponse = Invoke-WebRequest -Uri $url -Method GET -ErrorAction Stop
        Write-Host "  HTTP 상태: $($testResponse.StatusCode)" -ForegroundColor Green
        Write-Host "  Content-Type: $($testResponse.Headers['Content-Type'])"
    } catch {
        Write-Host "  HTTP 상태: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# 4. 운영 API 서버 테스트
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "4. 운영 API 서버 연결 테스트" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$PROD_URL = "https://api.kiwoom.com"
Write-Host "URL: $PROD_URL"
Write-Host ""

try {
    $prodResponse = Invoke-WebRequest -Uri $PROD_URL -Method GET -ErrorAction Stop
    Write-Host "✅ 연결 성공!" -ForegroundColor Green
    Write-Host "HTTP 상태: $($prodResponse.StatusCode)"
} catch {
    Write-Host "연결 실패 또는 인증 필요"
    Write-Host "HTTP 상태: $($_.Exception.Response.StatusCode.value__)"
}
Write-Host ""

# 5. 요약 및 권장사항
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "5. 요약 및 권장사항" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "1. Mock API 서버가 HTML을 반환하면:" -ForegroundColor Yellow
Write-Host "   - config/config.yaml을 열고" -ForegroundColor Yellow
Write-Host "   - base_url을 운영 API로 변경: https://api.kiwoom.com" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. 키움증권 고객센터 문의:" -ForegroundColor Yellow
Write-Host "   - 전화: 1544-5000" -ForegroundColor Yellow
Write-Host "   - OpenAPI: https://www.kiwoom.com" -ForegroundColor Yellow
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "테스트 완료" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
