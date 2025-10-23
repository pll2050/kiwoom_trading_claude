# -*- coding: utf-8 -*-
"""
키움증권 REST API 클라이언트
Kiwoom REST API Client

이 모듈은 키움증권 REST API와의 비동기 상호작용을 관리합니다.
OAuth2.0 인증, 계좌 조회, 주문 실행, 시세 조회 등 다양한 API 기능을 포함합니다.
"""
import asyncio
import aiohttp
import yaml
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# 프로젝트의 로거를 가져옵니다.
from src.utils.logger import logger

class KiwoomRestClient:
    """
    키움증권 REST API 비동기 클라이언트 클래스.
    OAuth 인증, API 호출, 토큰 자동 갱신을 처리합니다.
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        KiwoomRestClient를 초기화합니다.

        Args:
            config_path (str): 설정 파일의 경로.
        """
        self._load_config(config_path)
        self.client_session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._token_lock = asyncio.Lock()
        logger.info("Kiwoom REST API 클라이언트 초기화 완료.")

    def _load_config(self, config_path: str) -> None:
        """설정 파일(config.yaml)을 로드합니다."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.app_key = config['kiwoom']['app_key']
            self.app_secret = config['kiwoom']['app_secret']
            self.account_number = config['kiwoom']['account_number']
            self.base_url = config['kiwoom']['base_url']
            self.is_test_mode = config['trading']['test_mode']
            
            # 모의투자/실전투자에 따른 URL 분기 (가정)
            # 실제 키움증권 API는 base_url이 동일하고 tr_id로 구분하는 경우가 많습니다.
            # 여기서는 예시로 도메인을 변경하는 로직을 추가해봅니다.
            if self.is_test_mode:
                self.base_url = self.base_url.replace("openapi", "openapi-mock") # 가상의 모의투자 URL
                logger.warning("테스트 모드로 실행됩니다. 모의투자 서버를 사용합니다.")
            
            logger.info(f"설정 파일 로드 완료. API URL: {self.base_url}")

        except FileNotFoundError:
            logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
            raise
        except KeyError as e:
            logger.error(f"설정 파일에 필수 키가 없습니다: {e}")
            raise

    async def __aenter__(self):
        """비동기 컨텍스트 관리자 진입점."""
        self.client_session = aiohttp.ClientSession()
        await self._get_valid_token()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 관리자 종료점."""
        if self.client_session:
            await self.client_session.close()
            logger.info("aiohttp 클라이언트 세션이 종료되었습니다.")

    async def _request(self, method: str, path: str, headers: Dict[str, str], json_data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        API 요청을 보내는 내부 메소드.

        Args:
            method (str): HTTP 메소드 ('GET' 또는 'POST').
            path (str): API 엔드포인트 경로.
            headers (Dict[str, str]): 요청 헤더.
            json_data (Optional[Dict[str, Any]]): POST 요청 본문.
            params (Optional[Dict[str, Any]]): GET 요청 쿼리 파라미터.

        Returns:
            Dict[str, Any]: API 응답 데이터.
        
        Raises:
            Exception: API 요청 실패 시.
        """
        if not self.client_session or self.client_session.closed:
            raise RuntimeError("클라이언트 세션이 활성화되지 않았습니다. 'async with' 구문을 사용해주세요.")

        full_url = f"{self.base_url}{path}"
        logger.debug(f"API 요청: {method} {full_url}, Headers: {headers}, Params: {params}, Body: {json_data}")

        # 재시도 로직 추가
        for attempt in range(3): # 최대 3번 재시도
            try:
                async with self.client_session.request(method, full_url, headers=headers, json=json_data, params=params, ssl=False) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.debug(f"API 응답: {result}")
                    
                    # API 자체 에러 코드 확인 (rt_cd가 0이 아닌 경우)
                    if result.get('rt_cd') != '0':
                        error_msg = result.get('msg1', '알 수 없는 API 오류')
                        logger.error(f"API 오류 발생: {error_msg} (rt_cd: {result.get('rt_cd')})")
                        # 특정 오류 코드에 대한 재시도 로직 추가 가능
                    
                    return result
            except aiohttp.ClientResponseError as e:
                logger.warning(f"HTTP 오류 발생 (시도 {attempt+