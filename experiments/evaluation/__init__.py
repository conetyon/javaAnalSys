# experiments/evaluation/__init__.py
"""
Java 知识点匹配系统评估模块

提供分级规则定义和评估判断功能。
评估脚本: scripts/_internal/run_evaluation.py
"""

from .rules import (
    KP_RULES,
    PILOT_KP_IDS,
    KPRule,
    calculate_feature_grade,
    get_pilot_kp_ids,
    get_all_kp_ids,
    get_rule,
    get_all_rules,
    run_independence_check,
    verify_rule_independence,
    get_noise_nodes,
    get_loc_range,
    DEFAULT_NOISE_NODES,
    DEFAULT_LOC_RANGE,
)

__all__ = [
    # 规则定义
    "KP_RULES",
    "PILOT_KP_IDS",
    "KPRule",
    # 分级判断
    "calculate_feature_grade",
    # 工具函数
    "get_pilot_kp_ids",
    "get_all_kp_ids",
    "get_rule",
    "get_all_rules",
    "run_independence_check",
    "verify_rule_independence",
    "get_noise_nodes",
    "get_loc_range",
    "DEFAULT_NOISE_NODES",
    "DEFAULT_LOC_RANGE",
]
