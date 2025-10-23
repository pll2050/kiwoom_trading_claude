"""
종목 스캐닝 엔진
Fast Scan -> Deep Scan -> AI Scan
"""

import asyncio
from typing import List, Dict, Any
from src.kiwoom.rest_client import KiwoomRestClient
from src.scanner.scoring import StockScorer
from src.utils.config_loader import load_config
from src.utils.logger import logger


class StockScanner:
    """종목 스캐닝 엔진"""

    def __init__(self, api_client: KiwoomRestClient):
        self.api = api_client
        self.scorer = StockScorer()

        config = load_config("scanning_rules")
        self.min_trading_value = config['scanning']['filters']['min_trading_value']
        self.exclude_conditions = config['scanning']['filters']['exclude_conditions']
        self.ai_min_score = config['scanning']['grading']['ai_analysis_min_score']

        logger.info("스캐너 초기화")

    async def fast_scan(self) -> List[Dict[str, Any]]:
        """Fast Scan: 거래량/가격 기본 스크리닝"""
        logger.info("=== Fast Scan ===")

        # Rate Limit 회피를 위해 순차적으로 호출
        all_stocks = []

        try:
            # 1. 거래량 급증
            surge_stocks = await self.api.get_volume_surge_stocks(100)
            all_stocks.extend(surge_stocks)
        except Exception as e:
            logger.warning(f"거래량 급증 조회 실패: {e}")

        try:
            # 2. 거래량 상위
            volume_stocks = await self.api.get_volume_leaders(100)
            all_stocks.extend(volume_stocks)
        except Exception as e:
            logger.warning(f"거래량 상위 조회 실패: {e}")

        try:
            # 3. 거래대금 상위
            turnover_stocks = await self.api.get_turnover_leaders(100)
            all_stocks.extend(turnover_stocks)
        except Exception as e:
            logger.warning(f"거래대금 상위 조회 실패: {e}")

        try:
            # 4. 등락률 상위
            price_stocks = await self.api.get_price_change_leaders(100)
            all_stocks.extend(price_stocks)
        except Exception as e:
            logger.warning(f"등락률 상위 조회 실패: {e}")

        unique = {s['code']: s for s in all_stocks}.values()
        filtered = self._apply_basic_filters(list(unique))
        top_50 = sorted(filtered, key=lambda x: x.get('trading_value', 0), reverse=True)[:50]

        logger.info(f"Fast Scan 완료: {len(top_50)}개")
        return top_50

    async def deep_scan(self, stocks: List[Dict]) -> List[Dict]:
        """Deep Scan: 상세 분석 및 점수 계산 (배치 처리)"""
        logger.info(f"=== Deep Scan: {len(stocks)}개 ===")

        batch_size = 10  # 한 번에 10개씩 처리
        scored = []

        # 배치로 나눠서 처리
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i+batch_size]
            logger.info(f"배치 {i//batch_size + 1}/{(len(stocks)-1)//batch_size + 1} 처리 중 ({len(batch)}개)...")

            for stock in batch:
                try:
                    data = await self._collect_detailed_data(stock)
                    score_result = self.scorer.calculate_score(data)

                    stock['score_info'] = score_result
                    stock['total_score'] = score_result['total_score']
                    stock['grade'] = score_result['grade']
                    scored.append(stock)

                except Exception as e:
                    logger.error(f"점수 계산 실패 ({stock.get('code')}): {e}")
                    continue

            # 배치 사이에 추가 대기 (Rate Limit 여유)
            if i + batch_size < len(stocks):
                await asyncio.sleep(3.0)
                logger.info(f"다음 배치 전 3초 대기...")

        # 점수별 통계
        if scored:
            avg_score = sum(s['total_score'] for s in scored) / len(scored)
            max_score = max(s['total_score'] for s in scored)
            min_score = min(s['total_score'] for s in scored)
            logger.info(f"점수 통계 - 평균: {avg_score:.1f}, 최고: {max_score}, 최저: {min_score}")

        # 200점 이상이 있으면 우선 선택, 없으면 상위 20개 선택
        qualified = [s for s in scored if s['total_score'] >= 200]
        if len(qualified) >= 20:
            top_20 = sorted(qualified, key=lambda x: x['total_score'], reverse=True)[:20]
            logger.info(f"Deep Scan 완료: 200점 이상 {len(qualified)}개 중 상위 20개 선택")
        else:
            top_20 = sorted(scored, key=lambda x: x['total_score'], reverse=True)[:20]
            logger.info(f"Deep Scan 완료: 200점 이상 {len(qualified)}개뿐 → 전체 중 상위 {len(top_20)}개 선택")

        return top_20

    def _apply_basic_filters(self, stocks: List[Dict]) -> List[Dict]:
        """기본 필터링"""
        filtered = []
        for s in stocks:
            if s.get('trading_value', 0) < self.min_trading_value:
                continue
            if any(c in s.get('status', '') for c in self.exclude_conditions):
                continue
            filtered.append(s)
        return filtered

    async def _collect_detailed_data(self, stock: Dict) -> Dict:
        """종목 상세 데이터 수집"""
        code = stock['code']
        try:
            quote = await self.api.get_quote(code)
            orderbook = await self.api.get_orderbook(code)

            return {
                **stock,
                'current_price': quote.get('price', 0),
                'volume_change_pct': stock.get('volume_change', 0),
                'price_change_pct': stock.get('price_change', 0),
                'high_proximity_pct': quote.get('high_proximity', 0),
                'foreign_consecutive_days': stock.get('foreign_days', 0),
                'institute_buy_billion': stock.get('institute_buy', 0) / 100000000,
                'bid_ask_ratio': self._calc_bid_ask_ratio(orderbook),
                'trade_strength': quote.get('strength', 100),
            }
        except Exception as e:
            logger.error(f"데이터 수집 실패 ({code}): {e}")
            return stock

    def _calc_bid_ask_ratio(self, orderbook: Dict) -> float:
        """호가 비율 계산"""
        try:
            bid = sum(b.get('volume', 0) for b in orderbook.get('bids', []))
            ask = sum(a.get('volume', 0) for a in orderbook.get('asks', []))
            return (bid / ask) * 100 if ask > 0 else 0
        except:
            return 0


__all__ = ["StockScanner"]
