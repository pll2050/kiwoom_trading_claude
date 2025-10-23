"""
거래 전략
매수/매도 신호 생성, 손절/익절, 포지션 관리
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from src.utils.config_loader import load_config
from src.utils.logger import logger


class TradingStrategy:
    """거래 전략"""

    def __init__(self):
        self.trading_config = load_config("trading_rules")
        self.config = load_config("config")

        # 손익 설정
        self.stop_loss_pct = self.trading_config['profit_loss']['stop_loss_percentage']
        self.take_profit_pct = self.trading_config['profit_loss']['take_profit_percentage']

        # 투자 한도
        self.max_investment_per_stock = self.config['trading']['max_investment_per_stock']
        self.max_daily_loss = self.config['trading']['max_daily_loss']
        self.max_positions = self.trading_config['risk_management']['max_positions']

        # 거래 시간
        self.market_open = self.trading_config['trading_hours']['market_open']
        self.new_buy_close = self.trading_config['trading_hours']['new_buy_close']
        self.market_close = self.trading_config['trading_hours']['market_close']

        # 포지션 관리
        self.positions: Dict[str, Position] = {}
        self.daily_realized_pnl = 0.0

        logger.info("거래 전략 초기화")

    def should_buy(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """매수 판단"""
        # 기본 체크
        checks = {
            'time_check': self._check_trading_time(),
            'position_limit': len(self.positions) < self.max_positions,
            'daily_loss_limit': self.daily_realized_pnl > -self.max_daily_loss,
            'score_check': stock_data.get('total_score', 0) >= 200,
            'ai_check': False
        }

        # AI 분석 체크
        ai_analysis = stock_data.get('ai_analysis', {})
        if ai_analysis:
            checks['ai_check'] = (
                ai_analysis.get('recommendation') == 'BUY' and
                ai_analysis.get('confidence', 0) >= 0.7 and
                ai_analysis.get('probability', 0) >= 60
            )

        should_buy = all(checks.values())

        return {
            'decision': should_buy,
            'checks': checks,
            'reason': self._get_buy_reason(checks)
        }

    def should_sell(self, position: 'Position', current_price: float) -> Dict[str, Any]:
        """매도 판단"""
        pnl_pct = position.get_pnl_percentage(current_price)

        # 손절 체크
        if pnl_pct <= self.stop_loss_pct:
            return {
                'decision': True,
                'reason': 'STOP_LOSS',
                'pnl_pct': pnl_pct,
                'price': current_price
            }

        # 익절 체크
        if pnl_pct >= self.take_profit_pct:
            return {
                'decision': True,
                'reason': 'TAKE_PROFIT',
                'pnl_pct': pnl_pct,
                'price': current_price
            }

        # 장 마감 임박 (15:10 이후)
        if self._is_market_closing():
            return {
                'decision': True,
                'reason': 'MARKET_CLOSING',
                'pnl_pct': pnl_pct,
                'price': current_price
            }

        return {
            'decision': False,
            'reason': 'HOLD',
            'pnl_pct': pnl_pct,
            'price': current_price
        }

    def calculate_position_size(
        self,
        stock_price: float,
        available_cash: float,
        stock_data: Dict[str, Any]
    ) -> int:
        """포지션 크기 계산 (매수 수량)"""
        # 종목당 최대 투자금액과 가용 현금 중 작은 값
        max_investment = min(self.max_investment_per_stock, available_cash)

        # 기본 수량
        quantity = int(max_investment / stock_price)

        # AI 신뢰도에 따른 조정
        ai_analysis = stock_data.get('ai_analysis', {})
        confidence = ai_analysis.get('confidence', 0.5)

        if confidence >= 0.9:
            # 고신뢰도: 100%
            pass
        elif confidence >= 0.8:
            # 중신뢰도: 80%
            quantity = int(quantity * 0.8)
        elif confidence >= 0.7:
            # 저신뢰도: 60%
            quantity = int(quantity * 0.6)
        else:
            # 매우 낮음: 매수 안함
            quantity = 0

        return max(0, quantity)

    def add_position(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        entry_price: float
    ) -> 'Position':
        """포지션 추가"""
        position = Position(
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=datetime.now()
        )

        self.positions[stock_code] = position
        logger.info(f"포지션 추가: {stock_name} {quantity}주 @{entry_price}원")
        return position

    def remove_position(self, stock_code: str, exit_price: float) -> Optional[float]:
        """포지션 제거 및 손익 계산"""
        if stock_code not in self.positions:
            return None

        position = self.positions[stock_code]
        realized_pnl = position.get_realized_pnl(exit_price)
        self.daily_realized_pnl += realized_pnl

        logger.info(
            f"포지션 청산: {position.stock_name} "
            f"손익={realized_pnl:+,.0f}원 ({position.get_pnl_percentage(exit_price):+.2f}%)"
        )

        del self.positions[stock_code]
        return realized_pnl

    def get_position(self, stock_code: str) -> Optional['Position']:
        """포지션 조회"""
        return self.positions.get(stock_code)

    def get_all_positions(self) -> List['Position']:
        """모든 포지션 조회"""
        return list(self.positions.values())

    def reset_daily_pnl(self):
        """일일 손익 초기화 (매일 장 시작 전)"""
        self.daily_realized_pnl = 0.0
        logger.info("일일 손익 초기화")

    def _check_trading_time(self) -> bool:
        """거래 가능 시간 체크"""
        now = datetime.now().time()
        market_open = datetime.strptime(self.market_open, "%H:%M:%S").time()
        new_buy_close = datetime.strptime(self.new_buy_close, "%H:%M:%S").time()

        return market_open <= now <= new_buy_close

    def _is_market_closing(self) -> bool:
        """장 마감 임박 체크 (15:10 이후)"""
        now = datetime.now().time()
        closing_time = datetime.strptime("15:10:00", "%H:%M:%S").time()
        return now >= closing_time

    def _get_buy_reason(self, checks: Dict[str, bool]) -> str:
        """매수 가능/불가 사유"""
        if all(checks.values()):
            return "모든 조건 충족"

        reasons = []
        if not checks['time_check']:
            reasons.append("거래시간 외")
        if not checks['position_limit']:
            reasons.append("최대 포지션 초과")
        if not checks['daily_loss_limit']:
            reasons.append("일일 손실 한도 초과")
        if not checks['score_check']:
            reasons.append("스코어 부족")
        if not checks['ai_check']:
            reasons.append("AI 신뢰도 부족")

        return ", ".join(reasons)


class Position:
    """포지션 정보"""

    def __init__(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        entry_price: float,
        entry_time: datetime
    ):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = entry_time

        # 손절/익절가
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0

    def get_pnl(self, current_price: float) -> float:
        """평가 손익 (원)"""
        return (current_price - self.entry_price) * self.quantity

    def get_pnl_percentage(self, current_price: float) -> float:
        """평가 손익률 (%)"""
        if self.entry_price == 0:
            return 0.0
        return ((current_price - self.entry_price) / self.entry_price) * 100

    def get_realized_pnl(self, exit_price: float) -> float:
        """실현 손익 (원)"""
        return (exit_price - self.entry_price) * self.quantity

    def get_total_investment(self) -> float:
        """총 투자금액"""
        return self.entry_price * self.quantity

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'investment': self.get_total_investment()
        }

    def __repr__(self):
        return (
            f"Position(code={self.stock_code}, name={self.stock_name}, "
            f"qty={self.quantity}, price={self.entry_price})"
        )


class PortfolioManager:
    """포트폴리오 관리"""

    def __init__(self, strategy: TradingStrategy):
        self.strategy = strategy

    def get_total_investment(self) -> float:
        """총 투자금액"""
        return sum(p.get_total_investment() for p in self.strategy.get_all_positions())

    def get_total_pnl(self, current_prices: Dict[str, float]) -> float:
        """총 평가손익"""
        total = 0.0
        for position in self.strategy.get_all_positions():
            current_price = current_prices.get(position.stock_code, position.entry_price)
            total += position.get_pnl(current_price)
        return total

    def get_total_pnl_percentage(self, current_prices: Dict[str, float]) -> float:
        """총 평가손익률 (%)"""
        total_investment = self.get_total_investment()
        if total_investment == 0:
            return 0.0
        total_pnl = self.get_total_pnl(current_prices)
        return (total_pnl / total_investment) * 100

    def get_portfolio_summary(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """포트폴리오 요약"""
        positions = self.strategy.get_all_positions()

        position_details = []
        for p in positions:
            current_price = current_prices.get(p.stock_code, p.entry_price)
            position_details.append({
                'code': p.stock_code,
                'name': p.stock_name,
                'quantity': p.quantity,
                'entry_price': p.entry_price,
                'current_price': current_price,
                'pnl': p.get_pnl(current_price),
                'pnl_pct': p.get_pnl_percentage(current_price),
                'investment': p.get_total_investment()
            })

        return {
            'position_count': len(positions),
            'total_investment': self.get_total_investment(),
            'total_pnl': self.get_total_pnl(current_prices),
            'total_pnl_pct': self.get_total_pnl_percentage(current_prices),
            'daily_realized_pnl': self.strategy.daily_realized_pnl,
            'positions': position_details
        }

    def check_all_positions(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """모든 포지션 손익 체크"""
        sell_signals = []

        for position in self.strategy.get_all_positions():
            current_price = current_prices.get(position.stock_code)
            if not current_price:
                continue

            sell_decision = self.strategy.should_sell(position, current_price)
            if sell_decision['decision']:
                sell_signals.append({
                    'position': position,
                    'decision': sell_decision
                })

        return sell_signals


__all__ = ["TradingStrategy", "Position", "PortfolioManager"]
