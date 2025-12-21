# main.py
import os
import traceback
from lib.globals import core_logger as log

# 从重构后的包中导入类
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
    # (为了演示方便，这里简化写入内容)
    if not os.path.exists(filepath):
        print(f"Creating sample file: {filepath}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("""
public class SampleCode {
    public void process() {
        try {
            int a = 1;
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
""")
    return filepath


def main():
    """主程序：OOP 风格的编排流程"""

    # 可以在这里统一配置 DB 名称，或者留空使用默认值
    DB_NAME = "javalearningsys"

    try:
        # --- 实例化各类 Manager ---
        db_init = DatabaseInitializer(db_name=DB_NAME)
        kb_mgr = KnowledgePointManager(db_name=DB_NAME)
        code_mgr = CodeLibraryManager(db_name=DB_NAME)

        # --- 步骤 1: 初始化数据库和基线数据 ---
        print("--- Step 1: Initialize Database & Baseline Data ---")

        # 1.1 初始化表结构
        db_init.init_db()

        # 1.2 插入数据 (调用 Manager 实例的方法)
        kb_mgr.insert_baseline_data()
        code_mgr.insert_baseline_code_data()

        # 1.3 展示树结构
        kb_mgr.display_tree()

        # --- 步骤 2: 分析新代码并存入数据库 ---
        print("\n--- Step 2: Analyze New Code and Save to DB ---")
        sample_file = setup_sample_code_file()
        with open(sample_file, "r", encoding="utf-8") as f:
            java_code = f.read()

        # 使用分析器 (假设 Analyzer 也是一个类)
        analyzer = CodeAnalyzer()
        snippets = analyzer.analyze_file(java_code)
        print(f"在 '{sample_file}' 中检测到 {len(snippets)} 个代码片段。")

        if snippets:
            # 调用 CodeManager 保存
            code_mgr.save_analyzed_results(sample_file, java_code, snippets)

        # --- 步骤 3: 执行匹配算法 ---
        print("\n--- Step 3: Execute Matching Algorithm ---")

        kp_id = 10  # 假设查询 ID=10 (Java 基础)
        user_diff = 0.6
        print(f"用户查询: 知识点 ID={kp_id}, 期望难度={user_diff}")

        # 实例化匹配器 (内部会自动初始化它需要的 Managers)
        matcher = Matcher(db_name=DB_NAME)
        results = matcher.search(kp_id, user_diff)

        print(f"\n找到 {len(results)} 个匹配结果:")
        for rank, res in enumerate(results, 1):
            print(f"\n[Rank {rank}] 综合得分: {res['score']:.4f} ({res['details']})")
            print("-" * 40)
            content_preview = res['content'].strip()
            # 简单的截断展示
            preview = (content_preview[:60] + '...') if len(content_preview) > 60 else content_preview
            print(f"代码片段: {preview}")

    except Exception as e:
        traceback.print_exc()
        print(f"\n[CRITICAL ERROR] 程序执行中断: {e}")


if __name__ == "__main__":
    main()