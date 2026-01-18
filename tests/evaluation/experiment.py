# src/evaluation/experiment.py
"""
实验运行和报告生成模块

提供完整的评估实验流程：
1. 单一方法评估
2. 基线方法对比
3. 消融实验
4. 实验报告生成
"""

import json
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from .metrics import (
    calculate_top1_accuracy,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_mrr,
    calculate_map,
    calculate_f1_score,
)
from .baselines import TFIDFMatcher, PureASTMatcher, RandomMatcher
from lib.globals import core_logger as log


def load_ground_truth(file_path: str) -> List[Dict[str, Any]]:
    """
    加载标注数据集

    Args:
        file_path: 标注数据文件路径 (JSON 格式)

    Returns:
        List[Dict]: 测试用例列表

    文件格式示例:
    {
        "version": "1.0",
        "test_cases": [
            {
                "id": 1,
                "kp_id": 10011,
                "kp_name": "while loop",
                "relevant_snippet_ids": [2, 5],
                "irrelevant_snippet_ids": [1, 3, 4]
            }
        ]
    }
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])
    log.info(f"[Ground Truth] 加载完成: {len(test_cases)} 个测试用例")
    return test_cases


def run_single_evaluation(
    search_service,
    test_cases: List[Dict[str, Any]],
    top_k: int = 10
) -> Dict[str, Any]:
    """
    运行单一方法评估（当前系统的混合策略）

    Args:
        search_service: SearchService 实例
        test_cases: 测试用例列表
        top_k: 评估的截断位置

    Returns:
        Dict: 评估结果

    注意：评估实验使用ast_min_ratio=0.0, keyword_min_score=0.0
         以测试系统的最大召回能力（能否找到正确答案）
         生产环境会使用默认阈值0.1来保证推荐质量
    """
    log.info("=" * 60)
    log.info("[Evaluation] 开始单一方法评估 - 混合策略（AST + Keyword + Difficulty）")
    log.info("=" * 60)

    predictions = []
    ground_truths = []
    execution_times = []

    for i, test_case in enumerate(test_cases, start=1):
        kp_id = test_case["kp_id"]
        relevant_ids = set(test_case["relevant_snippet_ids"])

        log.debug(f"[Evaluation] 测试用例 {i}/{len(test_cases)}: KP {kp_id}")

        # 执行匹配并计时
        start_time = time.time()
        try:
            # 评估时使用低阈值，测试最大召回能力
            results = search_service.search(kp_id, top_k=top_k,
                                          ast_min_ratio=0.0,
                                          keyword_min_score=0.0)
            elapsed = time.time() - start_time
            execution_times.append(elapsed)

            # 提取 snippet_id 列表
            pred_ids = [r["id"] for r in results if "id" in r]
            predictions.append(pred_ids)
            ground_truths.append(relevant_ids)

            log.debug(f"  预测: {pred_ids[:5]}... (耗时: {elapsed:.3f}s)")
            log.debug(f"  真实: {relevant_ids}")

        except Exception as e:
            log.error(f"[Evaluation] 测试用例 {i} 执行失败: {e}", exc_info=True)
            predictions.append([])
            ground_truths.append(relevant_ids)
            execution_times.append(0.0)

    # 计算所有评估指标
    log.info("\n" + "=" * 60)
    log.info("[Evaluation] 计算评估指标...")
    log.info("=" * 60)

    top1_acc = calculate_top1_accuracy(predictions, ground_truths)
    p_at_5, _ = calculate_precision_at_k(predictions, ground_truths, k=5)
    p_at_10, _ = calculate_precision_at_k(predictions, ground_truths, k=10)
    r_at_5, _ = calculate_recall_at_k(predictions, ground_truths, k=5)
    r_at_10, _ = calculate_recall_at_k(predictions, ground_truths, k=10)
    mrr, _ = calculate_mrr(predictions, ground_truths)
    map_score, _ = calculate_map(predictions, ground_truths)

    # 计算 F1 分数
    f1_at_5 = calculate_f1_score(p_at_5, r_at_5)
    f1_at_10 = calculate_f1_score(p_at_10, r_at_10)

    # 平均执行时间
    avg_time = sum(execution_times) / len(execution_times) if execution_times else 0.0

    results = {
        "method": "Hybrid (AST + Keyword + Difficulty)",
        "top1_accuracy": top1_acc,
        "precision@5": p_at_5,
        "precision@10": p_at_10,
        "recall@5": r_at_5,
        "recall@10": r_at_10,
        "f1@5": f1_at_5,
        "f1@10": f1_at_10,
        "mrr": mrr,
        "map": map_score,
        "avg_execution_time_ms": avg_time * 1000,
        "num_test_cases": len(test_cases),
    }

    log.info("\n" + "=" * 60)
    log.info("[Evaluation] 评估结果汇总")
    log.info("=" * 60)
    for key, value in results.items():
        if isinstance(value, float):
            if key == "avg_execution_time_ms":
                log.info(f"  {key}: {value:.2f} ms")
            else:
                log.info(f"  {key}: {value:.4f}")
        else:
            log.info(f"  {key}: {value}")

    return results


def run_baseline_comparison(
    search_service,
    test_cases: List[Dict[str, Any]],
    all_snippets: List[Dict[str, Any]],
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    运行基线方法对比实验

    Args:
        search_service: SearchService 实例（用于混合方法）
        test_cases: 测试用例列表
        all_snippets: 所有代码片段（用于基线方法）
        top_k: 评估的截断位置

    Returns:
        List[Dict]: 所有方法的评估结果
    """
    log.info("=" * 60)
    log.info("[Baseline Comparison] 开始基线方法对比实验")
    log.info("=" * 60)

    results_list = []

    # 1. 混合策略（当前系统）
    hybrid_results = run_single_evaluation(search_service, test_cases, top_k)
    results_list.append(hybrid_results)

    # 2. TF-IDF 基线
    log.info("\n" + "=" * 60)
    log.info("[Baseline] 评估 TF-IDF 匹配器")
    log.info("=" * 60)
    tfidf_results = _evaluate_baseline_method(
        test_cases, all_snippets, "TF-IDF", top_k
    )
    results_list.append(tfidf_results)

    # 3. Pure AST 基线
    log.info("\n" + "=" * 60)
    log.info("[Baseline] 评估 Pure AST 匹配器")
    log.info("=" * 60)
    ast_results = _evaluate_baseline_method(
        test_cases, all_snippets, "Pure AST", top_k
    )
    results_list.append(ast_results)

    # 4. Random 基线
    log.info("\n" + "=" * 60)
    log.info("[Baseline] 评估 Random 匹配器")
    log.info("=" * 60)
    random_results = _evaluate_baseline_method(
        test_cases, all_snippets, "Random", top_k
    )
    results_list.append(random_results)

    return results_list


