# db_manager/__init__.py

# 从包内的各个模块中导入核心函数，以便外部可以直接从 db_manager 包导入
# 使用 . (点) 表示从当前包内导入
from .database import get_connection, init_db
from .knowledge_point_manager import insert_knowledge_points, display_knowledge_point_tree
from .code_library_manager import insert_baseline_code_data, save_analyzed_results

# (可选) 定义当使用 from db_manager import * 时，哪些符号会被导出
__all__ = [
    "get_connection",
    "init_db",
    "insert_knowledge_points",
    "save_analyzed_results",
    "display_knowledge_point_tree",
    "insert_baseline_code_data",
]
