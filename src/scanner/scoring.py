"""
종목 점수 계산 시스템
10가지 평가 기준으로 종목 점수화
"""

from typing import Dict, Any
from src.utils.config_loader import load_config


class StockScorer:
    """종목 점수 계산기"""

    def __init__(self):
        config = load_config("scanning_rules")
        self.weights = config['scanning']['weights']
        self.criteria = config['scanning']['criteria']
        self.grading = config['scanning']['grading']

    def calculate_score(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """종목 종합 점수 계산"""
        scores = {
            'volume': self._score_volume(stock_data),
            'price': self._score_price(stock_data),
            'foreign_institute': self._score_foreign_institute(stock_data),
            'bid_ask': self._score_bid_ask(stock_data),
            'strength': self._score_strength(stock_data)
        }

        weighted = {k: v * self.weights.get(k, 1.0) for k, v in scores.items()}
        total = sum(weighted.values())
        grade = self._determine_grade(total)

        return {
            'total_score': round(total, 2),
            'grade': grade,
            'scores': scores,
            'weighted_scores': weighted
        }

    def _score_volume(self, data: Dict) -> float:
        """거래량 점수"""
        change = data.get('volume_change_pct', 0)
        for c in self.criteria['volume']:
            if change >= c['threshold']:
                return c['score']
        return 0

    def _score_price(self, data: Dict) -> float:
        """가격 점수"""
        change = data.get('price_change_pct', 0)
        score = 0
        for c in self.criteria['price']:
            if change >= c['threshold']:
                score = c['score']
                break
        prox = data.get('high_proximity_pct', -999)
        for c in self.criteria['price_proximity_to_high']:
            if prox >= c['threshold']:
                score += c['score']
                break
        return score

    def _score_foreign_institute(self, data: Dict) -> float:
        """외국인/기관 점수"""
        score = 0
        foreign_days = data.get('foreign_consecutive_days', 0)
        for c in self.criteria['foreign']:
            if foreign_days >= c['consecutive_days']:
                score += c['score']
                break
        institute = data.get('institute_buy_billion', 0)
        for c in self.criteria['institute']:
            if institute >= c['amount_billion']:
                score += c['score']
                break
        return score

    def _score_bid_ask(self, data: Dict) -> float:
        """호가 강도 점수"""
        ratio = data.get('bid_ask_ratio', 0)
        for c in self.criteria['bid_ask_ratio']:
            if ratio >= c['threshold']:
                return c['score']
        return 0

    def _score_strength(self, data: Dict) -> float:
        """체결 강도 점수"""
        strength = data.get('trade_strength', 0)
        for c in self.criteria['trade_strength']:
            if strength >= c['threshold']:
                return c['score']
        return 0

    def _determine_grade(self, total: float) -> str:
        """등급 결정"""
        if total >= self.grading['s_grade']:
            return 'S'
        elif total >= self.grading['a_grade']:
            return 'A'
        elif total >= self.grading['b_grade']:
            return 'B'
        elif total >= self.grading['c_grade']:
            return 'C'
        return 'D'


__all__ = ["StockScorer"]