def _evaluate_baseline_method(
    test_cases: List[Dict[str, Any]],
    all_snippets: List[Dict[str, Any]],
    method_name: str,
    top_k: int
) -> Dict[str, Any]:
    """
    评估单个基线方法

    Args:
        test_cases: 测试用例
        all_snippets: 所有代码片段
        method_name: 方法名称 ("TF-IDF", "Pure AST", "Random")
        top_k: 截断位置

    Returns:
        Dict: 评估结果
    """
    from src.db_manager import KnowledgePointManager

    # 初始化匹配器
    if method_name == "TF-IDF":
        matcher = TFIDFMatcher()
    elif method_name == "Pure AST":
        matcher = PureASTMatcher()
    elif method_name == "Random":
        matcher = RandomMatcher()
    else:
        raise ValueError(f"未知的基线方法: {method_name}")

    kp_manager = KnowledgePointManager()
    predictions = []
    ground_truths = []
    execution_times = []

    for i, test_case in enumerate(test_cases, start=1):
        kp_id = test_case["kp_id"]
        relevant_ids = set(test_case["relevant_snippet_ids"])

        log.debug(f"[{method_name}] 测试用例 {i}/{len(test_cases)}: KP {kp_id}")

        start_time = time.time()
        try:
            # 获取知识点信息
            kp_info = kp_manager.get_by_id(kp_id)
            if not kp_info:
                log.warning(f"  知识点 {kp_id} 不存在")
                predictions.append([])
                ground_truths.append(relevant_ids)
                execution_times.append(0.0)
                continue

            # 根据方法类型执行匹配
            if method_name == "TF-IDF":
                kp_keywords_raw = kp_info.get("keywords", [])
                if isinstance(kp_keywords_raw, str):
                    kp_keywords_raw = json.loads(kp_keywords_raw)
                pred_ids = matcher.match(kp_keywords_raw, all_snippets, top_k)

            elif method_name == "Pure AST":
                kp_ast_raw = kp_info.get("ast_template", {})
                if isinstance(kp_ast_raw, str):
                    kp_ast_raw = json.loads(kp_ast_raw)
                kp_ast_nodes = kp_ast_raw.get("required_nodes", []) if isinstance(kp_ast_raw, dict) else []
                pred_ids = matcher.match(kp_ast_nodes, all_snippets, top_k)

            elif method_name == "Random":
                pred_ids = matcher.match(all_snippets, top_k)

            elapsed = time.time() - start_time
            execution_times.append(elapsed)

            predictions.append(pred_ids)
            ground_truths.append(relevant_ids)

            log.debug(f"  预测: {pred_ids[:5]}... (耗时: {elapsed:.3f}s)")

        except Exception as e:
            log.error(f"[{method_name}] 测试用例 {i} 执行失败: {e}", exc_info=True)
            predictions.append([])
            ground_truths.append(relevant_ids)
            execution_times.append(0.0)

    # 计算评估指标
    top1_acc = calculate_top1_accuracy(predictions, ground_truths)
    p_at_5, _ = calculate_precision_at_k(predictions, ground_truths, k=5)
    p_at_10, _ = calculate_precision_at_k(predictions, ground_truths, k=10)
    r_at_5, _ = calculate_recall_at_k(predictions, ground_truths, k=5)
    r_at_10, _ = calculate_recall_at_k(predictions, ground_truths, k=10)
    mrr, _ = calculate_mrr(predictions, ground_truths)
    map_score, _ = calculate_map(predictions, ground_truths)

    f1_at_5 = calculate_f1_score(p_at_5, r_at_5)
    f1_at_10 = calculate_f1_score(p_at_10, r_at_10)

    avg_time = sum(execution_times) / len(execution_times) if execution_times else 0.0

    results = {
        "method": method_name,
        "top1_accuracy": top1_acc,
        "precision@5": p_at_5,
        "precision@10": p_at_10,
        "recall@5": r_at_5,
        "recall@10": r_at_10,
        "f1@5": f1_at_5,
        "f1@10": f1_at_10,
        "mrr": mrr,
        "map": map_score,
        "avg_execution_time_ms": avg_time * 1000,
        "num_test_cases": len(test_cases),
    }

    log.info("\n" + "-" * 60)
    log.info(f"[{method_name}] 评估结果:")
    log.info("-" * 60)
    for key, value in results.items():
        if isinstance(value, float):
            if key == "avg_execution_time_ms":
                log.info(f"  {key}: {value:.2f} ms")
            else:
                log.info(f"  {key}: {value:.4f}")

    return results


