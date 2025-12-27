# lib/utils/settings.py
from __future__ import annotations
import yaml
from pathlib import Path
from collections.abc import ItemsView
from logging import config as logging_config
from typing import Dict, Any, Optional, Iterator, Tuple
from pydantic import BaseModel, Field, RootModel, ConfigDict


class _AppConfig(BaseModel):
    debug: bool = False
    version: str = "0.0.1"
    logger: Optional[LoggerConfig] = None
    redis: Optional[Dict[str, RedisConfig]] = None
    db: Dict[str, DbConfig]

    # 允许用环境变量覆盖
    model_config = {
        "env_prefix": "APP_",   # e.g. APP_DEBUG=true
        "env_nested_delimiter": "__"
    }

class DbConfig(BaseModel):
    host: str
    port: int = 3306
    user: str
    password: str
    db: Optional[str] = None
    charset: str = "utf8mb4"

    # 连接池／超时等，可视需要再加
    maxIdle: int = Field(50, alias="maxIdle")
    maxConn: int = Field(500, alias="maxConn")
    connMaxLiftTime: int = Field(3600, alias="connMaxLiftTime")

    model_config = ConfigDict(populate_by_name=True)


class RedisConfig(BaseModel):
    host: str
    port: int = 6379
    db:   int = 0
    password: Optional[str] = None

    max_idle:     int = Field(100, alias="maxIdle")
    idle_timeout: int = Field(30,  alias="idleTimeout")
    max_active:   int = Field(1000, alias="maxActive")

    model_config = ConfigDict(populate_by_name=True)

class LoggerConfig(RootModel[dict[str, Any]]):
    """
    直接把 logging.config.dictConfig 需要的那棵 dict
    包在 RootModel 里，不做字段级校验，保持原生格式。
    """
    def apply(self) -> None:
        """helper：一行把配置注入 logging"""
        logging_config.dictConfig(self.root)


class DbRegistry(RootModel[Dict[str, DbConfig]]):
    """root == {'bai_db': DbConfig, ...}"""

    # 取子项：settings.db["bai_db"]
    def __getitem__(self, item: str) -> DbConfig:       # type: ignore[override]
        return self.root[item]

    def get(self, key: str, default: Optional[DbConfig] = None):
        return self.root.get(key, default)

    def items(self) -> ItemsView[str, DbConfig]:
        return self.root.items()


class RedisRegistry(RootModel[Dict[str, RedisConfig]]):
    """root == {'passport_redis': RedisConfig, ...}"""

    # 取子项：settings.redis["passport_redis"]
    def __getitem__(self, item: str) -> RedisConfig:       # type: ignore[override]
        return self.root[item]

    def get(self, key: str, default: Optional[RedisConfig] = None):
        return self.root.get(key, default)

    def items(self) -> ItemsView[str, RedisConfig]:
        return self.root.items()

def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def init_settings() -> _AppConfig:
    """
    读取 ./config 目录下所有 yml|yaml 并合并，
    再由 Pydantic 校验 -> AppConfig 实例
    """
    cfg_dir = Path(__file__).resolve().parents[2] / "config"
    merged: dict = {}
    for file in cfg_dir.glob("*.y*ml"):
        merged |= _load_yaml(file)   # Py 3.9+ 字典合并运算符 |
    return _AppConfig.model_validate(merged)


AppConfig: _AppConfig = init_settings()
"""
全局配置对象: AppConfig
使用方法：
    >>> from config import AppConfig
    >>> print(AppConfig.erase_video.access_key_id)
    >>> print(AppConfig.qwen.api_key)
"""
