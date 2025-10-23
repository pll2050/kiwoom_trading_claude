"""
매매 시스템 디버깅 스크립트
왜 매수/매도가 실행되지 않는지 확인
"""

import asyncio
from datetime import datetime
from src.utils.config_loader import load_config
from src.utils.logger import logger


async def debug_trading_system():
    """매매 시스템 디버깅"""

    logger.info("=" * 60)
    logger.info("매매 시스템 디버깅 시작")
    logger.info("=" * 60)
    logger.info("")

    # 1. 설정 확인
    logger.info("1. 설정 확인")
    logger.info("-" * 60)

    config = load_config("config")
    trading_config = load_config("trading_rules")
    scanning_config = load_config("scanning_rules")

    # 테스트 모드
    test_mode = config['trading']['test_mode']
    logger.info(f"✓ 테스트 모드: {test_mode}")
    if not test_mode:
        logger.warning("⚠️  실전 투자 모드입니다! test_mode: true로 변경을 권장합니다.")

    # 투자 설정
    initial_capital = config['trading']['initial_capital']
    max_investment = config['trading']['max_investment_per_stock']
    max_daily_loss = config['trading']['max_daily_loss']

    logger.info(f"✓ 초기 자본: {initial_capital:,}원")
    logger.info(f"✓ 종목당 최대 투자: {max_investment:,}원")
    logger.info(f"✓ 일일 최대 손실: {max_daily_loss:,}원")

    # 동적 리스크 관리
    drm_enabled = config['trading']['dynamic_risk_management']['enabled']
    logger.info(f"✓ 동적 리스크 관리: {drm_enabled}")
    logger.info("")

    # 2. 스캔 간격 확인
    logger.info("2. 스캔 간격 확인")
    logger.info("-" * 60)

    intervals = scanning_config['scanning']['intervals']
    fast_interval = intervals['fast_scan']
    deep_interval = intervals['deep_scan']
    ai_interval = intervals['ai_analysis']

    logger.info(f"✓ Fast Scan 간격: {fast_interval}초 ({fast_interval//60}분)")
    logger.info(f"✓ Deep Scan 간격: {deep_interval}초 ({deep_interval//60}분)")
    logger.info(f"✓ AI Scan 간격: {ai_interval}초 ({ai_interval//60}분)")
    logger.info("")

    # AI Scan 간격이 너무 길면 경고
    if ai_interval > 1800:  # 30분 이상
        logger.warning(f"⚠️  AI Scan 간격이 너무 깁니다! ({ai_interval//60}분)")
        logger.warning("   매수 신호가 늦게 생성될 수 있습니다.")
        logger.warning(f"   권장: 10-15분 (600-900초)")
    logger.info("")

    # 3. 거래 시간 확인
    logger.info("3. 거래 시간 확인")
    logger.info("-" * 60)

    trading_hours = trading_config['trading_hours']
    market_open = trading_hours['market_open']
    new_buy_close = trading_hours['new_buy_close']
    market_close = trading_hours['market_close']

    now = datetime.now()
    current_time = now.time()
    market_open_time = datetime.strptime(market_open, "%H:%M:%S").time()
    new_buy_close_time = datetime.strptime(new_buy_close, "%H:%M:%S").time()
    market_close_time = datetime.strptime(market_close, "%H:%M:%S").time()

    logger.info(f"✓ 현재 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"✓ 장 시작: {market_open}")
    logger.info(f"✓ 신규 매수 마감: {new_buy_close}")
    logger.info(f"✓ 장 마감: {market_close}")
    logger.info("")

    # 거래 가능 시간 체크
    is_trading_hours = market_open_time <= current_time <= new_buy_close_time
    is_weekday = now.weekday() < 5  # 0=월요일, 4=금요일

    if not is_weekday:
        logger.error("❌ 주말입니다! 거래가 불가능합니다.")
        logger.info("   월~금요일에만 거래가 가능합니다.")
    elif not is_trading_hours:
        logger.warning("⚠️  거래 시간이 아닙니다!")
        logger.info(f"   매수 가능 시간: {market_open} ~ {new_buy_close}")

        if current_time < market_open_time:
            wait_seconds = (datetime.combine(now.date(), market_open_time) - now).seconds
            logger.info(f"   장 시작까지: {wait_seconds//3600}시간 {(wait_seconds%3600)//60}분")
        else:
            logger.info("   오늘 거래 시간 종료")
    else:
        logger.info("✅ 거래 가능 시간입니다!")
    logger.info("")

    # 4. 매수 조건 확인
    logger.info("4. 매수 조건 확인")
    logger.info("-" * 60)

    risk_mgmt = trading_config['risk_management']
    max_positions = risk_mgmt['max_positions']
    min_score = scanning_config['scanning']['grading']['ai_analysis_min_score']

    logger.info(f"✓ 최대 포지션 수: {max_positions}개")
    logger.info(f"✓ AI 분석 최소 점수: {min_score}점 (Deep Scan)")
    logger.info("")

    # AI 분석 조건
    logger.info("AI 매수 조건:")
    logger.info("  - 추천: BUY")
    logger.info("  - 신뢰도: 70% 이상 (동적 조정)")
    logger.info("  - 확률: 60% 이상")
    logger.info("")

    # 5. 예상 매수 진행 상황
    logger.info("5. 예상 매수 진행 상황")
    logger.info("-" * 60)

    if not is_weekday:
        logger.info("❌ 주말 - 거래 불가")
    elif not is_trading_hours:
        logger.info("⚠️  거래 시간 외 - 매수 불가")
    else:
        logger.info("매수 실행 흐름:")
        logger.info(f"  1. Fast Scan 실행 ({fast_interval}초마다)")
        logger.info(f"  2. Deep Scan 실행 ({deep_interval}초마다, 5초 후 시작)")
        logger.info(f"     → {min_score}점 이상 종목 필터링")
        logger.info(f"  3. AI Scan 실행 ({ai_interval}초마다, 10초 후 시작)")
        logger.info(f"     → 상위 10개 종목 AI 분석")
        logger.info(f"     → BUY 추천 + 신뢰도 70%+ 종목 매수")
        logger.info("")

        # 첫 번째 AI Scan까지 대기 시간
        first_ai_scan = 10  # 초기 대기 시간
        logger.info(f"✓ 첫 번째 AI Scan: 시작 후 약 {first_ai_scan}초")
        logger.info(f"✓ 두 번째 AI Scan: 첫 번째 후 약 {ai_interval}초 ({ai_interval//60}분)")
        logger.info("")

        if test_mode:
            logger.info("⚠️  테스트 모드 활성화:")
            logger.info("   - 실제 주문은 실행되지 않습니다")
            logger.info("   - 로그에만 표시됩니다")
        else:
            logger.warning("🔴 실전 투자 모드:")
            logger.warning("   - 실제 주문이 실행됩니다!")
            logger.warning("   - 신중하게 확인하세요!")
        logger.info("")

    # 6. 매도 조건 확인
    logger.info("6. 매도 조건 확인")
    logger.info("-" * 60)

    profit_loss = trading_config['profit_loss']
    stop_loss = profit_loss['stop_loss_percentage']
    take_profit = profit_loss['take_profit_percentage']

    logger.info(f"✓ 손절: {stop_loss}%")
    logger.info(f"✓ 익절: {take_profit}%")
    logger.info(f"✓ 장 마감 전 청산: {market_close}")
    logger.info("")

    logger.info("매도 실행 조건:")
    logger.info(f"  - 손실이 {stop_loss}% 이하")
    logger.info(f"  - 수익이 {take_profit}% 이상")
    logger.info(f"  - 15:10 이후 (장 마감 임박)")
    logger.info("")

    # 7. 로그 확인 방법
    logger.info("7. 로그 확인 방법")
    logger.info("-" * 60)

    logger.info("실시간 로그 확인:")
    logger.info("  # Linux/Mac")
    logger.info("  tail -f logs/trading.log")
    logger.info("")
    logger.info("  # Windows PowerShell")
    logger.info("  Get-Content logs/trading.log -Wait -Tail 50")
    logger.info("")

    logger.info("특정 키워드 검색:")
    logger.info("  # AI Scan 결과")
    logger.info("  grep 'AI Scan' logs/trading.log")
    logger.info("")
    logger.info("  # 매수 추천")
    logger.info("  grep '매수 추천' logs/trading.log")
    logger.info("")
    logger.info("  # 매수 주문")
    logger.info("  grep '매수 주문' logs/trading.log")
    logger.info("")
    logger.info("  # 매수 불가 사유")
    logger.info("  grep '매수 불가' logs/trading.log")
    logger.info("")

    # 8. 문제 해결
    logger.info("8. 일반적인 문제")
    logger.info("-" * 60)

    logger.info("매수가 실행되지 않는 이유:")
    logger.info("")
    logger.info("✓ 거래 시간이 아님")
    logger.info("  → 09:00~14:50 사이에만 매수 가능")
    logger.info("")
    logger.info("✓ AI Scan 간격이 너무 김")
    logger.info(f"  → 현재: {ai_interval}초 ({ai_interval//60}분)")
    logger.info("  → 권장: 600-900초 (10-15분)")
    logger.info("")
    logger.info("✓ Deep Scan에서 고득점 종목이 없음")
    logger.info(f"  → {min_score}점 이상 종목이 필요")
    logger.info("  → 로그에서 'Deep Scan 완료' 확인")
    logger.info("")
    logger.info("✓ AI가 BUY 추천하지 않음")
    logger.info("  → 시장 상황이 좋지 않을 수 있음")
    logger.info("  → 로그에서 '매수 추천: 0개' 확인")
    logger.info("")
    logger.info("✓ AI 신뢰도가 낮음")
    logger.info("  → 70% 이상이어야 매수")
    logger.info("  → 동적 리스크 관리로 조정됨")
    logger.info("")
    logger.info("✓ test_mode가 true")
    logger.info("  → 실제 주문 없이 로그만 출력")
    logger.info("")

    logger.info("=" * 60)
    logger.info("디버깅 완료")
    logger.info("=" * 60)
    logger.info("")
    logger.info("다음 단계:")
    logger.info("1. python main.py 실행")
    logger.info("2. 로그 확인 (tail -f logs/trading.log)")
    logger.info("3. 'AI Scan' 로그 대기")
    logger.info("4. '매수 추천' 메시지 확인")
    logger.info("")


if __name__ == "__main__":
    try:
        asyncio.run(debug_trading_system())
    except Exception as e:
        logger.error(f"디버깅 실패: {e}", exc_info=True)
