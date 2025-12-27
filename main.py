# main.py
import os
import traceback
import config
from lib.globals import core_logger as log

from src.db_manager import (
    DatabaseInitializer,
    KnowledgePointManager,
    CodeLibraryManager
)
from src.java_analyzer import JavaAnalyzer
from src.services.search_service import SearchService

# 指定样本路径（确保存在）
SAMPLE_FILE_PATH = "./sample_code.java"

# 直接指定检索参数（无需环境变量）
KP_IDS = [10083]            # 例如 10010, 10011, 10031, 10034, 10083
TARGET_DIFFICULTY = 0.6     # 0~1
TOP_K = 5                   # 返回前K条
AST_MIN_RATIO = 0.5         # AST结构匹配阈值
KEYWORD_MIN_SCORE = 0.6     # 关键词匹配阈值
DIFFICULTY_MODE = "relaxed" # strict / relaxed


def main():
    try:
        DB_NAME = config.DB_NAME

        # --- Step 1: 初始化数据库（不改动知识点） ---
        print("\n=== Step 1: Init Database ===")
        db_init = DatabaseInitializer(db_name=DB_NAME)
        code_mgr = CodeLibraryManager(db_name=DB_NAME)
        kp_mgr = KnowledgePointManager(db_name=DB_NAME)
        db_init.init_db()
        kp_mgr.insert_baseline_data()
        print("[INFO] 数据库初始化完成")

        # --- Step 2: 代码分析与入库（幂等） ---
        print("\n=== Step 2: Analyze & Ingest Code ===")
        if not os.path.exists(SAMPLE_FILE_PATH):
            raise FileNotFoundError(f"未找到样本文件: {SAMPLE_FILE_PATH}，请确认路径是否正确")

        with open(SAMPLE_FILE_PATH, "r", encoding="utf-8") as f:
            code_content = f.read()

        # 简单诊断：是否包含 break/continue（针对 KP 10012）
        print(f"[DIAG] 'break' 出现次数: {code_content.count('break')}, "
              f"'continue' 出现次数: {code_content.count('continue')}")

        analyzer = JavaAnalyzer()
        snippets = analyzer.analyze_file(code_content)
        print(f"-> Detected {len(snippets)} snippets in {SAMPLE_FILE_PATH}")
        if snippets:
            code_mgr.save_analyzed_results(SAMPLE_FILE_PATH, code_content, snippets)
            print("[INFO] 分析结果已入库（幂等保存）")
        else:
            print("[WARN] 未检测到可用片段，后续匹配可能为空")

        # --- Step 3: 搜索匹配 ---
        print("\n=== Step 3: Matching Execution ===")
        search_service = SearchService(db_name=DB_NAME)

        if not KP_IDS:
            print("[WARN] 未指定知识点ID（KP_IDS 为空），请在文件顶部修改 KP_IDS 列表后重试。")
            return

        for kp_id in KP_IDS:
            print(f"\n-> Query: KP_ID={kp_id}, Target_Diff={TARGET_DIFFICULTY}, "
                  f"AST_Min={AST_MIN_RATIO}, KW_Min={KEYWORD_MIN_SCORE}, Mode={DIFFICULTY_MODE}, TopK={TOP_K}")
            try:
                results = search_service.search(
                    kp_id=kp_id,
                    target_difficulty=TARGET_DIFFICULTY,
                    top_k=TOP_K,
                    ast_min_ratio=AST_MIN_RATIO,
                    keyword_min_score=KEYWORD_MIN_SCORE,
                    difficulty_mode=DIFFICULTY_MODE
                )
            except Exception as e:
                print(f"[ERROR] 搜索失败: KP_ID={kp_id} | {e}")
                continue

            # 若无结果，自动降阈值重试一次，便于定位问题（可注释掉）
            if not results:
                print("[INFO] 无匹配结果，尝试降阈值重试：AST_Min=0.3, KW_Min=0.3")
                try:
                    results = search_service.search(
                        kp_id=kp_id,
                        target_difficulty=TARGET_DIFFICULTY,
                        top_k=TOP_K,
                        ast_min_ratio=0.3,
                        keyword_min_score=0.3,
                        difficulty_mode=DIFFICULTY_MODE
                    )
                except Exception as e:
                    print(f"[ERROR] 降阈值重试失败: KP_ID={kp_id} | {e}")

            # 去重输出
            seen = set()
            dedup_results = []
            for r in results or []:
                preview_key = (r.get('content') or '').strip()
                if preview_key and preview_key not in seen:
                    dedup_results.append(r)
                    seen.add(preview_key)

            print(f"\n-> Top {len(dedup_results)} Matches for KP {kp_id}:")
            if not dedup_results:
                print("   [EMPTY] 可能原因：1) 样例代码不包含该知识点关键结构；"
                      "2) 阈值过高；3) 知识点定义与分析器AST节点命名不一致；"
                      "4) 知识点被其他初始化逻辑覆盖。")
                print("   建议：a) 在样例中加入对应代码片段；b) 暂时降低阈值；"
                      "c) 改查更通用的KP（如 10010 for loop 或 10031 try-catch）以验证链路。")
            for rank, res in enumerate(dedup_results, 1):
                score = res.get('score')
                details = res.get('details')
                ast_ratio = res.get('ast_ratio')
                kw_score = res.get('keyword_score')
                difficulty = res.get('difficulty')
                file_path = res.get('file_path') or res.get('source_path')

                print(f"\n[#{rank}] Score: {score} | AST: {ast_ratio} | KW: {kw_score} | Diff: {difficulty}")
                if details:
                    print(f"Details: {details}")
                if file_path:
                    print(f"File: {file_path}")
                print("-" * 40)
                preview = (res.get('content') or '').strip()[:240].replace('\n', ' ')
                print(f"Code: {preview}...")

    except Exception as e:
        traceback.print_exc()
        print(f"\n[CRITICAL ERROR] {e}")


if __name__ == "__main__":
    main()
