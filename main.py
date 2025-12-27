# main.py
import os
import json
import traceback
import config
from lib.globals import core_logger as log

from src.db_manager import (
    DatabaseInitializer,
    CodeLibraryManager,
    KnowledgePointManager
)
from src.java_analyzer import JavaAnalyzer
from src.services.search_service import SearchService

SAMPLE_FILE_PATH = "sample_code.java"

SAMPLE_JAVA_CONTENT = """// 这是一个模拟的长文件 content
import java.io.*;

public class DataProcessor {
    // Snippet 1: 简单的Getter，不应该匹配 Try-Catch
    public String getName() {
        return "Processor";
    }

    // Snippet 2: 包含 Try-Catch 的 IO 操作，应该匹配
    public void processFile(String path) {
        System.out.println("Starting...");
        try {
            BufferedReader reader = new BufferedReader(new FileReader(path));
            String line = reader.readLine();
            while (line != null) {
                System.out.println(line);
                line = reader.readLine();
            }
        } catch (FileNotFoundException e) {
            System.err.println("File missing");
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            System.out.println("Done.");
        }
    }

    // Snippet 3: 复杂的逻辑但没有 Try-Catch
    public int calculate(int n) {
        if (n < 0) return 0;
        int sum = 0;
        for (int i=0; i<n; i++) {
            sum += i;
        }
        return sum;
    }
}
"""


def ensure_sample_file(filepath: str, content: str, overwrite: bool = True):
    """确保 sample.java 存在（默认覆盖写入，以便分析器产生片段）"""
    if overwrite or not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[INFO] 写入示例文件: {filepath}")
    else:
        print(f"[INFO] 保留现有示例文件: {filepath}")
    return filepath


def ensure_kp_try_catch(kp_mgr: KnowledgePointManager, kp_id: int = 10001):
    """
    确保知识点 10001 为 Try-Catch IO 基础操作，
    以便与包含 try/catch/finally 的代码片段稳定匹配。
    """
    kp_name = "Try-Catch IO 基础操作"
    required_nodes = [
        "method_declaration", "try_statement", "catch_clause",
        "finally_block", "method_invocation"
    ]
    kp_keywords = [
        "try", "catch", "finally", "IOException",
        "FileNotFoundException", "read"
    ]
    ast_template_json = json.dumps({"required_nodes": required_nodes}, ensure_ascii=False)
    keywords_json = json.dumps(kp_keywords, ensure_ascii=False)

    sql = """
    INSERT INTO knowledge_points (id, name, ast_template, keywords)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      name = VALUES(name),
      ast_template = VALUES(ast_template),
      keywords = VALUES(keywords)
    """
    params = (kp_id, kp_name, ast_template_json, keywords_json)

    client = kp_mgr._get_client()
    client.execute(sql, params)
    print(f"[Knowledge Manager] 已确保 KP {kp_id} = '{kp_name}' 配置为 Try-Catch IO。")


def main():
    try:
        DB_NAME = config.DB_NAME

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
        ensure_kp_try_catch(kb_mgr, kp_id=DEFAULT_KP_ID)

        # --- 阶段 2: 代码分析与入库（幂等） ---
        print("\n=== Step 2: Analyze & Ingest Code ===")
        # 1) 基线片段：幂等 Upsert，不会重复插入，不会推动自增主键
        code_mgr.insert_baseline_code_data()

        # 2) 写入/更新示例 Java 文件，并分析入库；内容不变则跳过保存（幂等）
        sample_path = ensure_sample_file(SAMPLE_FILE_PATH, SAMPLE_JAVA_CONTENT, overwrite=True)
        with open(sample_path, "r", encoding="utf-8") as f:
            code_content = f.read()
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
            top_k=5,
            ast_min_ratio=0.4,
            keyword_min_score=0.4,
            difficulty_mode="relaxed"
        )

        # --- 阶段 4: 结果展示 ---
        print(f"\n-> Top {len(results)} Matches:")
        for rank, res in enumerate(results, 1):
            print(f"\n[#{rank}] Score: {res['score']} | {res['details']}")
            print("-" * 40)
            preview = res['content'].strip()[:160].replace('\n', ' ')
            print(f"Code: {preview}...")
    except Exception as e:
        traceback.print_exc()
        print(f"\n[CRITICAL ERROR] {e}")


if __name__ == "__main__":
    main()
