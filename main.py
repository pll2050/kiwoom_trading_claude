"""
키움증권 자동 증권거래 시스템
메인 실행 파일
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any
from src.kiwoom.rest_client import KiwoomRestClient
from src.kiwoom.websocket_client import KiwoomWebSocketClient, RealTimeDataQueue
from src.scanner.stock_scanner import StockScanner
from src.gemini.ai_trader import GeminiAITrader
from src.strategy.trading_strategy import TradingStrategy, PortfolioManager
from src.strategy.dynamic_risk_manager import DynamicRiskManager
from src.utils.logger import logger
from src.utils.config_loader import load_config


class AutoTradingSystem:
    """자동 거래 시스템"""

    def __init__(self):
        self.config = load_config("config")
        self.trading_config = load_config("trading_rules")
        self.scanning_config = load_config("scanning_rules")

        self.api_client = None
        self.ws_client = None
        self.scanner = None
        self.ai_trader = GeminiAITrader()
        self.strategy = TradingStrategy()
        self.portfolio = None
        self.realtime_queue = RealTimeDataQueue()
        self.risk_manager = DynamicRiskManager()

        self.is_running = False
        self.current_prices: Dict[str, float] = {}
        self.current_capital = 0  # 현재 총 자산

        logger.info("=" * 60)
        logger.info("자동 거래 시스템 초기화")
        logger.info("=" * 60)

    async def start(self):
        """시스템 시작"""
        logger.info("시스템 시작")

        try:
            async with KiwoomRestClient() as api_client:
                self.api_client = api_client
                self.scanner = StockScanner(api_client)
                self.portfolio = PortfolioManager(self.strategy)

                # WebSocket 초기화
                self.ws_client = KiwoomWebSocketClient(api_client.access_token)
                await self._setup_websocket_handlers()

                # 계좌 확인
                await self._check_account()

                # 시스템 시작
                self.is_running = True

                # 병렬 실행: 메인 루프 + WebSocket + 포지션 모니터링 + 계좌 모니터링
                tasks = [
                    self._main_loop(),
                    self._monitor_positions(),
                    self._monitor_account(),
                ]

                # WebSocket은 테스트 모드가 아닐 때만 시작
                if self.ws_client is not None:
                    tasks.append(self.ws_client.start())

                await asyncio.gather(*tasks, return_exceptions=True)

        except KeyboardInterrupt:
            logger.info("사용자 중단")
        except Exception as e:
            logger.error(f"시스템 오류: {e}", exc_info=True)
        finally:
            await self._shutdown()

    async def _setup_websocket_handlers(self):
        """WebSocket 핸들러 설정"""
        # 현재가 핸들러
        async def handle_current_price(data):
            stock_code = data.get('stock_code')
            price = data.get('current_price')
            if stock_code and price:
                self.current_prices[stock_code] = price
                await self.realtime_queue.put('current_price', stock_code, data)

        # 주문체결 핸들러
        async def handle_order_execution(data):
            logger.info(f"주문체결: {data}")
            await self.realtime_queue.put('order_execution', 'ALL', data)

        # 잔고 핸들러
        async def handle_balance(data):
            logger.info(f"잔고 업데이트: {data}")
            await self.realtime_queue.put('balance', 'ALL', data)

        self.ws_client.add_handler(KiwoomWebSocketClient.RT_CURRENT_PRICE, handle_current_price)
        self.ws_client.add_handler(KiwoomWebSocketClient.RT_ORDER_EXECUTION, handle_order_execution)
        self.ws_client.add_handler(KiwoomWebSocketClient.RT_BALANCE, handle_balance)

        # 기본 구독
        await self.ws_client.subscribe_order_execution()
        await self.ws_client.subscribe_balance()

        logger.info("WebSocket 핸들러 설정 완료")

    async def _check_account(self):
        """계좌 상태 확인"""
        logger.info("=== 계좌 확인 ===")
        try:
            # API 호출 (테스트/실전 모두 동일)
            balance = await self.api_client.get_balance()
            info = await self.api_client.get_account_info()
            holdings = await self.api_client.get_holdings()

            # 디버깅: 실제 응답 데이터 확인
            logger.debug(f"Balance API 응답: {balance}")
            logger.debug(f"Account Info API 응답: {info}")
            logger.debug(f"Holdings API 응답: {holdings}")

            # 여러 필드명 시도 (API 응답 구조가 다를 수 있음)
            available_cash = (
                balance.get('available_cash') or
                balance.get('entr') or
                balance.get('dnca_tot_amt') or
                balance.get('nass_amt') or
                0
            )

            total_asset = (
                info.get('total_asset') or
                info.get('prsm_dpst_aset_amt') or
                info.get('tot_evlu_amt') or
                0
            )

            logger.info(f"예수금: {int(available_cash):,}원")
            logger.info(f"총자산: {int(total_asset):,}원")
            logger.info(f"보유종목: {len(holdings)}개")

            # 현재 자본금 초기화
            self.current_capital = int(total_asset) if total_asset else int(available_cash)

            # 기존 보유종목 포지션 복원
            for h in holdings:
                code = h.get('stock_code')
                if code and code not in self.strategy.positions:
                    self.strategy.add_position(
                        stock_code=code,
                        stock_name=h.get('stock_name', ''),
                        quantity=h.get('quantity', 0),
                        entry_price=h.get('avg_price', 0)
                    )
                    # 실시간 현재가 구독
                    await self.ws_client.subscribe_current_price(code)

        except Exception as e:
            logger.error(f"계좌 확인 실패: {e}", exc_info=True)

    async def _main_loop(self):
        """메인 루프"""
        logger.info("=== 메인 루프 시작 ===")

        intervals = self.scanning_config['scanning']['intervals']

        tasks = [
            asyncio.create_task(self._fast_scan_loop(intervals['fast_scan'])),
            asyncio.create_task(self._deep_scan_loop(intervals['deep_scan'])),
            asyncio.create_task(self._ai_scan_loop(intervals['ai_analysis']))
        ]

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("중단됨")
            self.is_running = False

    async def _fast_scan_loop(self, interval: int):
        """Fast Scan 루프"""
        while self.is_running:
            try:
                logger.info(f"[{datetime.now():%H:%M:%S}] Fast Scan")
                stocks = await self.scanner.fast_scan()
                logger.info(f"결과: {len(stocks)}개")
            except Exception as e:
                logger.error(f"Fast Scan 오류: {e}", exc_info=True)
            await asyncio.sleep(interval)

    async def _deep_scan_loop(self, interval: int):
        """Deep Scan 루프"""
        await asyncio.sleep(5)
        while self.is_running:
            try:
                logger.info(f"[{datetime.now():%H:%M:%S}] Deep Scan")
                fast_result = await self.scanner.fast_scan()
                deep_result = await self.scanner.deep_scan(fast_result)

                logger.info(f"결과: {len(deep_result)}개 (200점+)")
                for s in deep_result[:5]:
                    logger.info(
                        f"  - {s.get('name')} ({s.get('code')}): "
                        f"{s.get('total_score')}점 [{s.get('grade')}]"
                    )
            except Exception as e:
                logger.error(f"Deep Scan 오류: {e}", exc_info=True)
            await asyncio.sleep(interval)

    async def _ai_scan_loop(self, interval: int):
        """AI Scan 루프"""
        await asyncio.sleep(10)
        while self.is_running:
            try:
                logger.info(f"[{datetime.now():%H:%M:%S}] AI Scan")
                fast = await self.scanner.fast_scan()
                deep = await self.scanner.deep_scan(fast)
                ai_result = await self.ai_trader.analyze_multiple_stocks(deep[:10])

                # 동적 리스크 관리: 현재 모드에 맞는 AI 신뢰도 필터링
                min_confidence = self.risk_manager.get_ai_confidence_min()

                buy_recs = [
                    s for s in ai_result
                    if s['ai_analysis'].get('recommendation') == 'BUY'
                    and s['ai_analysis'].get('confidence', 0) >= min_confidence
                ]

                logger.info(f"매수 추천: {len(buy_recs)}개 (AI 신뢰도 {min_confidence*100:.0f}% 이상)")

                for s in buy_recs[:3]:
                    ai = s['ai_analysis']
                    logger.info(
                        f"  [매수] {s.get('name')} ({s.get('code')})\n"
                        f"    - 확률: {ai.get('probability')}%\n"
                        f"    - 목표가: {ai.get('target_price'):,}원\n"
                        f"    - 신뢰도: {ai.get('confidence'):.2f}\n"
                        f"    - 이유: {ai.get('reason')}"
                    )

                if buy_recs:
                    await self._execute_trades(buy_recs[:5])

            except Exception as e:
                logger.error(f"AI Scan 오류: {e}", exc_info=True)
            await asyncio.sleep(interval)

    async def _execute_trades(self, stocks: List):
        """매수 실행 (동적 리스크 관리 적용)"""
        try:
            # 매수 시도/성공 카운터
            attempt_count = len(stocks)
            success_count = 0

            logger.info("=" * 60)
            logger.info(f"📋 매수 시도: {attempt_count}개 종목")
            logger.info("=" * 60)

            # 현재 포지션 수
            num_positions = len(self.strategy.positions)

            for s in stocks:
                try:
                    code = s['code']
                    name = s.get('name', '')
                    ai_confidence = s.get('ai_analysis', {}).get('confidence', 0)

                    # 동적 리스크 관리: 매수 가능 여부 확인
                    risk_decision = self.risk_manager.should_buy(
                        self.current_capital,
                        num_positions,
                        ai_confidence
                    )

                    if not risk_decision['decision']:
                        logger.warning(
                            f"[{risk_decision['mode']}] 매수 불가 ({name}): {risk_decision['reason']}"
                        )
                        continue

                    # 기존 전략 매수 판단
                    decision = self.strategy.should_buy(s)
                    if not decision['decision']:
                        logger.warning(f"매수 불가 ({name}): {decision['reason']}")
                        continue

                    # 현재가 조회 (테스트 모드에서도 Mock API 호출)
                    quote = await self.api_client.get_quote(code)
                    price = quote.get('price', 0)
                    if price == 0:
                        logger.warning(f"가격 정보 없음: {name}")
                        continue

                    # 동적 리스크 관리: 포지션 크기 계산
                    qty = self.risk_manager.calculate_position_size(self.current_capital, price)
                    if qty <= 0:
                        logger.warning(f"매수 수량 0: {name}")
                        continue

                    # 주문 실행 (테스트 모드에서도 Mock API 호출)
                    await self.api_client.order_buy(code, qty, price)

                    investment_amount = price * qty
                    position_pct = (investment_amount / self.current_capital * 100) if self.current_capital > 0 else 0

                    logger.info(
                        f"✅ [{risk_decision['mode']}] 매수 주문 성공: {name} {qty}주 @{price:,}원 "
                        f"(투자: {investment_amount:,}원, {position_pct:.1f}%)"
                    )

                    # 포지션 추가
                    self.strategy.add_position(code, name, qty, price)

                    # 실시간 현재가 구독
                    await self.ws_client.subscribe_current_price(code)

                    # 포지션 수 증가
                    num_positions += 1
                    success_count += 1

                except Exception as e:
                    logger.error(f"❌ 매수 실패 ({s.get('name')}): {e}", exc_info=True)

            # 매수 결과 요약
            logger.info("=" * 60)
            logger.info(f"✅ 매수 완료: {success_count}/{attempt_count}개 성공")
            if success_count < attempt_count:
                logger.warning(f"⚠️  매수 실패: {attempt_count - success_count}개")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"매수 실행 오류: {e}", exc_info=True)

    async def _monitor_account(self):
        """계좌 모니터링 (잔고, 보유종목 조회)"""
        await asyncio.sleep(15)  # 초기 대기

        interval = self.config.get('monitoring', {}).get('account_check_interval', 10)

        while self.is_running:
            try:
                logger.info("=" * 60)
                logger.info(f"[{datetime.now():%H:%M:%S}] 계좌 조회")
                logger.info("=" * 60)

                # API 호출 (테스트/실전 모두 동일)
                balance = await self.api_client.get_balance()
                entr = int(balance.get('entr', '0'))  # 예수금
                logger.info(f"💰 예수금: {entr:,}원")

                # 계좌 정보 조회
                info = await self.api_client.get_account_info()
                prsm_dpst_aset_amt = int(info.get('prsm_dpst_aset_amt', '0'))  # 추정예탁자산

                # 현재 총 자산 업데이트
                self.current_capital = prsm_dpst_aset_amt
                logger.info(f"📊 총자산: {prsm_dpst_aset_amt:,}원")

                # 보유 종목 조회
                holdings = await self.api_client.get_holdings()

                # 투자원금 = 보유종목의 매수금액 합계
                total_investment = 0
                total_valuation = 0

                # API 응답 데이터 사용
                for h in holdings:
                    qty = int(h.get('remn_qty', '0'))  # 잔고수량
                    avg_price = float(h.get('avg_unpr', '0'))  # 평단가
                    current_price = float(h.get('prsn_rate', avg_price))  # 현재가

                    total_investment += avg_price * qty  # 매수금액
                    total_valuation += current_price * qty  # 평가금액

                # 손익 계산
                total_pnl = total_valuation - total_investment
                pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0

                if total_investment > 0:
                    logger.info(f"💼 투자원금: {int(total_investment):,}원")
                    logger.info(f"💹 평가금액: {int(total_valuation):,}원")
                    logger.info(f"📈 총손익: {int(total_pnl):+,}원 ({pnl_pct:+.2f}%)")

                logger.info(f"📋 보유종목: {len(holdings)}개")

                # 동적 리스크 관리 상태 업데이트 및 표시
                self.risk_manager.update_risk_level(self.current_capital)
                risk_status = self.risk_manager.get_current_status()

                logger.info("-" * 60)
                logger.info(f"⚙️  투자 모드: {risk_status['mode_name']} (원금 대비 {risk_status['capital_ratio']*100:.1f}%)")
                logger.info(f"   최대 포지션: {risk_status['max_positions']}개 | 종목당: {risk_status['position_size_pct']:.1f}%")
                logger.info(f"   손절/익절: {risk_status['stop_loss_pct']:+.1f}% / {risk_status['take_profit_pct']:+.1f}%")
                logger.info(f"   AI 신뢰도: {risk_status['ai_confidence_min']*100:.0f}% 이상")
                logger.info("-" * 60)

                if holdings:
                    logger.info("-" * 60)
                    for i, h in enumerate(holdings, 1):
                        # API 응답 데이터 사용
                        code = h.get('sht_cd', '')  # 단축코드
                        name = h.get('pdno_hngl_nm', '')  # 상품명
                        qty = int(h.get('remn_qty', '0'))  # 잔고수량
                        avg_price = float(h.get('avg_unpr', '0'))  # 평단가
                        current_price = float(h.get('prsn_rate', avg_price))  # 현재가

                        investment = avg_price * qty  # 매수금액
                        valuation = current_price * qty  # 평가금액
                        pnl = valuation - investment  # 손익
                        pnl_pct = (pnl / investment * 100) if investment > 0 else 0

                        logger.info(
                            f"{i}. {name}({code}) "
                            f"{qty}주 @{int(avg_price):,}원 → {int(current_price):,}원 | "
                            f"투자: {int(investment):,}원 → 평가: {int(valuation):,}원 "
                            f"({int(pnl):+,}원, {pnl_pct:+.2f}%)"
                        )
                    logger.info("-" * 60)

                logger.info("=" * 60)

            except Exception as e:
                logger.error(f"계좌 모니터링 오류: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def _monitor_positions(self):
        """포지션 모니터링 (손익 체크)"""
        await asyncio.sleep(20)  # 초기 대기

        while self.is_running:
            try:
                # 포지션 손익 체크
                sell_signals = self.portfolio.check_all_positions(self.current_prices)

                if sell_signals:
                    logger.info("=" * 60)
                    logger.info(f"📋 매도 신호: {len(sell_signals)}개 종목")
                    logger.info("=" * 60)

                sell_success_count = 0
                sell_attempt_count = len(sell_signals)

                for signal in sell_signals:
                    position = signal['position']
                    decision = signal['decision']

                    logger.info(
                        f"매도 신호: {position.stock_name} "
                        f"사유={decision['reason']} "
                        f"손익={decision['pnl_pct']:+.2f}%"
                    )

                    # 매도 실행
                    success = await self._execute_sell(position, decision['price'])
                    if success:
                        sell_success_count += 1

                # 매도 결과 요약
                if sell_signals:
                    logger.info("=" * 60)
                    logger.info(f"✅ 매도 완료: {sell_success_count}/{sell_attempt_count}개 성공")
                    if sell_success_count < sell_attempt_count:
                        logger.warning(f"⚠️  매도 실패: {sell_attempt_count - sell_success_count}개")
                    logger.info("=" * 60)

                # 포트폴리오 요약 출력 (5분마다)
                if datetime.now().minute % 5 == 0:
                    await self._log_portfolio_summary()

                await asyncio.sleep(10)  # 10초마다 체크

            except Exception as e:
                logger.error(f"포지션 모니터링 오류: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def _execute_sell(self, position: Any, price: float) -> bool:
        """매도 실행"""
        try:
            # 주문 실행 (테스트 모드에서도 Mock API 호출)
            await self.api_client.order_sell(
                position.stock_code,
                position.quantity,
                int(price)
            )

            logger.info(
                f"✅ 매도 주문 성공: {position.stock_name} "
                f"{position.quantity}주 @{price:,}원"
            )

            # 포지션 제거
            realized_pnl = self.strategy.remove_position(position.stock_code, price)

            # 실시간 구독 해제
            await self.ws_client.unsubscribe(
                KiwoomWebSocketClient.RT_CURRENT_PRICE,
                position.stock_code
            )

            return True

        except Exception as e:
            logger.error(f"❌ 매도 실패 ({position.stock_name}): {e}", exc_info=True)
            return False

    async def _log_portfolio_summary(self):
        """포트폴리오 요약 로그"""
        try:
            summary = self.portfolio.get_portfolio_summary(self.current_prices)

            logger.info("=" * 60)
            logger.info("포트폴리오 요약")
            logger.info(f"포지션 수: {summary['position_count']}개")
            logger.info(f"총 투자금: {summary['total_investment']:,.0f}원")
            logger.info(f"평가손익: {summary['total_pnl']:+,.0f}원 ({summary['total_pnl_pct']:+.2f}%)")
            logger.info(f"실현손익: {summary['daily_realized_pnl']:+,.0f}원")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"포트폴리오 요약 오류: {e}", exc_info=True)

    async def _shutdown(self):
        """시스템 종료"""
        logger.info("시스템 종료 중...")
        self.is_running = False

        if self.ws_client:
            await self.ws_client.disconnect()

        logger.info("시스템 종료 완료")


async def main():
    """메인 함수"""
    system = AutoTradingSystem()
    await system.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n종료")
    except Exception as e:
        logger.error(f"오류: {e}", exc_info=True)
