# main.py
import os
import traceback
import config
from lib.globals import core_logger as log

# 导入业务组件
from src.db_manager import (
    DatabaseInitializer,
    CodeLibraryManager,
    KnowledgePointManager
)
from src.java_analyzer import JavaAnalyzer
from src.services.search_service import SearchService

def ensure_sample_file(filepath):
    """辅助：确保演示文件存在"""
    if not os.path.exists(filepath):
        print(f"[WARN] 文件 {filepath} 不存在，正在创建空文件...")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("public class Test { }")
    return filepath


def main():
    try:
        DB_NAME = config.DB_NAME
        SAMPLE_FILE_PATH = "sample_code.java"
        # 默认演示参数
        DEFAULT_KP_ID = 10001
        DEFAULT_DIFFICULTY = 0.6
        # --- 阶段 1: 基础设施初始化 ---
        print("\n=== Step 1: Init Database ===")
        db_init = DatabaseInitializer(db_name=DB_NAME)
        kb_mgr = KnowledgePointManager(db_name=DB_NAME)
        code_mgr = CodeLibraryManager(db_name=DB_NAME)
        db_init.init_db()
        kb_mgr.insert_baseline_data()
        code_mgr.insert_baseline_code_data()
        # --- 阶段 2: 代码分析与入库 ---
        print("\n=== Step 2: Analyze & Ingest Code ===")
        sample_path = ensure_sample_file(SAMPLE_FILE_PATH)

        with open(sample_path, "r", encoding="utf-8") as f:
            code_content = f.read()
        # 初始化分析器
        analyzer = JavaAnalyzer()
        snippets = analyzer.analyze_file(code_content)
        print(f"-> Detected {len(snippets)} snippets in {sample_path}")
        if snippets:
            code_mgr.save_analyzed_results(sample_path, code_content, snippets)
        # --- 阶段 3: 执行智能匹配 ---
        print("\n=== Step 3: Matching Execution ===")
        search_service = SearchService(db_name=DB_NAME)

        print(f"-> Query: KP_ID={DEFAULT_KP_ID}, Target_Diff={DEFAULT_DIFFICULTY}")

        results = search_service.search(
            kp_id=DEFAULT_KP_ID,
            target_difficulty=DEFAULT_DIFFICULTY,
            top_k=5
        )
        # --- 阶段 4: 结果展示 ---
        print(f"\n-> Top {len(results)} Matches:")
        for rank, res in enumerate(results, 1):
            print(f"\n[#{rank}] Score: {res['score']} | {res['details']}")
            print("-" * 40)
            preview = res['content'].strip()[:80].replace('\n', ' ')
            print(f"Code: {preview}...")
    except Exception as e:
        traceback.print_exc()
        print(f"\n[CRITICAL ERROR] {e}")


if __name__ == "__main__":
    main()