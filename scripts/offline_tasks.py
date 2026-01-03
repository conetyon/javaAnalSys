# scripts/offline_tasks.py
"""
离线任务模块
封装数据库初始化、代码分析、匹配测试等离线操作
供 main.py 和其他脚本调用
"""
import os
from typing import List, Dict, Any, Optional

import config
from lib.globals import core_logger as log

from src.db_manager import (
    DatabaseInitializer,
    KnowledgePointManager,
    CodeLibraryManager
)
from src.java_analyzer import JavaAnalyzer
from src.services import SearchService


def init_database(db_name: str = None, insert_baseline: bool = True) -> bool:
    """
    初始化数据库
    
    :param db_name: 数据库名称，默认使用配置文件中的值
    :param insert_baseline: 是否插入预置知识点数据
    :return: 是否成功
    """
    db_name = db_name or config.DB_NAME
    log.info(f"[离线任务] 开始初始化数据库: {db_name}")

    try:
        db_init = DatabaseInitializer(db_name=db_name)
        db_init.init_db()
        log.info("[离线任务] 数据库表结构初始化完成")

        if insert_baseline:
            kp_mgr = KnowledgePointManager(db_name=db_name)
            kp_mgr.insert_baseline_data()
            log.info("[离线任务] 预置知识点数据插入完成")

        return True
    except Exception as e:
        log.error(f"[离线任务] 数据库初始化失败: {e}", exc_info=True)
        return False


