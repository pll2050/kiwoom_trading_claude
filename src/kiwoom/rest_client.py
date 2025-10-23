"""
키움증권 REST API 클라이언트
OAuth 인증, 계좌 조회, 주문 실행, 시세 조회
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from src.utils.logger import logger
from src.utils.config_loader import load_config


class KiwoomRestClient:
    """키움증권 REST API 비동기 클라이언트"""

    def __init__(self):
        config = load_config("config")
        self.app_key = config['kiwoom']['app_key']
        self.app_secret = config['kiwoom']['app_secret']
        self.account_number = config['kiwoom']['account_number']
        self.base_url = config['kiwoom']['base_url']

        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        # Rate Limiting 설정
        self.last_request_time: Dict[str, datetime] = {}
        self.min_request_interval = 1.0  # 1000ms (초당 1회) - API ID별 엄격한 제한
        self.max_retries = 3
        self.retry_delay = 3.0  # 3초

        logger.info("키움증권 REST API 클라이언트 초기화")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()

        # 테스트 모드 확인
        from src.utils.config_loader import load_config
        config = load_config("config")
        test_mode = config.get('trading', {}).get('test_mode', False)

        if test_mode:
            logger.info("🧪 테스트 모드: API 토큰 발급 스킵")
            self.access_token = "TEST_TOKEN"
            self.token_expires_at = datetime.now() + timedelta(days=1)
        else:
            await self.get_access_token()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            logger.info("세션 종료")

    async def _ensure_token(self):
        """토큰 유효성 확인 및 자동 갱신"""
        if not self.access_token or not self.token_expires_at:
            await self.get_access_token()
        elif datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            logger.info("토큰 재발급")
            await self.get_access_token()

    async def _rate_limit(self, api_id: str):
        """API별 Rate Limiting 적용"""
        if api_id in self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time[api_id]).total_seconds()
            if elapsed < self.min_request_interval:
                delay = self.min_request_interval - elapsed
                await asyncio.sleep(delay)

        self.last_request_time[api_id] = datetime.now()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        api_id: str = ""
    ) -> Dict[str, Any]:
        """API 요청 실행 (Rate Limiting + Retry 로직 포함)"""
        await self._ensure_token()

        # Rate Limiting 적용
        if api_id:
            await self._rate_limit(api_id)

        url = f"{self.base_url}{endpoint}"

        # 키움증권 API 표준 헤더
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json;charset=UTF-8"
        }

        # api-id 헤더 추가 (키움증권 필수)
        if api_id:
            headers["api-id"] = api_id

        # Retry 로직
        for attempt in range(self.max_retries):
            try:
                async with self.session.request(
                    method, url, json=data, params=params, headers=headers
                ) as response:
                    result = await response.json()

                    # 429 Rate Limit 에러 처리
                    if response.status == 429:
                        if attempt < self.max_retries - 1:
                            retry_after = self.retry_delay * (attempt + 1)
                            logger.warning(f"Rate Limit 초과 (429). {retry_after}초 후 재시도... ({attempt + 1}/{self.max_retries})")
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            logger.error(f"Rate Limit 초과 (429) - 최대 재시도 횟수 도달: {result}")
                            raise Exception(f"Rate Limit Error: {result}")

                    # 기타 에러
                    if response.status != 200:
                        logger.error(f"API 오류: {response.status} - {result}")
                        raise Exception(f"API Error: {result}")

                    return result

            except aiohttp.ClientError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"요청 실패, 재시도 중... ({attempt + 1}/{self.max_retries}): {e}")
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"요청 실패: {endpoint} - {e}")
                    raise
            except Exception as e:
                logger.error(f"요청 실패: {endpoint} - {e}")
                raise

        # 모든 재시도 실패
        raise Exception(f"Maximum retries exceeded for {endpoint}")

    # OAuth 인증
    async def get_access_token(self) -> str:
        """접근 토큰 발급 (au10001)"""
        endpoint = "/oauth2/token"

        # 키움증권 API 스펙에 맞는 요청 데이터
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret  # 키움증권은 'secretkey' 사용
        }

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "api-id": "au10001"  # 키움증권은 api-id 헤더 필요
        }

        try:
            async with self.session.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers=headers
            ) as response:
                # 응답 상태 코드 확인
                if response.status != 200:
                    response_text = await response.text()
                    logger.error(
                        f"토큰 발급 실패 - HTTP {response.status}\n"
                        f"URL: {self.base_url}{endpoint}\n"
                        f"응답: {response_text[:500]}"
                    )
                    raise Exception(f"HTTP {response.status}: 토큰 발급 실패")

                # Content-Type 확인
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' not in content_type:
                    response_text = await response.text()
                    logger.error(
                        f"JSON이 아닌 응답 수신 - Content-Type: {content_type}\n"
                        f"URL: {self.base_url}{endpoint}\n"
                        f"응답 내용:\n{response_text[:1000]}"
                    )

                    # Mock API 서버 문제인 경우 안내
                    if 'text/html' in content_type:
                        logger.error(
                            "\n" + "="*60 + "\n"
                            "🚨 Mock API 서버 오류\n"
                            "="*60 + "\n"
                            "Mock API 서버가 HTML을 반환했습니다.\n"
                            "가능한 원인:\n"
                            "1. Mock API 서버가 다운되었거나 점검 중\n"
                            "2. API 엔드포인트가 변경됨\n"
                            "3. config.yaml에서 실제 운영 API URL 사용 필요\n\n"
                            "해결 방법:\n"
                            "- 키움증권 OpenAPI 문서 확인\n"
                            "- config.yaml의 base_url을 실제 운영 URL로 변경\n"
                            "- 키움증권 고객센터에 문의\n"
                            + "="*60
                        )
                    raise Exception(f"서버가 JSON 대신 {content_type} 응답")

                result = await response.json()

                # 키움증권 응답: token, token_type, expires_dt
                self.access_token = result.get("token")

                # expires_dt 파싱 (예: "20241107083713")
                expires_dt = result.get("expires_dt")
                if expires_dt:
                    from datetime import datetime
                    expires_time = datetime.strptime(expires_dt, "%Y%m%d%H%M%S")
                    self.token_expires_at = expires_time
                else:
                    # 기본값: 24시간
                    self.token_expires_at = datetime.now() + timedelta(seconds=86400)

                logger.info("토큰 발급 성공")
                return self.access_token
        except Exception as e:
            logger.error(f"토큰 발급 실패: {e}")
            raise

    # 계좌 조회
    async def get_balance(self) -> Dict[str, Any]:
        """예수금상세현황 조회 (kt00001)"""
        return await self._request(
            method="POST",
            endpoint="/api/dostk/acnt",
            data={"qry_tp": "2"},  # 2:일반조회
            api_id="kt00001"
        )

    async def get_account_info(self) -> Dict[str, Any]:
        """추정자산 조회 (kt00003)"""
        return await self._request(
            method="POST",
            endpoint="/api/dostk/acnt",
            data={"qry_tp": "3"},  # 3:추정조회
            api_id="kt00003"
        )

    async def get_holdings(self) -> List[Dict[str, Any]]:
        """계좌평가잔고내역 조회 (kt00018)"""
        result = await self._request(
            method="POST",
            endpoint="/api/dostk/acnt",
            data={
                "qry_tp": "2",           # 2:개별
                "dmst_stex_tp": "KRX"    # KRX:한국거래소
            },
            api_id="kt00018"
        )
        return result.get("acnt_evlt_remn_indv_tot", [])

    async def get_profit_loss(self) -> Dict[str, Any]:
        """계좌수익률 조회 (ka10085)"""
        return await self._request("GET", "/api/account/profit", params={
            "account_no": self.account_number
        })

    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """미체결 조회 (ka10075)"""
        result = await self._request("GET", "/api/orders/open", params={
            "account_no": self.account_number
        })
        return result.get("orders", [])

    # 주문 실행
    async def order_buy(
        self,
        stock_code: str,
        quantity: int,
        price: int,
        order_type: str = "limit"
    ) -> Dict[str, Any]:
        """매수 주문 (kt10000)"""
        data = {
            "account_no": self.account_number,
            "stock_code": stock_code,
            "quantity": quantity,
            "price": price,
            "order_type": order_type
        }
        logger.info(f"매수: {stock_code} {quantity}주 @{price}원")
        return await self._request("POST", "/api/orders/buy", data=data)

    async def order_sell(
        self,
        stock_code: str,
        quantity: int,
        price: int,
        order_type: str = "limit"
    ) -> Dict[str, Any]:
        """매도 주문 (kt10001)"""
        data = {
            "account_no": self.account_number,
            "stock_code": stock_code,
            "quantity": quantity,
            "price": price,
            "order_type": order_type
        }
        logger.info(f"매도: {stock_code} {quantity}주 @{price}원")
        return await self._request("POST", "/api/orders/sell", data=data)

    async def cancel_order(self, order_no: str) -> Dict[str, Any]:
        """주문 취소 (kt10003)"""
        logger.info(f"취소: {order_no}")
        return await self._request("DELETE", f"/api/orders/{order_no}")

    # 시세 조회
    async def get_quote(self, stock_code: str) -> Dict[str, Any]:
        """현재가 및 기본정보 조회 (ka10001)"""
        result = await self._request(
            method="POST",
            endpoint="/api/dostk/stkinfo",
            data={"stk_cd": stock_code},
            api_id="ka10001"
        )

        # 응답 데이터 정규화
        return {
            "code": result.get("stk_cd", ""),
            "name": result.get("stk_nm", ""),
            "price": int(result.get("cur_prc", "0").replace("+", "").replace("-", "")),
            "change": float(result.get("flu_rt", "0").replace("+", "").replace("-", "")),
            "volume": int(result.get("trde_qty", "0")),
            "high": int(result.get("high_pric", "0").replace("+", "").replace("-", "")),
            "low": int(result.get("low_pric", "0").replace("+", "").replace("-", "")),
            "open": int(result.get("open_pric", "0").replace("+", "").replace("-", "")),
            "high_proximity": self._calc_high_proximity(
                int(result.get("cur_prc", "0").replace("+", "").replace("-", "")),
                int(result.get("high_pric", "0").replace("+", "").replace("-", ""))
            ),
            "strength": 100  # 기본값
        }

    def _calc_high_proximity(self, current: int, high: int) -> float:
        """고가 근접도 계산"""
        if high == 0:
            return 0
        return (current / high) * 100

    async def get_orderbook(self, stock_code: str) -> Dict[str, Any]:
        """호가 조회 (ka10004)"""
        result = await self._request(
            method="POST",
            endpoint="/api/dostk/mrkcond",
            data={"stk_cd": stock_code},
            api_id="ka10004"
        )

        # 호가 데이터 파싱 (매수/매도 1~5호가)
        bids = []
        asks = []

        for i in range(1, 6):
            # 매수호가
            if i == 1:
                bid_price = result.get("buy_fpr_bid", "0")
                bid_volume = result.get("buy_fpr_req", "0")
            else:
                bid_price = result.get(f"buy_{i}th_pre_bid", "0")
                bid_volume = result.get(f"buy_{i}th_pre_req", "0")

            if bid_price and bid_volume:
                bids.append({
                    "price": int(bid_price.replace("+", "").replace("-", "")),
                    "volume": int(bid_volume)
                })

            # 매도호가
            if i == 1:
                ask_price = result.get("sel_fpr_bid", "0")
                ask_volume = result.get("sel_fpr_req", "0")
            else:
                ask_price = result.get(f"sel_{i}th_pre_bid", "0")
                ask_volume = result.get(f"sel_{i}th_pre_req", "0")

            if ask_price and ask_volume:
                asks.append({
                    "price": int(ask_price.replace("+", "").replace("-", "")),
                    "volume": int(ask_volume)
                })

        return {
            "bids": bids,
            "asks": asks
        }

    # 스캐닝용 API
    async def get_volume_surge_stocks(self, limit: int = 100) -> List[Dict]:
        """거래량 급증 (ka10023)"""
        result = await self._request(
            method="POST",
            endpoint="/api/dostk/rkinfo",
            data={
                "mrkt_tp": "000",  # 전체
                "sort_tp": "1",    # 급증량
                "tm_tp": "1",      # 분
                "trde_qty_tp": "5",  # 5천주이상
                "tm": "10",        # 10분
                "stk_cnd": "0",    # 전체조회
                "pric_tp": "0",    # 전체조회
                "stex_tp": "1"     # KRX
            },
            api_id="ka10023"
        )
        return self._parse_ranking_result(result, "trde_qty_sdnin")

    async def get_volume_leaders(self, limit: int = 100) -> List[Dict]:
        """거래량 상위 (ka10030)"""
        result = await self._request(
            method="POST",
            endpoint="/api/dostk/rkinfo",
            data={
                "mrkt_tp": "000",      # 전체
                "sort_tp": "1",        # 거래량
                "mang_stk_incls": "0", # 전체
                "crd_tp": "0",         # 전체
                "trde_qty_tp": "0",    # 전체
                "pric_tp": "0",        # 전체
                "trde_prica_tp": "0",  # 전체
                "mrkt_open_tp": "0",   # 전체조회 (0: 전체, 1: 장중, 2: 장전, 3: 장후)
                "stex_tp": "1"         # KRX
            },
            api_id="ka10030"
        )
        return self._parse_ranking_result(result, "tdy_trde_qty_upper")

    async def get_turnover_leaders(self, limit: int = 100) -> List[Dict]:
        """거래대금 상위 (ka10032)"""
        result = await self._request(
            method="POST",
            endpoint="/api/dostk/rkinfo",
            data={
                "mrkt_tp": "000",      # 전체
                "mang_stk_incls": "0", # 전체
                "stex_tp": "1"         # KRX
            },
            api_id="ka10032"
        )
        return self._parse_ranking_result(result, "trde_prica_upper")

    async def get_price_change_leaders(self, limit: int = 100) -> List[Dict]:
        """등락률 상위 (ka10027)"""
        result = await self._request(
            method="POST",
            endpoint="/api/dostk/rkinfo",
            data={
                "mrkt_tp": "000",        # 전체
                "sort_tp": "1",          # 상승률
                "trde_qty_cnd": "0000",  # 전체조회
                "stk_cnd": "0",          # 전체조회
                "crd_cnd": "0",          # 전체조회
                "updown_incls": "1",     # 포함
                "pric_cnd": "0",         # 전체조회
                "trde_prica_cnd": "0",   # 전체조회
                "stex_tp": "1"           # KRX
            },
            api_id="ka10027"
        )
        return self._parse_ranking_result(result, "pred_pre_flu_rt_upper")

    def _parse_ranking_result(self, result: Dict, list_key: str) -> List[Dict]:
        """순위정보 API 응답 파싱"""
        # API별로 다른 응답 키를 사용
        items = result.get(list_key, [])

        parsed = []
        for item in items:
            # 가격과 수량 값에서 부호 제거
            cur_prc = item.get("cur_prc", "0").replace("+", "").replace("-", "")
            trde_qty = item.get("trde_qty", item.get("now_trde_qty", "0"))

            # 거래대금: trde_amt (원) 또는 trde_prica (백만원)
            trde_amt_str = item.get("trde_amt", item.get("trde_prica", "0"))

            try:
                price = int(cur_prc) if cur_prc else 0
                volume = int(trde_qty) if trde_qty else 0

                # trde_prica는 백만원 단위이므로 변환 (1,000,000 곱하기)
                trading_value_raw = int(trde_amt_str) if trde_amt_str else 0

                # trde_amt (원 단위)인지 trde_prica (백만원 단위)인지 판단
                if "trde_prica" in item:
                    trading_value = trading_value_raw * 1_000_000  # 백만원 → 원
                else:
                    trading_value = trading_value_raw  # 이미 원 단위

            except (ValueError, TypeError):
                continue

            parsed.append({
                "code": item.get("stk_cd", ""),
                "name": item.get("stk_nm", ""),
                "price": price,
                "price_change": float(item.get("flu_rt", "0").replace("+", "").replace("-", "")),
                "volume": volume,
                "trading_value": trading_value,
                "status": ""
            })
        return parsed

    async def get_chart_data(
        self,
        stock_code: str,
        timeframe: str = "day",
        count: int = 100
    ) -> List[Dict]:
        """차트 데이터 (ka10079~10083)"""
        result = await self._request("GET", f"/api/chart/{stock_code}", params={
            "timeframe": timeframe,
            "count": count
        })
        return result.get("candles", [])


__all__ = ["KiwoomRestClient"]