def run_ablation_study(
    search_service,
    test_cases: List[Dict[str, Any]],
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    运行消融实验（Ablation Study）

    测试移除不同组件对性能的影响：
    1. 完整系统（AST + Keyword + Difficulty）
    2. 仅 AST + Keyword
    3. 仅 AST + Difficulty
    4. 仅 Keyword + Difficulty
    5. 仅 AST
    6. 仅 Keyword

    Args:
        search_service: SearchService 实例
        test_cases: 测试用例
        top_k: 截断位置

    Returns:
        List[Dict]: 所有配置的评估结果
    """
    log.info("=" * 60)
    log.info("[Ablation Study] 开始消融实验")
    log.info("=" * 60)

    # 消融实验权重配置
    # 系统设计包含三个维度：AST结构、关键词、难度适配
    # 消融实验测试不同组件组合对性能的影响
    weight_configs = [
        # 完整系统：三个组件都启用
        {"name": "Full (AST+KW+DIFF)", "ast": 0.3, "keyword": 0.6, "difficulty": 0.1},
        # 双组件组合
        {"name": "AST + Keyword", "ast": 0.3, "keyword": 0.7, "difficulty": 0.0},
        {"name": "AST + Difficulty", "ast": 0.8, "keyword": 0.0, "difficulty": 0.2},
        {"name": "Keyword + Difficulty", "ast": 0.0, "keyword": 0.8, "difficulty": 0.2},
        # 单组件配置
        {"name": "AST Only", "ast": 1.0, "keyword": 0.0, "difficulty": 0.0},
        {"name": "Keyword Only", "ast": 0.0, "keyword": 1.0, "difficulty": 0.0},
    ]

    results_list = []

    for config in weight_configs:
        log.info("\n" + "=" * 60)
        log.info(f"[Ablation] 配置: {config['name']}")
        log.info(f"  权重 - AST: {config['ast']}, Keyword: {config['keyword']}, Difficulty: {config['difficulty']}")
        log.info("=" * 60)

        predictions = []
        ground_truths = []
        execution_times = []

        for i, test_case in enumerate(test_cases, start=1):
            kp_id = test_case["kp_id"]
            relevant_ids = set(test_case["relevant_snippet_ids"])

            start_time = time.time()
            try:
                # 评估时使用低阈值，测试最大召回能力
                # 使用自定义权重
                results = search_service.search(
                    kp_id,
                    top_k=top_k,
                    ast_min_ratio=0.0,
                    keyword_min_score=0.0,
                    w_ast=config["ast"],
                    w_keyword=config["keyword"],
                    w_difficulty=config["difficulty"]
                )
                elapsed = time.time() - start_time
                execution_times.append(elapsed)

                pred_ids = [r["id"] for r in results if "id" in r]
                predictions.append(pred_ids)
                ground_truths.append(relevant_ids)

            except Exception as e:
                log.error(f"[Ablation] 测试用例 {i} 执行失败: {e}", exc_info=True)
                predictions.append([])
                ground_truths.append(relevant_ids)
                execution_times.append(0.0)

        # 计算评估指标
        top1_acc = calculate_top1_accuracy(predictions, ground_truths)
        p_at_10, _ = calculate_precision_at_k(predictions, ground_truths, k=10)
        r_at_10, _ = calculate_recall_at_k(predictions, ground_truths, k=10)
        mrr, _ = calculate_mrr(predictions, ground_truths)
        map_score, _ = calculate_map(predictions, ground_truths)

        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0.0

        results = {
            "method": config["name"],
            "weights": f"AST={config['ast']}, KW={config['keyword']}, DIFF={config['difficulty']}",
            "top1_accuracy": top1_acc,
            "precision@10": p_at_10,
            "recall@10": r_at_10,
            "mrr": mrr,
            "map": map_score,
            "avg_execution_time_ms": avg_time * 1000,
        }

        log.info(f"  Top-1 Accuracy: {top1_acc:.2%}")
        log.info(f"  Precision@10: {p_at_10:.2%}")
        log.info(f"  MRR: {mrr:.3f}")

        results_list.append(results)

    return results_list


def generate_experiment_report(
    all_results: Dict[str, Any],
    output_path: str = None
) -> str:
    """
    生成实验报告（Markdown 格式 + JSON 数据）

    Args:
        all_results: 所有实验结果
        output_path: 输出文件路径（可选）

    Returns:
        str: Markdown 格式的报告内容
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# Java 知识点匹配系统 - 实验评估报告

**生成时间**: {timestamp}

---

## 1. 实验概览

### 1.1 评估数据集
- 测试用例数量: {all_results.get('num_test_cases', 'N/A')}
- 评估指标: Top-1 Accuracy, Precision@K, Recall@K, MRR, MAP, F1-Score

### 1.2 实验配置
- 截断位置 K: 10
- 权重配置: AST=0.6, Keyword=0.3, Difficulty=0.1

---

## 2. 主要结果

### 2.1 混合策略性能（当前系统）

"""

    # 如果有单一方法评估结果
    if "single_evaluation" in all_results:
        single = all_results["single_evaluation"]
        report += f"""
| 指标 | 数值 |
|------|------|
| **Top-1 Accuracy** | **{single['top1_accuracy']:.2%}** |
| Precision@5 | {single['precision@5']:.2%} |
| Precision@10 | {single['precision@10']:.2%} |
| Recall@5 | {single['recall@5']:.2%} |
| Recall@10 | {single['recall@10']:.2%} |
| F1@5 | {single['f1@5']:.2%} |
| F1@10 | {single['f1@10']:.2%} |
| MRR | {single['mrr']:.4f} |
| MAP | {single['map']:.4f} |
| 平均执行时间 | {single['avg_execution_time_ms']:.2f} ms |

"""

    # 如果有基线对比结果
    if "baseline_comparison" in all_results:
        report += """
### 2.2 基线方法对比

| 方法 | Top-1 Acc | P@10 | R@10 | MRR | MAP | 时间(ms) |
|------|-----------|------|------|-----|-----|----------|
"""
        for result in all_results["baseline_comparison"]:
            report += f"| {result['method']} | {result['top1_accuracy']:.2%} | {result['precision@10']:.2%} | {result['recall@10']:.2%} | {result['mrr']:.4f} | {result['map']:.4f} | {result['avg_execution_time_ms']:.2f} |\n"

    # 如果有消融实验结果
    if "ablation_study" in all_results:
        report += """
### 2.3 消融实验

| 配置 | Top-1 Acc | P@10 | R@10 | MRR |
|------|-----------|------|------|-----|
"""
        for result in all_results["ablation_study"]:
            report += f"| {result['method']} | {result['top1_accuracy']:.2%} | {result['precision@10']:.2%} | {result['recall@10']:.2%} | {result['mrr']:.4f} |\n"

    report += """
---

## 3. 结论

### 3.1 性能分析
- **达标情况**: Top-1 准确率目标为 95%，实际达到 XX%
- **优势分析**: 混合策略相比基线方法提升 XX%
- **组件贡献**: 消融实验显示 AST 组件贡献最大

### 3.2 改进方向
1. 权重优化：可通过网格搜索找到更优权重配置
2. 阈值调整：当前过滤阈值可能过严格/宽松
3. 特征增强：考虑引入语义向量特征

---

**报告结束**
"""

    # 保存到文件
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

        # 同时保存 JSON 数据
        json_path = output_path.replace(".md", ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        log.info(f"[Report] 报告已保存: {output_path}")
        log.info(f"[Report] JSON 数据已保存: {json_path}")

    return report