def analyze_code_file(
    file_path: str,
    db_name: str = None,
    save_to_db: bool = True
) -> List[Dict[str, Any]]:
    """
    分析 Java 代码文件并提取特征
    
    :param file_path: Java 文件路径
    :param db_name: 数据库名称
    :param save_to_db: 是否保存到数据库
    :return: 提取的代码片段列表
    """
    db_name = db_name or config.DB_NAME
    log.info(f"[离线任务] 开始分析代码文件: {file_path}")

    if not os.path.exists(file_path):
        log.error(f"[离线任务] 文件不存在: {file_path}")
        raise FileNotFoundError(f"未找到文件: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code_content = f.read()

        # 诊断信息
        log.debug(f"[离线任务] 文件大小: {len(code_content)} 字符")
        log.debug(f"[离线任务] 'break' 出现次数: {code_content.count('break')}")
        log.debug(f"[离线任务] 'continue' 出现次数: {code_content.count('continue')}")

        # 分析代码
        analyzer = JavaAnalyzer()
        snippets = analyzer.analyze_file(code_content)
        log.info(f"[离线任务] 检测到 {len(snippets)} 个代码片段")

        # 保存到数据库
        if save_to_db and snippets:
            code_mgr = CodeLibraryManager(db_name=db_name)
            code_mgr.save_analyzed_results(file_path, code_content, snippets)
            log.info("[离线任务] 分析结果已保存到数据库")

        return snippets

    except Exception as e:
        log.error(f"[离线任务] 代码分析失败: {e}", exc_info=True)
        raise


def analyze_code_directory(
    dir_path: str,
    db_name: str = None,
    recursive: bool = True,
    file_extension: str = ".java"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    批量分析目录下的 Java 文件
    
    :param dir_path: 目录路径
    :param db_name: 数据库名称
    :param recursive: 是否递归处理子目录
    :param file_extension: 文件扩展名
    :return: 文件路径 -> 代码片段列表 的映射
    """
    db_name = db_name or config.DB_NAME
    log.info(f"[离线任务] 开始批量分析目录: {dir_path}")

    if not os.path.isdir(dir_path):
        log.error(f"[离线任务] 目录不存在: {dir_path}")
        raise NotADirectoryError(f"目录不存在: {dir_path}")

    results = {}
    file_count = 0
    snippet_count = 0

    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith(file_extension):
                file_path = os.path.join(root, file)
                try:
                    snippets = analyze_code_file(file_path, db_name=db_name, save_to_db=True)
                    results[file_path] = snippets
                    file_count += 1
                    snippet_count += len(snippets)
                except Exception as e:
                    log.warning(f"[离线任务] 文件分析失败: {file_path} - {e}")
                    results[file_path] = []

        if not recursive:
            break

    log.info(f"[离线任务] 批量分析完成: {file_count} 个文件, {snippet_count} 个片段")
    return results


def run_matching_test(
    kp_ids: List[int],
    target_difficulty: float = 0.5,
    top_k: int = 5,
    ast_min_ratio: float = 0.4,
    keyword_min_score: float = 0.4,
    difficulty_mode: str = "relaxed",
    db_name: str = None
) -> Dict[int, List[Dict[str, Any]]]:
    """
    运行匹配测试
    
    :param kp_ids: 知识点 ID 列表
    :param target_difficulty: 目标难度
    :param top_k: 返回结果数量
    :param ast_min_ratio: AST 最低匹配率
    :param keyword_min_score: 关键词最低得分
    :param difficulty_mode: 难度模式
    :param db_name: 数据库名称
    :return: 知识点 ID -> 匹配结果列表 的映射
    """
    db_name = db_name or config.DB_NAME
    log.info(f"[离线任务] 开始匹配测试: kp_ids={kp_ids}")

    search_service = SearchService(db_name=db_name)
    results = {}

    for kp_id in kp_ids:
        log.info(f"[离线任务] 匹配知识点: {kp_id}")
        try:
            matches = search_service.search(
                kp_id=kp_id,
                target_difficulty=target_difficulty,
                top_k=top_k,
                ast_min_ratio=ast_min_ratio,
                keyword_min_score=keyword_min_score,
                difficulty_mode=difficulty_mode
            )
            results[kp_id] = matches
            log.info(f"[离线任务] 知识点 {kp_id} 匹配到 {len(matches)} 条结果")

            # 如果无结果，尝试降低阈值重试
            if not matches:
                log.info(f"[离线任务] 知识点 {kp_id} 无结果，尝试降低阈值重试")
                matches = search_service.search(
                    kp_id=kp_id,
                    target_difficulty=target_difficulty,
                    top_k=2,
                    ast_min_ratio=0,
                    keyword_min_score=0,
                    difficulty_mode=difficulty_mode
                )
                results[kp_id] = matches
                log.info(f"[离线任务] 降阈值后匹配到 {len(matches)} 条结果")

        except Exception as e:
            log.error(f"[离线任务] 知识点 {kp_id} 匹配失败: {e}")
            results[kp_id] = []

    return results


def run_full_pipeline(
    sample_file: str = "./sample_code.java",
    kp_ids: List[int] = None,
    target_difficulty: float = 0.5,
    top_k: int = 5,
    db_name: str = None
) -> Dict[str, Any]:
    """
    运行完整的离线处理流程
    
    :param sample_file: 样本代码文件路径
    :param kp_ids: 要测试的知识点 ID 列表
    :param target_difficulty: 目标难度
    :param top_k: 返回结果数量
    :param db_name: 数据库名称
    :return: 处理结果摘要
    """
    db_name = db_name or config.DB_NAME
    kp_ids = kp_ids or [10011]  # 默认测试知识点

    log.info("=" * 50)
    log.info("[离线任务] 开始完整处理流程")
    log.info("=" * 50)

    result = {
        "db_init": False,
        "code_analysis": {"file": sample_file, "snippets": 0},
        "matching": {}
    }

    # Step 1: 初始化数据库
    print("\n=== Step 1: Init Database ===")
    result["db_init"] = init_database(db_name=db_name)
    if result["db_init"]:
        print("[INFO] 数据库初始化完成")
    else:
        print("[ERROR] 数据库初始化失败")
        return result

    # Step 2: 代码分析
    print("\n=== Step 2: Analyze & Ingest Code ===")
    try:
        snippets = analyze_code_file(sample_file, db_name=db_name)
        result["code_analysis"]["snippets"] = len(snippets)
        print(f"[INFO] 检测到 {len(snippets)} 个代码片段")
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return result
    except Exception as e:
        print(f"[ERROR] 代码分析失败: {e}")
        return result

    # Step 3: 匹配测试
    print("\n=== Step 3: Matching Execution ===")
    if not kp_ids:
        print("[WARN] 未指定知识点 ID，跳过匹配测试")
    else:
        matching_results = run_matching_test(
            kp_ids=kp_ids,
            target_difficulty=target_difficulty,
            top_k=top_k,
            db_name=db_name
        )
        result["matching"] = matching_results

        # 打印匹配结果
        for kp_id, matches in matching_results.items():
            print(f"\n-> Top {len(matches)} Matches for KP {kp_id}:")
            if not matches:
                print("   [EMPTY] 无匹配结果")
            for rank, match in enumerate(matches, 1):
                print(f"\n[#{rank}] Score: {match.get('score')} | "
                      f"AST: {match.get('ast_ratio')} | "
                      f"KW: {match.get('keyword_score')} | "
                      f"Diff: {match.get('difficulty')}")
                if match.get('details'):
                    print(f"Details: {match.get('details')}")
                if match.get('file_path'):
                    print(f"File: {match.get('file_path')}")
                print("-" * 40)
                preview = (match.get('content') or '').strip()[:240].replace('\n', ' ')
                print(f"Code: {preview}...")

    log.info("[离线任务] 完整处理流程结束")
    return result


def print_knowledge_tree(db_name: str = None):
    """
    打印知识点树结构（辅助调试）
    
    :param db_name: 数据库名称
    """
    db_name = db_name or config.DB_NAME
    kp_mgr = KnowledgePointManager(db_name=db_name)
    kp_mgr.print_tree()
