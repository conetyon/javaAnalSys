# src/evaluation/__init__.py
"""
Java 知识点匹配系统评估模块

提供性能评估指标、消融实验、实验报告生成等功能。
"""

from .metrics import (
    calculate_top1_accuracy,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_mrr,
    calculate_ndcg,
    calculate_map,
)

from .experiment import (
    run_single_evaluation,
    run_ablation_study,
    generate_experiment_report,
)

__all__ = [
    # 评估指标
    "calculate_top1_accuracy",
    "calculate_precision_at_k",
    "calculate_recall_at_k",
    "calculate_mrr",
    "calculate_ndcg",
    "calculate_map",
    # 实验运行
    "run_single_evaluation",
    "run_ablation_study",
    "generate_experiment_report",
]
