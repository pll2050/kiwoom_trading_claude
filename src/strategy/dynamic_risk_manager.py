"""
동적 리스크 관리 시스템
원금 대비 잔고 비율에 따라 투자 전략을 동적으로 조정
"""

from typing import Dict, Any
from src.utils.config_loader import load_config
from src.utils.logger import logger


class DynamicRiskManager:
    """원금 기반 동적 리스크 관리"""

    def __init__(self):
        self.config = load_config("config")
        self.trading_config = self.config['trading']
        self.initial_capital = self.trading_config['initial_capital']
        self.dynamic_config = self.trading_config['dynamic_risk_management']
        self.enabled = self.dynamic_config['enabled']

        self.current_mode = "normal_mode"
        self.mode_params = {}

        logger.info(f"동적 리스크 관리 초기화 - 원금: {self.initial_capital:,}원")
        logger.info(f"동적 리스크 관리: {'활성화' if self.enabled else '비활성화'}")

    def update_risk_level(self, current_capital: float) -> Dict[str, Any]:
        """
        현재 자본금에 따라 리스크 레벨 업데이트

        Args:
            current_capital: 현재 총 자산 (예수금 + 보유종목 평가액)

        Returns:
            현재 모드의 파라미터
        """
        if not self.enabled:
            # 동적 관리 비활성화 시 기본값 반환
            return self._get_default_params()

        # 원금 대비 비율 계산
        capital_ratio = current_capital / self.initial_capital

        # 비율에 따라 모드 결정
        mode = self._determine_mode(capital_ratio)

        # 모드 변경 시 로그
        if mode != self.current_mode:
            old_mode = self.current_mode
            self.current_mode = mode
            logger.warning(
                f"🔄 투자 모드 변경: {self._mode_name(old_mode)} → {self._mode_name(mode)} "
                f"(원금 대비 {capital_ratio*100:.1f}%)"
            )

        # 현재 모드 파라미터 반환
        self.mode_params = self.dynamic_config[mode].copy()
        self.mode_params['capital_ratio'] = capital_ratio
        self.mode_params['mode_name'] = self._mode_name(mode)

        return self.mode_params

    def _determine_mode(self, capital_ratio: float) -> str:
        """자본 비율에 따라 모드 결정"""
        if capital_ratio >= 1.00:
            return "profit_mode"
        elif capital_ratio >= 0.90:
            return "normal_mode"
        elif capital_ratio >= 0.80:
            return "conservative_mode"
        else:
            return "very_conservative_mode"

    def _mode_name(self, mode: str) -> str:
        """모드 이름을 한글로 변환"""
        names = {
            "profit_mode": "공격적 (수익)",
            "normal_mode": "정상",
            "conservative_mode": "보수적",
            "very_conservative_mode": "매우 보수적"
        }
        return names.get(mode, mode)

    def _get_default_params(self) -> Dict[str, Any]:
        """기본 파라미터 반환 (동적 관리 비활성화 시)"""
        return {
            'max_positions': 10,
            'position_size_pct': 5.0,
            'stop_loss_pct': -3.0,
            'take_profit_pct': 5.0,
            'ai_confidence_min': 0.75,
            'capital_ratio': 1.0,
            'mode_name': '기본'
        }

    def get_max_positions(self) -> int:
        """최대 포지션 수 반환"""
        return self.mode_params.get('max_positions', 10)

    def get_position_size_pct(self) -> float:
        """종목당 투자 비율 반환"""
        return self.mode_params.get('position_size_pct', 5.0)

    def get_stop_loss_pct(self) -> float:
        """손절 비율 반환"""
        return self.mode_params.get('stop_loss_pct', -3.0)

    def get_take_profit_pct(self) -> float:
        """익절 비율 반환"""
        return self.mode_params.get('take_profit_pct', 5.0)

    def get_ai_confidence_min(self) -> float:
        """최소 AI 신뢰도 반환"""
        return self.mode_params.get('ai_confidence_min', 0.75)

    def calculate_position_size(self, current_capital: float, stock_price: float) -> int:
        """
        포지션 크기 계산

        Args:
            current_capital: 현재 총 자산
            stock_price: 주식 가격

        Returns:
            매수할 주식 수량
        """
        # 투자 가능 금액 = 현재 자산 * 종목당 비율
        position_size_pct = self.get_position_size_pct() / 100
        investment_amount = current_capital * position_size_pct

        # 수량 계산
        quantity = int(investment_amount / stock_price)

        return quantity

    def should_buy(self, current_capital: float, num_positions: int, ai_confidence: float) -> Dict[str, Any]:
        """
        매수 가능 여부 판단

        Args:
            current_capital: 현재 총 자산
            num_positions: 현재 보유 포지션 수
            ai_confidence: AI 신뢰도

        Returns:
            매수 가능 여부 및 사유
        """
        # 리스크 레벨 업데이트
        self.update_risk_level(current_capital)

        # 최대 포지션 수 체크
        max_positions = self.get_max_positions()
        if num_positions >= max_positions:
            return {
                'decision': False,
                'reason': f'최대 포지션 수 도달 ({num_positions}/{max_positions})',
                'mode': self.mode_params.get('mode_name', '')
            }

        # AI 신뢰도 체크
        min_confidence = self.get_ai_confidence_min()
        if ai_confidence < min_confidence:
            return {
                'decision': False,
                'reason': f'AI 신뢰도 부족 ({ai_confidence:.2f} < {min_confidence:.2f})',
                'mode': self.mode_params.get('mode_name', '')
            }

        return {
            'decision': True,
            'reason': '매수 조건 충족',
            'mode': self.mode_params.get('mode_name', ''),
            'max_positions': max_positions,
            'position_size_pct': self.get_position_size_pct()
        }

    def get_current_status(self) -> Dict[str, Any]:
        """현재 리스크 관리 상태 반환"""
        return {
            'enabled': self.enabled,
            'initial_capital': self.initial_capital,
            'current_mode': self.current_mode,
            'mode_name': self.mode_params.get('mode_name', ''),
            'capital_ratio': self.mode_params.get('capital_ratio', 1.0),
            'max_positions': self.get_max_positions(),
            'position_size_pct': self.get_position_size_pct(),
            'stop_loss_pct': self.get_stop_loss_pct(),
            'take_profit_pct': self.get_take_profit_pct(),
            'ai_confidence_min': self.get_ai_confidence_min()
        }


__all__ = ["DynamicRiskManager"]
