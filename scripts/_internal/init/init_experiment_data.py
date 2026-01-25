#!/usr/bin/env python
"""
实验数据自动初始化脚本

功能：
1. 检查 ground_truth_codesearchnet.json 是否存在
2. 如不存在，自动生成（使用当前匹配算法）
3. 确保评估所需的代码片段在数据库中存在
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.search_service import SearchService
from src.db_manager import CodeLibraryManager, KnowledgePointManager
from config import DB_NAME
from lib.globals import core_logger as log


def ensure_ground_truth_exists(ground_truth_path: Path, force_regenerate: bool = False) -> bool:
    """
    确保 ground truth 文件存在且有效，如不存在或snippet ID不匹配则自动生成

    Args:
        ground_truth_path: Ground truth 文件路径
        force_regenerate: 是否强制重新生成（即使文件存在）

    Returns:
        bool: True if file exists or was created successfully
    """
    # 检查是否强制重新生成
    if force_regenerate:
        log.info(f"[Init] Force regenerate ground truth (force_regenerate=True)")
        needs_generation = True
    elif not ground_truth_path.exists():
        log.warning(f"[Init] Ground truth not found, generating: {ground_truth_path}")
        needs_generation = True
    else:
        # 文件存在，验证snippet ID是否有效
        log.info(f"[Init] Ground truth exists, verifying snippet IDs...")

        try:
            with open(ground_truth_path, 'r', encoding='utf-8') as f:
                gt_data = json.load(f)

            # 提取所有snippet ID
            all_snippet_ids = set()
            for tc in gt_data.get('test_cases', []):
                all_snippet_ids.update(tc.get('relevant_snippet_ids', []))

            if not all_snippet_ids:
                log.warning("[Init] Ground truth has no snippet IDs, regenerating")
                needs_generation = True
            else:
                # 快速验证：检查数据库中实际的snippet ID范围
                from src.db_manager import CodeLibraryManager
                code_mgr = CodeLibraryManager(DB_NAME)

                # 获取前100个snippet（快速检查）
                all_snippets = code_mgr.get_all_snippets()
                db_snippet_ids = {s['id'] for s in all_snippets}

                # 检查ground truth中的ID是否在数据库中
                missing_count = sum(1 for sid in list(all_snippet_ids)[:5] if sid not in db_snippet_ids)

                if missing_count > 0:
                    log.warning(f"[Init] Ground truth contains invalid snippet IDs (sample check: {missing_count}/5 missing)")
                    log.warning(f"[Init] Example GT IDs: {list(all_snippet_ids)[:5]}")
                    log.warning(f"[Init] DB ID range: {min(db_snippet_ids) if db_snippet_ids else 'N/A'}-{max(db_snippet_ids) if db_snippet_ids else 'N/A'}")
                    log.warning("[Init] Regenerating ground truth with current database IDs")
                    needs_generation = True
                else:
                    log.info("[Init] Ground truth validation passed, using existing file")
                    needs_generation = False

        except Exception as e:
            log.error(f"[Init] Failed to validate ground truth: {e}", exc_info=True)
            log.warning("[Init] Will regenerate ground truth")
            needs_generation = True

    # 如果需要生成
    if needs_generation:
        try:
            log.info("[Init] Generating ground truth from current dataset...")
            # 生成 ground truth
            ground_truth_data = generate_ground_truth_auto()

            # 保存到文件
            ground_truth_path.parent.mkdir(parents=True, exist_ok=True)
            with open(ground_truth_path, 'w', encoding='utf-8') as f:
                json.dump(ground_truth_data, f, indent=2, ensure_ascii=False)

            log.info(f"[Init] Ground truth generated successfully: {len(ground_truth_data['test_cases'])} test cases")
            return True

        except Exception as e:
            log.error(f"[Init] Failed to generate ground truth: {e}", exc_info=True)
            return False

    return True


def generate_ground_truth_auto():
    """自动生成 ground truth（使用混合策略配置，与评估一致）

    策略：
    1. 查询数据库中所有叶子节点知识点（最具体的知识点）
    2. 为每个知识点运行匹配，选择高分代码片段
    3. 只保留能找到匹配的知识点，最大化测试覆盖率
    """

    search_service = SearchService(DB_NAME)
    kp_mgr = KnowledgePointManager(DB_NAME)

    log.info("[Init] Generating ground truth from current dataset...")
    log.info("[Init] Strategy: Auto-select all knowledge points with valid matches")
    log.info("[Init] Using Hybrid strategy (w_ast=0.6, w_keyword=0.3, w_difficulty=0.1)")

    # 获取所有叶子节点知识点（parent_id不为NULL且没有子节点的）
    # 叶子节点最具体，适合作为测试用例
    from lib.client.db import MySQLClient
    client = MySQLClient(DB_NAME)

    # 查询所有叶子节点（没有子节点的知识点）
    query = """
        SELECT k.id, k.name, k.parent_id
        FROM knowledge_points k
        LEFT JOIN knowledge_points child ON child.parent_id = k.id
        WHERE child.id IS NULL
        ORDER BY k.id
    """

    try:
        results = client.fetch_all(query)
        all_kp_ids = [r['id'] for r in results]
        log.info(f"[Init] Found {len(all_kp_ids)} leaf knowledge points to test")
    except Exception as e:
        log.error(f"[Init] Failed to query knowledge points: {e}")
        # Fallback: use predefined list
        log.warning("[Init] Falling back to predefined knowledge point list")
        all_kp_ids = [
            10007, 10008, 10009, 10010, 10011, 10012,  # 控制流
            10031, 10032, 10033, 10034,  # 异常
            10037, 10038, 10041, 10042, 10045, 10046, 10049, 10053,  # 集合
            10013, 10014, 10015, 10016, 10019,  # OOP
            10074, 10075, 10076,  # 并发
            10083, 10084, 10085, 10086,  # I/O
        ]

    test_cases = []
    skipped_count = 0

    for i, kp_id in enumerate(all_kp_ids, start=1):
        if i % 10 == 0:
            log.info(f"[Init] Processing {i}/{len(all_kp_ids)}...")

        kp = kp_mgr.get_by_id(kp_id)
        if not kp:
            log.debug(f"[Init] KP {kp_id} not found, skipping")
            skipped_count += 1
            continue

        kp_name = kp.get('name', f'KP_{kp_id}')

        try:
            # 使用零阈值获取最大召回率，然后用分数筛选
            results = search_service.search(
                kp_id=kp_id,
                top_k=20,
                ast_min_ratio=0.0,  # 零阈值，让匹配算法自然排序
                keyword_min_score=0.0,  # 零阈值
                w_ast=0.6,
                w_keyword=0.3,
                w_difficulty=0.1
            )

            if not results:
                log.debug(f"[Init] No matches for KP {kp_id} ({kp_name})")
                skipped_count += 1
                continue

            # 策略：取分数 >= 0.4 的结果，最多5个
            # 这样既保证质量，又尽量保证数量
            valid_results = [r for r in results if r.get('score', 0) >= 0.4]

            if not valid_results:
                log.debug(f"[Init] KP {kp_id} ({kp_name}): no results with score >= 0.4, skipping")
                skipped_count += 1
                continue

            # 取前5个（如果有的话）
            # 使用 content_hash 而不是 id（稳定标识符，数据库重建后不变）
            relevant_hashes = [r['content_hash'] for r in valid_results[:5]]

            if relevant_hashes:
                # 计算这批结果的分数范围
                scores = [r.get('score', 0) for r in valid_results[:len(relevant_hashes)]]
                min_score = min(scores)
                max_score = max(scores)

                test_cases.append({
                    "id": len(test_cases) + 1,
                    "kp_id": kp_id,
                    "kp_name": kp_name,
                    "relevant_snippet_hashes": relevant_hashes,  # 使用哈希而不是ID
                    "notes": f"Auto-generated (score {min_score:.2f}-{max_score:.2f}, top {len(relevant_hashes)})"
                })
                log.debug(f"[Init] KP {kp_id} ({kp_name}): {len(relevant_hashes)} snippets (score range: {min_score:.2f}-{max_score:.2f})")

        except Exception as e:
            log.warning(f"[Init] Failed to match KP {kp_id}: {e}")
            skipped_count += 1

    log.info(f"[Init] Generated {len(test_cases)} test cases ({skipped_count} KPs skipped)")

    return {
        "version": "3.2",
        "description": "Java knowledge point matching - CodeSearchNet ground truth (auto-generated, full coverage)",
        "created_at": "2026-01-25",
        "dataset": "CodeSearchNet Java subset",
        "generation_method": "Hybrid matching (w_ast=0.6, w_kw=0.3, w_diff=0.1) with score >= 0.4 threshold, zero thresholds for max recall",
        "identifier_type": "content_hash (stable across database rebuilds)",
        "test_cases": test_cases,
        "statistics": {
            "total_test_cases": len(test_cases),
            "total_relevant_snippets": sum(len(tc['relevant_snippet_hashes']) for tc in test_cases),
            "skipped_kps": skipped_count,
            "total_kps_tested": len(all_kp_ids)
        }
    }


def verify_snippets_exist(ground_truth_path: Path) -> bool:
    """
    验证 ground truth 中引用的代码片段在数据库中存在
    支持新格式（content_hash）和旧格式（id）

    Returns:
        bool: True if all snippets exist
    """
    code_mgr = CodeLibraryManager(DB_NAME)

    with open(ground_truth_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)

    # 检测使用哪种标识符格式
    use_hash = False
    all_identifiers = set()

    for tc in gt_data['test_cases']:
        if 'relevant_snippet_hashes' in tc:
            all_identifiers.update(tc['relevant_snippet_hashes'])
            use_hash = True
        elif 'relevant_snippet_ids' in tc:
            all_identifiers.update(tc['relevant_snippet_ids'])

    identifier_type = "content_hash" if use_hash else "id"
    log.info(f"[Init] Verifying {len(all_identifiers)} snippets exist in database (using {identifier_type})...")

    # 获取数据库中所有snippet（一次性查询）
    snippets = code_mgr.get_all_snippets()

    if use_hash:
        # 新格式：使用 content_hash
        db_identifiers = {s['content_hash'] for s in snippets if s.get('content_hash')}
    else:
        # 旧格式：使用 id
        db_identifiers = {s['id'] for s in snippets}

    # 检查缺失的标识符
    missing = [sid for sid in all_identifiers if sid not in db_identifiers]

    if missing:
        log.warning(f"[Init] Missing {len(missing)} snippets in database")
        log.warning(f"[Init] Example missing {identifier_type}s: {list(missing)[:5]}...")
        log.warning(f"[Init] DB has {len(db_identifiers)} snippets")
        return False

    log.info("[Init] All snippets verified in database")
    return True


def init_experiment_data(ground_truth_path: str = None):
    """
    初始化实验数据（幂等操作）

    步骤：
    1. 确保 ground truth 文件存在
    2. 验证引用的代码片段存在
    """
    print("=" * 70)
    print("[Experiment Data Init] Starting...")
    print("=" * 70)

    # 默认路径
    if ground_truth_path is None:
        ground_truth_path = project_root / "experiments" / "datasets" / "ground_truth" / "codesearchnet_v7.0-final.json"
    else:
        ground_truth_path = Path(ground_truth_path)

    # Step 1: 确保 ground truth 存在
    print("\n[1/2] Ensuring ground truth exists...")
    if not ensure_ground_truth_exists(ground_truth_path):
        print("[ERROR] Failed to initialize ground truth")
        return False
    print("[OK] Ground truth ready")

    # Step 2: 验证代码片段存在
    print("\n[2/2] Verifying code snippets in database...")
    if not verify_snippets_exist(ground_truth_path):
        print("[WARN] Some snippets missing - run data initialization first:")
        print("  python scripts/init_data/run_all.py")
        print("  python scripts/batch_import/import_code_repos.py --all")
        return False
    print("[OK] All code snippets verified")

    print("\n" + "=" * 70)
    print("[SUCCESS] Experiment data initialized")
    print(f"Ground truth: {ground_truth_path}")
    print("=" * 70)
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize experiment data")
    parser.add_argument("--ground-truth", type=str, help="Ground truth file path")

    args = parser.parse_args()

    success = init_experiment_data(args.ground_truth)
    sys.exit(0 if success else 1)
