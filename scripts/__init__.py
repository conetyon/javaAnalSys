# scripts/__init__.py
"""
离线脚本模块
包含数据库初始化、代码分析、匹配测试等离线任务
"""
from .offline_tasks import (
    init_database,
    analyze_code_file,
    run_matching_test,
    run_full_pipeline,
)

__all__ = [
    "init_database",
    "analyze_code_file",
    "run_matching_test",
    "run_full_pipeline",
]
