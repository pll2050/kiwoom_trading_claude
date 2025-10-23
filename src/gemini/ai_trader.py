"""
Gemini AI 트레이딩 로직
종목 분석 및 매매 의사결정
"""

import google.generativeai as genai
from typing import Dict, Any, List
from src.utils.config_loader import load_config
from src.utils.logger import logger


class GeminiAITrader:
    """Gemini AI 트레이더"""

    def __init__(self):
        config = load_config("config")
        api_key = config['gemini']['api_key']
        model_name = config['gemini']['model']

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

        logger.info(f"Gemini AI 초기화: {model_name}")

    async def analyze_stock(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """종목 심층 분석"""
        prompt = self._create_prompt(stock_data)

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_response(response.text)
            logger.info(f"AI 분석: {stock_data.get('name')} - {result.get('recommendation')}")
            return result
        except Exception as e:
            logger.error(f"AI 분석 실패: {e}")
            return {
                'recommendation': 'HOLD',
                'confidence': 0.0,
                'reason': 'AI 분석 실패'
            }

    def _create_prompt(self, data: Dict) -> str:
        """분석 프롬프트 생성"""
        return f"""
전문 애널리스트로 다음 종목을 분석해주세요.

【종목 정보】
- 종목명: {data.get('name')}
- 종목코드: {data.get('code')}
- 현재가: {data.get('current_price'):,}원
- 등락률: {data.get('price_change_pct')}%

【스캐닝 점수】
- 종합: {data.get('total_score')}/440점
- 등급: {data.get('grade')}
- 거래량: {data.get('volume_change_pct')}%

【분석 요청】
1. 상승 가능성 (%)
2. 매수/매도/관망 추천
3. 목표가
4. 리스크
5. 신뢰도 (0~1)

JSON 형식으로만 답변:
{{
  "probability": 85,
  "recommendation": "BUY",
  "target_price": 75000,
  "risk_level": "MEDIUM",
  "confidence": 0.85,
  "reason": "근거..."
}}
"""

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """AI 응답 파싱"""
        try:
            import json
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return self._default()
        except:
            return self._default()

    def _default(self) -> Dict[str, Any]:
        """기본 응답"""
        return {
            'probability': 50,
            'recommendation': 'HOLD',
            'target_price': 0,
            'risk_level': 'HIGH',
            'confidence': 0.3,
            'reason': '분석 불가'
        }

    async def analyze_multiple_stocks(self, stocks: List[Dict]) -> List[Dict]:
        """여러 종목 분석"""
        results = []
        for stock in stocks:
            analysis = await self.analyze_stock(stock)
            stock['ai_analysis'] = analysis
            results.append(stock)

        results.sort(key=lambda x: x['ai_analysis'].get('confidence', 0), reverse=True)
        return results


__all__ = ["GeminiAITrader"]
