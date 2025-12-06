import sqlite3
import json
import os
from db_manager import init_db, insert_baseline_data, DB_NAME
from analyzer import CodeAnalyzer
from matcher import Matcher


def main():
    # 1. 初始化数据库及基线数据
    print("--- Step 1: Init Database ---")
    conn = init_db()
    insert_baseline_data(conn)

    # 2. 读取并解析 Java 长代码
    print("\n--- Step 2: Extract Features from Sample Code ---")
    with open("sample_code.java", "r", encoding="utf-8") as f:
        java_code = f.read()

    # 保存文件记录
    c = conn.cursor()
    c.execute("INSERT INTO code_files (filename, content) VALUES (?, ?)", ("sample_code.java", java_code))
    file_id = c.lastrowid

    # 解析提取
    analyzer = CodeAnalyzer()
    snippets = analyzer.analyze_file(java_code)
    print(f"Detected {len(snippets)} snippets/methods in sample file.")

    # 存入数据库
    for s in snippets:
        print(f"  -> Processed Method (Line {s['start_line']}-{s['end_line']}), Difficulty: {s['difficulty']}")
        c.execute("""
                  INSERT INTO code_snippets
                  (file_id, start_line, end_line, content, complexity_score, ast_features, keywords)
                  VALUES (?, ?, ?, ?, ?, ?, ?)
                  """, (
                      file_id,
                      s['start_line'],
                      s['end_line'],
                      s['content'],
                      s['difficulty'],
                      json.dumps(s['ast_features']),
                      json.dumps(s['keywords'])
                  ))
    conn.commit()
    conn.close()

    # 3. 执行匹配
    print("\n--- Step 3: Executing Matching Algorithm ---")
    # 假设用户选择了 "Exception Handling (Try-Catch)" (ID=101), 期望难度 0.6
    kp_id = 101
    user_diff = 0.6
    print(f"User Query: Knowledge Point ID={kp_id} (Try-Catch), Difficulty={user_diff}")

    matcher = Matcher(DB_NAME)
    results = matcher.search(kp_id, user_diff)

    print(f"\nFound {len(results)} matches:")
    for rank, res in enumerate(results, 1):
        print(f"\n[Rank {rank}] Score: {res['score']} ({res['details']})")
        print("-" * 40)
        # 打印部分代码展示
        preview = res['content'].strip().split('\n')[0] + "..."
        print(f"Code: {preview}")


if __name__ == "__main__":
    main()
