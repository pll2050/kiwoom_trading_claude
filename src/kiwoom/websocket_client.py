"""
키움증권 WebSocket 클라이언트
실시간 시세 데이터 수신
"""

import asyncio
import json
import websockets
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from src.utils.logger import logger
from src.utils.config_loader import load_config


class KiwoomWebSocketClient:
    """키움증권 WebSocket 비동기 클라이언트"""

    # 실시간 데이터 타입
    RT_ORDER_EXECUTION = "00"  # 주문체결
    RT_CURRENT_PRICE = "01"    # 현재가
    RT_ORDERBOOK = "02"        # 호가
    RT_BALANCE = "04"          # 잔고
    RT_STOCK_QUOTE = "0A"      # 주식기세
    RT_STOCK_EXECUTION = "0B"  # 주식체결
    RT_PRIORITY_QUOTE = "0C"   # 주식우선호가
    RT_QUOTE_VOLUME = "0D"     # 주식호가잔량

    def __init__(self, access_token: str):
        config = load_config("config")

        # 테스트 모드에 따라 올바른 WebSocket URL 선택
        test_mode = config.get('trading', {}).get('test_mode', False)
        kiwoom_config_key = 'kiwoom_test' if test_mode else 'kiwoom'

        self.websocket_url = config[kiwoom_config_key]['websocket_url']
        self.access_token = access_token

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.is_running = False

        # 구독 관리
        self.subscriptions: Dict[str, List[str]] = {}  # {data_type: [stock_codes]}

        # 콜백 핸들러
        self.handlers: Dict[str, List[Callable]] = {
            self.RT_ORDER_EXECUTION: [],
            self.RT_CURRENT_PRICE: [],
            self.RT_ORDERBOOK: [],
            self.RT_BALANCE: [],
            self.RT_STOCK_QUOTE: [],
            self.RT_STOCK_EXECUTION: []
        }

        # 재연결 설정
        self.reconnect_delay = 5  # 초
        self.max_reconnect_attempts = 10
        self.reconnect_count = 0

        # 하트비트
        self.heartbeat_interval = 30  # 초
        self.last_heartbeat = None

        logger.info("WebSocket 클라이언트 초기화")

    async def connect(self):
        """WebSocket 연결 및 로그인 (타임아웃: 10초)"""
        try:
            logger.info(f"WebSocket 연결 시도: {self.websocket_url}")

            # WebSocket 연결 (헤더 없이 연결)
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    ping_interval=20,
                    ping_timeout=10
                ),
                timeout=10.0
            )

            logger.info("WebSocket 연결 성공, 로그인 시도 중...")

            # LOGIN 패킷 전송 (키움증권 WebSocket 필수)
            login_message = {
                "trnm": "LOGIN",
                "token": self.access_token
            }
            await self.websocket.send(json.dumps(login_message))
            logger.info("LOGIN 패킷 전송 완료")

            # LOGIN 응답 대기 (최대 5초)
            try:
                response_str = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                response = json.loads(response_str)

                if response.get("trnm") == "LOGIN":
                    if response.get("return_code") == 0:
                        logger.info("WebSocket 로그인 성공")
                        self.is_connected = True
                        self.reconnect_count = 0

                        # 로그인 성공 후 기존 구독 복원
                        await self._restore_subscriptions()
                    else:
                        error_msg = response.get("return_msg", "알 수 없는 오류")
                        logger.error(f"WebSocket 로그인 실패: {error_msg}")
                        self.is_connected = False
                        raise Exception(f"LOGIN failed: {error_msg}")
                else:
                    logger.warning(f"예상치 못한 응답: {response}")

            except asyncio.TimeoutError:
                logger.error("LOGIN 응답 타임아웃")
                self.is_connected = False
                raise

        except asyncio.TimeoutError:
            logger.warning(f"WebSocket 연결 타임아웃 (10초 초과)")
            self.is_connected = False
            raise

        except Exception as e:
            logger.warning(f"WebSocket 연결 실패: {e}")
            self.is_connected = False
            raise

    async def disconnect(self):
        """WebSocket 연결 종료"""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket 연결 종료")

    async def start(self):
        """WebSocket 수신 시작 (연결 실패 시 계속 재시도)"""
        self.is_running = True

        while self.is_running:
            try:
                if not self.is_connected:
                    await self.connect()

                # 병렬 실행: 메시지 수신 + 하트비트
                await asyncio.gather(
                    self._receive_messages(),
                    self._heartbeat_loop(),
                    return_exceptions=True
                )

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket 연결 끊김")
                self.is_connected = False
                await self._handle_reconnect()

            except asyncio.TimeoutError:
                # 타임아웃은 경고만 남기고 계속 진행
                logger.warning(f"WebSocket 연결 타임아웃. {self.reconnect_delay}초 후 재시도...")
                self.is_connected = False
                await asyncio.sleep(self.reconnect_delay)

            except Exception as e:
                # 기타 오류는 경고만 남기고 재연결 시도
                logger.warning(f"WebSocket 오류: {e}. {self.reconnect_delay}초 후 재시도...")
                self.is_connected = False
                await asyncio.sleep(self.reconnect_delay)

    async def _receive_messages(self):
        """메시지 수신 루프"""
        while self.is_running and self.is_connected:
            try:
                message = await self.websocket.recv()
                await self._handle_message(message)

            except websockets.exceptions.ConnectionClosed:
                raise
            except Exception as e:
                logger.error(f"메시지 수신 오류: {e}")

    async def _handle_message(self, message: str):
        """수신한 메시지 처리 (키움증권 WebSocket 스펙)"""
        try:
            data = json.loads(message)
            trnm = data.get("trnm")

            # PING 메시지 처리 (서버가 보낸 PING을 그대로 반환)
            if trnm == "PING":
                await self.websocket.send(message)
                logger.debug("PING 응답 전송")
                return

            # 등록 응답
            if trnm == "REG":
                return_code = data.get("return_code")
                if return_code == 0:
                    logger.debug("구독 등록 성공")
                else:
                    logger.error(f"구독 등록 실패: {data.get('return_msg')}")
                return

            # 실시간 데이터 수신
            if trnm == "REAL":
                data_list = data.get("data", [])
                for item in data_list:
                    data_type = item.get("type")  # "00", "01", "04" 등
                    stock_code = item.get("item", "")
                    values = item.get("values", {})

                    # 핸들러 호출
                    handlers = self.handlers.get(data_type, [])
                    for handler in handlers:
                        try:
                            await handler({
                                "type": data_type,
                                "item": stock_code,
                                "name": item.get("name"),
                                "values": values
                            })
                        except Exception as e:
                            logger.error(f"핸들러 실행 오류 ({data_type}): {e}")
                return

        except json.JSONDecodeError:
            logger.error(f"JSON 파싱 실패: {message}")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")

    async def _heartbeat_loop(self):
        """하트비트 전송 (WebSocket 자체 ping/pong 사용)"""
        # 키움증권 WebSocket은 자체적으로 ping/pong 처리
        # websockets 라이브러리가 자동으로 ping_interval에 따라 처리함
        while self.is_running and self.is_connected:
            await asyncio.sleep(30)
            # 연결 상태만 확인
            if not self.websocket or self.websocket.closed:
                break

    async def _handle_reconnect(self):
        """재연결 처리"""
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error("최대 재연결 시도 횟수 초과")
            self.is_running = False
            return

        self.reconnect_count += 1
        delay = self.reconnect_delay * self.reconnect_count

        logger.info(f"재연결 시도 {self.reconnect_count}/{self.max_reconnect_attempts} ({delay}초 후)")
        await asyncio.sleep(delay)

    async def _restore_subscriptions(self):
        """연결 복구 시 구독 복원"""
        if not self.subscriptions:
            return

        logger.info("구독 복원 중...")
        for data_type, stock_codes in self.subscriptions.items():
            for code in stock_codes:
                await self._send_subscribe(data_type, code)

    async def _send_subscribe(self, data_type: str, stock_code: str):
        """구독 요청 전송 (키움증권 WebSocket 스펙)"""
        try:
            # 키움증권 WebSocket 메시지 형식
            message = {
                "trnm": "REG",  # 등록
                "grp_no": "1",  # 그룹번호
                "refresh": "1",  # 기존 유지
                "data": [
                    {
                        "item": [stock_code] if stock_code != "ALL" else [""],
                        "type": [data_type]
                    }
                ]
            }
            await self.websocket.send(json.dumps(message))
            logger.debug(f"구독 요청: {data_type} - {stock_code}")
        except Exception as e:
            logger.error(f"구독 요청 실패: {e}")

    async def _send_unsubscribe(self, data_type: str, stock_code: str):
        """구독 해제 요청 전송 (키움증권 WebSocket 스펙)"""
        try:
            # 키움증권 WebSocket 해제 메시지
            message = {
                "trnm": "REMOVE",  # 해제
                "grp_no": "1",
                "data": [
                    {
                        "item": [stock_code] if stock_code != "ALL" else [""],
                        "type": [data_type]
                    }
                ]
            }
            await self.websocket.send(json.dumps(message))
            logger.debug(f"구독 해제: {data_type} - {stock_code}")
        except Exception as e:
            logger.error(f"구독 해제 실패: {e}")

    # 공개 API

    async def subscribe(self, data_type: str, stock_code: str):
        """실시간 데이터 구독"""
        if data_type not in self.subscriptions:
            self.subscriptions[data_type] = []

        if stock_code not in self.subscriptions[data_type]:
            self.subscriptions[data_type].append(stock_code)

            if self.is_connected:
                await self._send_subscribe(data_type, stock_code)

            logger.info(f"구독 추가: {data_type} - {stock_code}")

    async def unsubscribe(self, data_type: str, stock_code: str):
        """실시간 데이터 구독 해제"""
        if data_type in self.subscriptions and stock_code in self.subscriptions[data_type]:
            self.subscriptions[data_type].remove(stock_code)

            if self.is_connected:
                await self._send_unsubscribe(data_type, stock_code)

            logger.info(f"구독 해제: {data_type} - {stock_code}")

    async def subscribe_current_price(self, stock_code: str):
        """현재가 구독"""
        await self.subscribe(self.RT_CURRENT_PRICE, stock_code)

    async def subscribe_orderbook(self, stock_code: str):
        """호가 구독"""
        await self.subscribe(self.RT_ORDERBOOK, stock_code)

    async def subscribe_order_execution(self):
        """주문체결 구독 (계좌 전체)"""
        await self.subscribe(self.RT_ORDER_EXECUTION, "ALL")

    async def subscribe_balance(self):
        """잔고 구독 (계좌 전체)"""
        await self.subscribe(self.RT_BALANCE, "ALL")

    def add_handler(self, data_type: str, handler: Callable):
        """데이터 타입별 핸들러 등록"""
        if data_type not in self.handlers:
            self.handlers[data_type] = []

        self.handlers[data_type].append(handler)
        logger.info(f"핸들러 등록: {data_type}")

    def remove_handler(self, data_type: str, handler: Callable):
        """핸들러 제거"""
        if data_type in self.handlers and handler in self.handlers[data_type]:
            self.handlers[data_type].remove(handler)
            logger.info(f"핸들러 제거: {data_type}")


