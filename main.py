# main.py
import os
import traceback
from lib.globals import core_logger as log

from db_manager import (
    DatabaseInitializer,
    CodeLibraryManager,
    KnowledgePointManager
)
from matcher import Matcher
from analyzer import CodeAnalyzer  # 假设这个文件存在且未变动


def setup_sample_code_file():
    """确保演示用的Java文件存在。"""
    filepath = "sample_code.java"
    # 若不存在则创建；若已存在，沿用库中的样例
    if not os.path.exists(filepath):
        print(f"Creating sample file: {filepath}")
        log.error("Sample file not exist")
        exit(1)
    return filepath


def main():
    """主程序：初始化 -> 分析 -> 保存 -> 匹配（多阶段过滤 + 加权融合）"""
    DB_NAME = "javalearningsys"

    try:
        print("--- Step 1: Initialize Database & Baseline Data ---")
        db_init = DatabaseInitializer(db_name=DB_NAME)
        kb_mgr = KnowledgePointManager(db_name=DB_NAME)
        code_mgr = CodeLibraryManager(db_name=DB_NAME)

        # 初始化（若库中已有数据，这些方法应幂等）
        db_init.init_db()
        kb_mgr.insert_baseline_data()
        code_mgr.insert_baseline_code_data()
        kb_mgr.display_tree()

        print("\n--- Step 2: Analyze New Code and Save to DB ---")
        sample_file = setup_sample_code_file()
        with open(sample_file, "r", encoding="utf-8") as f:
            java_code = f.read()

        analyzer = CodeAnalyzer()
        snippets = analyzer.analyze_file(java_code)
        print(f"在 '{sample_file}' 中检测到 {len(snippets)} 个代码片段。")

        if snippets:
            code_mgr.save_analyzed_results(sample_file, java_code, snippets)

        print("\n--- Step 3: Execute Matching Algorithm ---")
        # 演示使用当前场景中的参数：ID=10（Java 基础），难度=0.6
        kp_id = 202
        user_diff = 0.6
        print(f"用户查询: 知识点 ID={kp_id}, 期望难度={user_diff}")

        matcher = Matcher(db_name=DB_NAME)

        # 使用设计方案：多阶段过滤
        # - 难度过滤：宽松模式，容差0.25
        # - AST组合模式：AND（如有复合模板）
        results = matcher.search(
            knowledge_point_id=kp_id,
            target_difficulty=user_diff,
            top_k=5
        )

        print(f"\n找到 {len(results)} 个匹配结果:")
        for rank, res in enumerate(results, 1):
            print(f"\n[Rank {rank}] 综合得分: {res['score']:.4f} ({res['details']})")
            print("-" * 40)
            content_preview = (res['content'] or '').strip()
            preview = (content_preview[:60] + '...') if len(content_preview) > 60 else content_preview
            print(f"代码片段: {preview}")

    except Exception as e:
        traceback.print_exc()
        print(f"\n[CRITICAL ERROR] 程序执行中断: {e}")


if __name__ == "__main__":
    main()