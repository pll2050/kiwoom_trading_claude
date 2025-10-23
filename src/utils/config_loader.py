"""
설정 파일 로더
YAML 설정 파일 로드 및 관리
"""

import yaml
from pathlib import Path
from typing import Dict, Any
from src.utils.logger import logger


class ConfigLoader:
    """YAML 설정 파일 로더"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load(self, config_name: str) -> Dict[str, Any]:
        """설정 파일 로드"""
        if config_name in self._cache:
            return self._cache[config_name]

        config_path = self.config_dir / f"{config_name}.yaml"

        if not config_path.exists():
            logger.error(f"설정 파일 없음: {config_path}")
            raise FileNotFoundError(f"Config not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            logger.info(f"설정 로드 완료: {config_name}.yaml")
            self._cache[config_name] = config
            return config

        except Exception as e:
            logger.error(f"설정 로드 실패: {config_name}.yaml - {e}")
            raise

    def get(self, config_name: str, key_path: str, default: Any = None) -> Any:
        """점 표기법으로 설정값 가져오기"""
        config = self.load(config_name)
        keys = key_path.split('.')
        value = config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value


# 싱글톤 인스턴스
_loader = ConfigLoader()


def load_config(name: str) -> Dict[str, Any]:
    """설정 파일 로드 (편의 함수)"""
    return _loader.load(name)


def get_config(name: str, key_path: str, default: Any = None) -> Any:
    """설정값 가져오기 (편의 함수)"""
    return _loader.get(name, key_path, default)


__all__ = ["ConfigLoader", "load_config", "get_config"]
