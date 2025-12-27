# lib/globals/__init__.py
from __future__ import annotations
import logging
from lib.utils.settings import init_settings, AppConfig
from typing import Optional

"""
日志句柄
    用于记录日志
    修改日志句柄需要：
        1. 修改配置文件：config/logger.yaml
        2. 在此处补充新日志句柄
    用法：
        >>> from lib.globals import logger
        >>> logger.info("this is a log with format way 1: {} {}".format("hello", "world"))
        >>> str1="hello"
        >>> str2="world"
        >>> logger.info(f"this is a log with format way 2 {str1} {str2}")
"""

# 惰性单例，保证只加载一次
_CACHED: Optional[AppConfig] = None


# 供外部直接使用： from lib.globals import Cfg
def _load() -> AppConfig:
    global _CACHED
    if _CACHED is None:
        _CACHED = init_settings()          # ← 用 _CACHED（大写 C）
        if _CACHED.logger:                 # type: ignore[truthy-bool]
            _CACHED.logger.apply()
    return _CACHED


# 全局配置对象
Cfg: AppConfig = _load()

# 日志句柄
logger:     logging.Logger = logging.getLogger()      # root
api_logger: logging.Logger = logging.getLogger("api")
web_logger: logging.Logger = logging.getLogger("web")
core_logger: logging.Logger = logging.getLogger("core")

__all__ = ["Cfg", "logger", "api_logger", "web_logger", "core_logger"]
