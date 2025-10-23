"""
로깅 시스템
loguru를 사용한 콘솔 및 파일 로깅
"""

import sys
from loguru import logger

# 기본 핸들러 제거
logger.remove()

# 로그 포맷 정의
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 콘솔 로거 추가
logger.add(
    sys.stderr,
    level="DEBUG",
    format=log_format,
    colorize=True
)

# 파일 로거 추가
logger.add(
    "logs/{time:YYYY-MM-DD}.log",
    level="DEBUG",
    format=log_format,
    rotation="10 MB",
    retention=30,
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    diagnose=True
)

__all__ = ["logger"]