class RealTimeDataQueue:
    """실시간 데이터 큐 관리"""

    def __init__(self, maxsize: int = 1000):
        self.queue = asyncio.Queue(maxsize=maxsize)
        self.latest_data: Dict[str, Dict[str, Any]] = {}  # {data_type: {stock_code: data}}

    async def put(self, data_type: str, stock_code: str, data: Dict[str, Any]):
        """데이터 추가"""
        try:
            await self.queue.put({
                "data_type": data_type,
                "stock_code": stock_code,
                "data": data,
                "timestamp": datetime.now()
            })

            # 최신 데이터 캐시
            if data_type not in self.latest_data:
                self.latest_data[data_type] = {}
            self.latest_data[data_type][stock_code] = data

        except asyncio.QueueFull:
            logger.warning(f"데이터 큐 가득참 ({data_type})")

    async def get(self) -> Dict[str, Any]:
        """데이터 가져오기"""
        return await self.queue.get()

    def get_latest(self, data_type: str, stock_code: str) -> Optional[Dict[str, Any]]:
        """최신 데이터 조회"""
        return self.latest_data.get(data_type, {}).get(stock_code)

    def qsize(self) -> int:
        """큐 크기"""
        return self.queue.qsize()


__all__ = ["KiwoomWebSocketClient", "RealTimeDataQueue"]
