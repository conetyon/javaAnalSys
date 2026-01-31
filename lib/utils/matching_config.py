"""
匹配配置加载器

用法:
    from lib.utils.matching_config import get_matching_config

    # 获取生产环境配置
    cfg = get_matching_config('default')
    # cfg = {'ast_min_ratio': 0.4, 'keyword_min_score': 0.4, 'w_ast': 0.5, ...}
"""

import yaml
from pathlib import Path
from typing import Dict, Any

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent.parent / 'config' / 'matching.yaml'

_config_cache: Dict[str, Any] = {}


def load_matching_config() -> Dict[str, Any]:
    """
    加载匹配配置文件

    Returns:
        配置字典
    """
    if _config_cache:
        return _config_cache

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Matching config not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    _config_cache.update(config)
    return _config_cache


def get_matching_config(profile: str = 'default') -> Dict[str, Any]:
    """
    获取指定配置profile

    Args:
        profile: 配置名称（目前仅支持 'default'）

    Returns:
        配置字典，包含阈值和权重

    Examples:
        >>> cfg = get_matching_config('default')
        >>> print(cfg['w_ast'])
        0.5
    """
    config = load_matching_config()

    if profile not in config:
        raise ValueError(f"Unknown profile: {profile}. Available: {list(config.keys())}")

    return config[profile]


def get_default_weights() -> Dict[str, float]:
    """
    获取默认权重（生产环境）

    Returns:
        {'w_ast': 0.5, 'w_keyword': 0.4, 'w_difficulty': 0.1}
    """
    cfg = get_matching_config('default')
    return {
        'w_ast': cfg['w_ast'],
        'w_keyword': cfg['w_keyword'],
        'w_difficulty': cfg['w_difficulty']
    }


def get_default_thresholds() -> Dict[str, float]:
    """
    获取默认阈值（生产环境）

    Returns:
        {'ast_min_ratio': 0.4, 'keyword_min_score': 0.4}
    """
    cfg = get_matching_config('default')
    return {
        'ast_min_ratio': cfg['ast_min_ratio'],
        'keyword_min_score': cfg['keyword_min_score']
    }
