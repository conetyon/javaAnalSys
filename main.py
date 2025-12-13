# main.py
import os
import json

# 1. 从 db_manager 统一导入所有数据库操作函数
from db_manager import (
    init_db,
    insert_knowledge_points,
    insert_baseline_code_data,
    save_analyzed_results,
    display_knowledge_point_tree
)
from analyzer import CodeAnalyzer  # 假设存在
from matcher import Matcher  # 假设存在


def setup_sample_code_file():
    """确保演示用的Java文件存在。"""
    filepath = "sample_code.java"
    if not os.path.exists(filepath):
        print(f"'{filepath}' 不存在，创建一个用于演示。")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("""
public class SampleCode {
    // 匹配 try-catch
    public void processFile() {
        try {
            java.io.FileReader reader = new java.io.FileReader("file.txt");
        } catch (java.io.FileNotFoundException e) {
            System.err.println("File not found!");
        }
    }

    // 简单方法
    public int add(int a, int b) {
        return a + b;
    }
}
""")
    return filepath


def main():
    """主程序：初始化 -> 分析 -> 保存 -> 匹配"""
    conn = None
    try:
        # --- 步骤 1: 初始化数据库和基线数据 ---
        print("--- Step 1: Initialize Database & Baseline Data ---")
        conn = init_db()
        insert_knowledge_points(conn)  # 插入知识点
        insert_baseline_code_data(conn)  # 插入基线代码
        display_knowledge_point_tree(conn)  # 展示知识点树

        # --- 步骤 2: 分析新代码并存入数据库 ---
        print("\n--- Step 2: Analyze New Code and Save to DB ---")
        sample_file = setup_sample_code_file()
        with open(sample_file, "r", encoding="utf-8") as f:
            java_code = f.read()

        # 使用分析器提取特征
        analyzer = CodeAnalyzer()
        snippets = analyzer.analyze_file(java_code)
        print(f"在 '{sample_file}' 中检测到 {len(snippets)} 个代码片段。")

        if snippets:
            save_analyzed_results(conn, sample_file, java_code, snippets)
            print(f"已将 '{sample_file}' 的分析结果存入数据库。")

        # --- 步骤 3: 执行匹配算法 ---
        print("\n--- Step 3: Execute Matching Algorithm ---")
        # 假设知识点 "数据类型" 的 ID 是 101, 用户期望难度是 0.6
        kp_id = 101  # 这里应对应一个有意义的知识点ID，例如 "异常处理"
        user_diff = 0.6
        print(f"用户查询: 知识点 ID={kp_id}, 期望难度={user_diff}")

        # 将已建立的连接注入 Matcher，而不是只传名字
        matcher = Matcher(conn)
        results = matcher.search(kp_id, user_diff)

        print(f"\n找到 {len(results)} 个匹配结果:")
        for rank, res in enumerate(results, 1):
            print(f"\n[Rank {rank}] 综合得分: {res['score']:.4f} ({res['details']})")
            print("-" * 40)
            preview = res['content'].strip().split('\n')[0] + " ..."
            print(f"代码片段: {preview}")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] 程序执行中断: {e}")
    finally:
        # --- 步骤 4: 清理 ---
        if conn:
            conn.close()
            print("\n[Main] 数据库连接已关闭。")


if __name__ == "__main__":
    main()
