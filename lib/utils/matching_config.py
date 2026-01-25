"""
匹配配置加载器

用法:
    from lib.utils.matching_config import get_matching_config

    # 获取评估配置
    cfg = get_matching_config('evaluation')
    results = search_service.search(
        kp_id=kp_id,
        top_k=10,
        ast_min_ratio=cfg['ast_min_ratio'],
        keyword_min_score=cfg['keyword_min_score'],
        w_ast=cfg['w_ast'],
        w_keyword=cfg['w_keyword'],
        w_difficulty=cfg['w_difficulty']
    )
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
        profile: 配置名称（default, evaluation, ground_truth, codesearchnet）

    Returns:
        配置字典，包含阈值和权重

    Examples:
        >>> cfg = get_matching_config('evaluation')
        >>> print(cfg['ast_min_ratio'])
        0.2
    """
    config = load_matching_config()

    if profile not in config:
        raise ValueError(f"Unknown profile: {profile}. Available: {list(config.keys())}")

    return config[profile]


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


def get_default_weights() -> Dict[str, float]:
    """
    获取默认权重（生产环境）

    Returns:
        {'w_ast': 0.6, 'w_keyword': 0.3, 'w_difficulty': 0.1}
    """
    cfg = get_matching_config('default')
    return {
        'w_ast': cfg['w_ast'],
        'w_keyword': cfg['w_keyword'],
        'w_difficulty': cfg['w_difficulty']
    }


def get_evaluation_config() -> Dict[str, Any]:
    """
    获取评估配置（快捷方法）

    Returns:
        评估配置字典
    """
    return get_matching_config('evaluation')


def get_ground_truth_config() -> Dict[str, Any]:
    """
    获取Ground Truth生成配置（快捷方法）

    Returns:
        Ground Truth配置字典
    """
    return get_matching_config('ground_truth')
