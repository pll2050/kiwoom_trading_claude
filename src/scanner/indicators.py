"""
기술적 지표 계산
RSI, MACD, 이동평균, 볼린저밴드, 스토캐스틱 등
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional


class TechnicalIndicators:
    """기술적 지표 계산기"""

    @staticmethod
    def calculate_all(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """모든 지표 계산"""
        if not candles or len(candles) < 20:
            return TechnicalIndicators._default_indicators()

        df = pd.DataFrame(candles)

        # 필수 컬럼 확인
        required = ['close', 'high', 'low', 'volume']
        if not all(col in df.columns for col in required):
            return TechnicalIndicators._default_indicators()

        try:
            result = {
                'rsi': TechnicalIndicators.rsi(df['close']),
                'macd': TechnicalIndicators.macd(df['close']),
                'moving_averages': TechnicalIndicators.moving_averages(df['close']),
                'bollinger_bands': TechnicalIndicators.bollinger_bands(df['close']),
                'stochastic': TechnicalIndicators.stochastic(df['high'], df['low'], df['close']),
                'volume_ma': TechnicalIndicators.volume_moving_average(df['volume']),
                'adx': TechnicalIndicators.adx(df['high'], df['low'], df['close']),
                'cci': TechnicalIndicators.cci(df['high'], df['low'], df['close'])
            }
            return result

        except Exception as e:
            return TechnicalIndicators._default_indicators()

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> Dict[str, float]:
        """
        RSI (Relative Strength Index)

        Returns:
            {
                'value': 현재 RSI 값 (0-100),
                'signal': 'OVERBOUGHT' | 'OVERSOLD' | 'NEUTRAL'
            }
        """
        if len(close) < period + 1:
            return {'value': 50.0, 'signal': 'NEUTRAL'}

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

        # 신호 판단
        if current_rsi >= 70:
            signal = 'OVERBOUGHT'  # 과매수
        elif current_rsi <= 30:
            signal = 'OVERSOLD'    # 과매도
        else:
            signal = 'NEUTRAL'

        return {
            'value': round(current_rsi, 2),
            'signal': signal
        }

    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """
        MACD (Moving Average Convergence Divergence)

        Returns:
            {
                'macd': MACD 라인,
                'signal': 시그널 라인,
                'histogram': 히스토그램,
                'trend': 'BULLISH' | 'BEARISH' | 'NEUTRAL'
            }
        """
        if len(close) < slow + signal:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0, 'trend': 'NEUTRAL'}

        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        current_macd = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0.0
        current_signal = float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else 0.0
        current_histogram = float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0.0

        # 추세 판단
        if current_histogram > 0 and current_macd > current_signal:
            trend = 'BULLISH'  # 상승 추세
        elif current_histogram < 0 and current_macd < current_signal:
            trend = 'BEARISH'  # 하락 추세
        else:
            trend = 'NEUTRAL'

        return {
            'macd': round(current_macd, 2),
            'signal': round(current_signal, 2),
            'histogram': round(current_histogram, 2),
            'trend': trend
        }

    @staticmethod
    def moving_averages(close: pd.Series) -> Dict[str, Any]:
        """
        이동평균선 (5일, 20일, 60일, 120일)

        Returns:
            {
                'ma5': 5일 이동평균,
                'ma20': 20일 이동평균,
                'ma60': 60일 이동평균,
                'ma120': 120일 이동평균,
                'current_price': 현재가,
                'golden_cross': 골든크로스 여부,
                'dead_cross': 데드크로스 여부,
                'alignment': 'BULLISH' | 'BEARISH' | 'NEUTRAL'
            }
        """
        result = {
            'ma5': 0.0,
            'ma20': 0.0,
            'ma60': 0.0,
            'ma120': 0.0,
            'current_price': float(close.iloc[-1]) if len(close) > 0 else 0.0,
            'golden_cross': False,
            'dead_cross': False,
            'alignment': 'NEUTRAL'
        }

        if len(close) >= 5:
            result['ma5'] = round(float(close.tail(5).mean()), 2)
        if len(close) >= 20:
            result['ma20'] = round(float(close.tail(20).mean()), 2)
        if len(close) >= 60:
            result['ma60'] = round(float(close.tail(60).mean()), 2)
        if len(close) >= 120:
            result['ma120'] = round(float(close.tail(120).mean()), 2)

        # 골든크로스 / 데드크로스 확인 (단기 > 장기)
        if len(close) >= 20:
            ma5_prev = float(close.iloc[-6:-1].mean()) if len(close) >= 6 else 0
            ma20_prev = float(close.iloc[-21:-1].mean()) if len(close) >= 21 else 0

            # 골든크로스: 단기선이 장기선을 상향 돌파
            if ma5_prev < ma20_prev and result['ma5'] > result['ma20']:
                result['golden_cross'] = True

            # 데드크로스: 단기선이 장기선을 하향 돌파
            if ma5_prev > ma20_prev and result['ma5'] < result['ma20']:
                result['dead_cross'] = True

        # 정배열 / 역배열 확인
        if all([result['ma5'], result['ma20'], result['ma60']]):
            if result['ma5'] > result['ma20'] > result['ma60']:
                result['alignment'] = 'BULLISH'   # 정배열 (상승)
            elif result['ma5'] < result['ma20'] < result['ma60']:
                result['alignment'] = 'BEARISH'   # 역배열 (하락)

        return result

    @staticmethod
    def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, Any]:
        """
        볼린저 밴드

        Returns:
            {
                'upper': 상단 밴드,
                'middle': 중간 밴드 (MA),
                'lower': 하단 밴드,
                'current_price': 현재가,
                'position': 현재가 위치 (%),
                'signal': 'OVERBOUGHT' | 'OVERSOLD' | 'NEUTRAL'
            }
        """
        if len(close) < period:
            current = float(close.iloc[-1]) if len(close) > 0 else 0.0
            return {
                'upper': current,
                'middle': current,
                'lower': current,
                'current_price': current,
                'position': 50.0,
                'signal': 'NEUTRAL'
            }

        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        current_price = float(close.iloc[-1])
        current_upper = float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else current_price
        current_middle = float(middle.iloc[-1]) if not pd.isna(middle.iloc[-1]) else current_price
        current_lower = float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else current_price

        # 현재가 위치 계산 (0-100%)
        if current_upper != current_lower:
            position = ((current_price - current_lower) / (current_upper - current_lower)) * 100
        else:
            position = 50.0

        # 신호 판단
        if position >= 90:
            signal = 'OVERBOUGHT'   # 상단 밴드 근접
        elif position <= 10:
            signal = 'OVERSOLD'     # 하단 밴드 근접
        else:
            signal = 'NEUTRAL'

        return {
            'upper': round(current_upper, 2),
            'middle': round(current_middle, 2),
            'lower': round(current_lower, 2),
            'current_price': round(current_price, 2),
            'position': round(position, 2),
            'signal': signal
        }

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                   k_period: int = 14, d_period: int = 3) -> Dict[str, Any]:
        """
        스토캐스틱 (Stochastic Oscillator)

        Returns:
            {
                'k': %K 값,
                'd': %D 값 (Signal),
                'signal': 'OVERBOUGHT' | 'OVERSOLD' | 'NEUTRAL'
            }
        """
        if len(close) < k_period:
            return {'k': 50.0, 'd': 50.0, 'signal': 'NEUTRAL'}

        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        current_k = float(k.iloc[-1]) if not pd.isna(k.iloc[-1]) else 50.0
        current_d = float(d.iloc[-1]) if not pd.isna(d.iloc[-1]) else 50.0

        # 신호 판단
        if current_k >= 80:
            signal = 'OVERBOUGHT'
        elif current_k <= 20:
            signal = 'OVERSOLD'
        else:
            signal = 'NEUTRAL'

        return {
            'k': round(current_k, 2),
            'd': round(current_d, 2),
            'signal': signal
        }

    @staticmethod
    def volume_moving_average(volume: pd.Series, periods: List[int] = [5, 20, 60]) -> Dict[str, float]:
        """
        거래량 이동평균

        Returns:
            {
                'current': 현재 거래량,
                'ma5': 5일 평균,
                'ma20': 20일 평균,
                'ma60': 60일 평균,
                'ratio_ma5': 현재/MA5 비율 (%),
                'ratio_ma20': 현재/MA20 비율 (%)
            }
        """
        result = {
            'current': float(volume.iloc[-1]) if len(volume) > 0 else 0.0,
            'ma5': 0.0,
            'ma20': 0.0,
            'ma60': 0.0,
            'ratio_ma5': 100.0,
            'ratio_ma20': 100.0
        }

        current_volume = result['current']

        if len(volume) >= 5:
            result['ma5'] = float(volume.tail(5).mean())
            if result['ma5'] > 0:
                result['ratio_ma5'] = round((current_volume / result['ma5']) * 100, 2)

        if len(volume) >= 20:
            result['ma20'] = float(volume.tail(20).mean())
            if result['ma20'] > 0:
                result['ratio_ma20'] = round((current_volume / result['ma20']) * 100, 2)

        if len(volume) >= 60:
            result['ma60'] = float(volume.tail(60).mean())

        return result

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict[str, Any]:
        """
        ADX (Average Directional Index) - 추세 강도

        Returns:
            {
                'adx': ADX 값,
                'plus_di': +DI,
                'minus_di': -DI,
                'trend_strength': 'STRONG' | 'WEAK'
            }
        """
        if len(close) < period * 2:
            return {'adx': 0.0, 'plus_di': 0.0, 'minus_di': 0.0, 'trend_strength': 'WEAK'}

        try:
            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Directional Movement
            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0

            # Smoothed indicators
            atr = tr.rolling(window=period).mean()
            plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

            # ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=period).mean()

            current_adx = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 0.0
            current_plus_di = float(plus_di.iloc[-1]) if not pd.isna(plus_di.iloc[-1]) else 0.0
            current_minus_di = float(minus_di.iloc[-1]) if not pd.isna(minus_di.iloc[-1]) else 0.0

            trend_strength = 'STRONG' if current_adx >= 25 else 'WEAK'

            return {
                'adx': round(current_adx, 2),
                'plus_di': round(current_plus_di, 2),
                'minus_di': round(current_minus_di, 2),
                'trend_strength': trend_strength
            }

        except Exception:
            return {'adx': 0.0, 'plus_di': 0.0, 'minus_di': 0.0, 'trend_strength': 'WEAK'}

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> Dict[str, Any]:
        """
        CCI (Commodity Channel Index)

        Returns:
            {
                'value': CCI 값,
                'signal': 'OVERBOUGHT' | 'OVERSOLD' | 'NEUTRAL'
            }
        """
        if len(close) < period:
            return {'value': 0.0, 'signal': 'NEUTRAL'}

        tp = (high + low + close) / 3
        ma = tp.rolling(window=period).mean()
        md = tp.rolling(window=period).apply(lambda x: abs(x - x.mean()).mean(), raw=True)

        cci = (tp - ma) / (0.015 * md)
        current_cci = float(cci.iloc[-1]) if not pd.isna(cci.iloc[-1]) else 0.0

        # 신호 판단
        if current_cci >= 100:
            signal = 'OVERBOUGHT'
        elif current_cci <= -100:
            signal = 'OVERSOLD'
        else:
            signal = 'NEUTRAL'

        return {
            'value': round(current_cci, 2),
            'signal': signal
        }

    @staticmethod
    def _default_indicators() -> Dict[str, Any]:
        """기본 지표 값"""
        return {
            'rsi': {'value': 50.0, 'signal': 'NEUTRAL'},
            'macd': {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0, 'trend': 'NEUTRAL'},
            'moving_averages': {
                'ma5': 0.0, 'ma20': 0.0, 'ma60': 0.0, 'ma120': 0.0,
                'current_price': 0.0, 'golden_cross': False, 'dead_cross': False,
                'alignment': 'NEUTRAL'
            },
            'bollinger_bands': {
                'upper': 0.0, 'middle': 0.0, 'lower': 0.0,
                'current_price': 0.0, 'position': 50.0, 'signal': 'NEUTRAL'
            },
            'stochastic': {'k': 50.0, 'd': 50.0, 'signal': 'NEUTRAL'},
            'volume_ma': {'current': 0.0, 'ma5': 0.0, 'ma20': 0.0, 'ma60': 0.0,
                         'ratio_ma5': 100.0, 'ratio_ma20': 100.0},
            'adx': {'adx': 0.0, 'plus_di': 0.0, 'minus_di': 0.0, 'trend_strength': 'WEAK'},
            'cci': {'value': 0.0, 'signal': 'NEUTRAL'}
        }


__all__ = ["TechnicalIndicators"]
