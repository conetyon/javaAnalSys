#!/usr/bin/env python
# scripts/_internal/run_evaluation.py
"""
评估脚本 - 运行分级评估实验并生成报告

使用规则生成 Ground Truth，计算 Graded Precision、nDCG、Binary Precision 等指标。

用法：
    python scripts/_internal/run_evaluation.py                # 完整评估（32 KP + 消融实验）
    python scripts/_internal/run_evaluation.py --quick        # 快速评估（仅评估，跳过消融）
    python scripts/_internal/run_evaluation.py --pilot        # 仅评估 Pilot KP（5个）
    python scripts/_internal/run_evaluation.py --ablation     # 仅运行消融实验
"""

import sys
import json
import math
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from experiments.evaluation.rules import (
    KP_RULES,
    calculate_feature_grade,
    PILOT_KP_IDS,
    get_all_kp_ids
)
from src.services.search_service import SearchService
from src.db_manager import CodeLibraryManager
from lib.client.db import MySQLClient
from lib.globals import core_logger as log
from config import DB_NAME


def ndcg_at_k(grades, k=10):
    """计算 nDCG@K"""
    def dcg(g_list):
        return sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(g_list))

    actual = grades[:k]
    ideal = sorted(grades, reverse=True)[:k]

    dcg_actual = dcg(actual)
    dcg_ideal = dcg(ideal)

    return dcg_actual / dcg_ideal if dcg_ideal > 0 else 0.0


def run_graded_evaluation(search_service, kp_ids, top_k=10):
    """
    运行分级评估

    Args:
        search_service: SearchService 实例
        kp_ids: 要评估的 KP ID 列表
        top_k: 评估的截断位置

    Returns:
        Dict: 评估结果
    """
    all_grades = []
    kp_results = []
    no_results_kps = []

    total = len(kp_ids)
    for idx, kp_id in enumerate(kp_ids, 1):
        rule = KP_RULES.get(kp_id)
        if not rule:
            continue

        # 进度显示
        if idx % 10 == 0 or idx == total:
            print(f"  进度: {idx}/{total} ({100*idx/total:.0f}%)")

        try:
            results = search_service.search(
                kp_id,
                top_k=top_k,
                source='codesearchnet',
                ast_min_ratio=0.0,
                keyword_min_score=0.0
            )
        except Exception as e:
            log.error(f"KP {kp_id} 搜索失败: {e}")
            continue

        if not results:
            no_results_kps.append(kp_id)
            continue

        grades = []
        for r in results:
            snippet = {
                'ast_features': r.get('ast_features', []),
                'method_name': r.get('method_name', ''),
                'lines_of_code': r.get('lines_of_code', 0),
                'keywords': r.get('keywords', [])
            }
            grade = calculate_feature_grade(snippet, rule)
            grades.append(grade)

        all_grades.extend(grades)

        # KP 级别指标
        g2 = grades.count(2)
        g1 = grades.count(1)
        g0 = grades.count(0)
        k = len(grades)
        graded_prec = (2 * g2 + g1) / (2 * k) if k > 0 else 0
        binary_prec = (g2 + g1) / k if k > 0 else 0
        ndcg = ndcg_at_k(grades, k=top_k)

        kp_results.append({
            'kp_id': kp_id,
            'name': rule['name'],
            'G2': g2, 'G1': g1, 'G0': g0,
            'graded_precision': graded_prec,
            'binary_precision': binary_prec,
            'ndcg': ndcg
        })

    # 总体指标
    total_snippets = len(all_grades)
    g2_total = all_grades.count(2)
    g1_total = all_grades.count(1)
    g0_total = all_grades.count(0)

    overall_graded_prec = (2 * g2_total + g1_total) / (2 * total_snippets) if total_snippets > 0 else 0
    overall_binary_prec = (g2_total + g1_total) / total_snippets if total_snippets > 0 else 0
    avg_ndcg = sum(r['ndcg'] for r in kp_results) / len(kp_results) if kp_results else 0

    return {
        'evaluated_kps': len(kp_results),
        'total_kps': len(kp_ids),
        'no_results_kps': no_results_kps,
        'total_snippets': total_snippets,
        'G2': g2_total,
        'G1': g1_total,
        'G0': g0_total,
        'graded_precision': overall_graded_prec,
        'binary_precision': overall_binary_prec,
        'avg_ndcg': avg_ndcg,
        'kp_results': kp_results
    }


def run_graded_ablation(search_service, kp_ids, top_k=10):
    """
    运行分级消融实验

    测试不同权重配置对分级评估指标的影响
    """
    weight_configs = [
        {"name": "Full (AST+KW+DIFF)", "ast": 0.2, "keyword": 0.7, "difficulty": 0.1},
        {"name": "AST + Keyword", "ast": 0.3, "keyword": 0.7, "difficulty": 0.0},
        {"name": "Keyword + Difficulty", "ast": 0.0, "keyword": 0.9, "difficulty": 0.1},
        {"name": "AST + Difficulty", "ast": 0.9, "keyword": 0.0, "difficulty": 0.1},
        {"name": "AST Only", "ast": 1.0, "keyword": 0.0, "difficulty": 0.0},
        {"name": "Keyword Only", "ast": 0.0, "keyword": 1.0, "difficulty": 0.0},
    ]

    results = []

    for cfg_idx, config in enumerate(weight_configs, 1):
        print(f"\n[消融 {cfg_idx}/{len(weight_configs)}] {config['name']}")
        print(f"  权重: AST={config['ast']}, KW={config['keyword']}, DIFF={config['difficulty']}")

        all_grades = []
        kp_count = 0

        for kp_id in kp_ids:
            rule = KP_RULES.get(kp_id)
            if not rule:
                continue

            try:
                search_results = search_service.search(
                    kp_id,
                    top_k=top_k,
                    source='codesearchnet',
                    ast_min_ratio=0.0,
                    keyword_min_score=0.0,
                    w_ast=config['ast'],
                    w_keyword=config['keyword'],
                    w_difficulty=config['difficulty']
                )
            except Exception:
                continue

            if not search_results:
                continue

            kp_count += 1
            for r in search_results:
                snippet = {
                    'ast_features': r.get('ast_features', []),
                    'method_name': r.get('method_name', ''),
                    'lines_of_code': r.get('lines_of_code', 0),
                    'keywords': r.get('keywords', [])
                }
                grade = calculate_feature_grade(snippet, rule)
                all_grades.append(grade)

        total = len(all_grades)
        g2 = all_grades.count(2)
        g1 = all_grades.count(1)
        g0 = all_grades.count(0)

        graded_prec = (2 * g2 + g1) / (2 * total) if total > 0 else 0
        binary_prec = (g2 + g1) / total if total > 0 else 0

        results.append({
            'name': config['name'],
            'weights': {'ast': config['ast'], 'keyword': config['keyword'], 'difficulty': config['difficulty']},
            'evaluated_kps': kp_count,
            'total_snippets': total,
            'G2': g2, 'G1': g1, 'G0': g0,
            'graded_precision': graded_prec,
            'binary_precision': binary_prec
        })

        print(f"  结果: Binary={binary_prec:.1%}, Graded={graded_prec:.1%}, G2:{g2} G1:{g1} G0:{g0}")

    return results


def generate_report(eval_results, ablation_results, output_path, pilot_mode):
    """生成评估报告"""

    report_lines = [
        "# Java 知识点匹配系统 - 分级评估报告",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 1. 评估概览",
        "",
        f"- 评估模式: {'Pilot (5 KP)' if pilot_mode else 'Full (32 KP)'}",
        f"- 评估 KP 数: {eval_results['evaluated_kps']}/{eval_results['total_kps']}",
        f"- 评估片段总数: {eval_results['total_snippets']}",
        "",
    ]

    if eval_results['no_results_kps']:
        report_lines.append(f"- 无结果 KP (数据缺失): {eval_results['no_results_kps']}")
        report_lines.append("")

    report_lines.extend([
        "---",
        "",
        "## 2. 核心指标",
        "",
        "| 指标 | 数值 | 说明 |",
        "|------|------|------|",
        f"| **Binary Precision** | **{eval_results['binary_precision']:.1%}** | 相关结果比例 (G1+G2) |",
        f"| Graded Precision | {eval_results['graded_precision']:.1%} | 加权精确率 |",
        f"| Average nDCG@10 | {eval_results['avg_ndcg']:.3f} | 排名质量 |",
        "",
        "### 分级分布",
        "",
        f"- G2 (高度相关): {eval_results['G2']} ({eval_results['G2']/eval_results['total_snippets']*100:.1f}%)",
        f"- G1 (部分相关): {eval_results['G1']} ({eval_results['G1']/eval_results['total_snippets']*100:.1f}%)",
        f"- G0 (不相关): {eval_results['G0']} ({eval_results['G0']/eval_results['total_snippets']*100:.1f}%)",
        "",
    ])

    if ablation_results:
        report_lines.extend([
            "---",
            "",
            "## 3. 消融实验",
            "",
            "| 配置 | Binary Precision | Graded Precision | G2 | G1 | G0 |",
            "|------|-----------------|------------------|----|----|----| ",
        ])

        for r in ablation_results:
            report_lines.append(
                f"| {r['name']} | {r['binary_precision']:.1%} | {r['graded_precision']:.1%} | "
                f"{r['G2']} | {r['G1']} | {r['G0']} |"
            )

        report_lines.extend([
            "",
            "### 消融分析",
            "",
            "**关键发现**:",
        ])

        # 找出最佳配置
        best = max(ablation_results, key=lambda x: x['binary_precision'])
        report_lines.append(f"- 最佳配置: {best['name']} (Binary Precision = {best['binary_precision']:.1%})")
        report_lines.append("")

    report_lines.extend([
        "---",
        "",
        "## 4. 结论",
        "",
        f"- **{eval_results['binary_precision']:.1%}** 的搜索结果包含目标知识点特征",
        f"- 只有 **{eval_results['G0']/eval_results['total_snippets']*100:.1f}%** 的结果是完全不相关的",
        f"- nDCG={eval_results['avg_ndcg']:.3f} 表示相关结果排名靠前",
        "",
    ])

    # 写入文件
    report_content = "\n".join(report_lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    # 同时保存 JSON
    json_path = output_path.replace('.md', '.json')
    json_data = {
        'generated_at': datetime.now().isoformat(),
        'mode': 'pilot' if pilot_mode else 'full',
        'evaluation': eval_results,
        'ablation': ablation_results
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    return report_content


def save_to_database(eval_results, ablation_results, pilot_mode):
    """
    保存评估结果到 experiment_runs 表

    Args:
        eval_results: 评估结果
        ablation_results: 消融实验结果
        pilot_mode: 是否为 pilot 模式
    """
    try:
        client = MySQLClient(db=DB_NAME)

        # 生成唯一的 run_name
        mode = 'pilot' if pilot_mode else 'full'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        run_name = f"graded_eval_{mode}_{timestamp}"

        # 准备 config 和 metrics
        config = {
            'mode': mode,
            'top_k': 10,
            'kp_count': eval_results['evaluated_kps'],
            'dataset': 'codesearchnet'
        }

        metrics = {
            'binary_precision': eval_results['binary_precision'],
            'graded_precision': eval_results['graded_precision'],
            'avg_ndcg': eval_results['avg_ndcg'],
            'total_snippets': eval_results['total_snippets'],
            'G2': eval_results['G2'],
            'G1': eval_results['G1'],
            'G0': eval_results['G0'],
            'kp_results': eval_results['kp_results']
        }

        if ablation_results:
            metrics['ablation'] = ablation_results

        # 插入数据库
        sql = """
            INSERT INTO experiment_runs (run_name, dataset_name, config, metrics)
            VALUES (%s, %s, %s, %s)
        """
        client.execute(sql, (
            run_name,
            'codesearchnet',
            json.dumps(config, ensure_ascii=False),
            json.dumps(metrics, ensure_ascii=False)
        ))

        print(f"[OK] 结果已保存到数据库: {run_name}")
        return True

    except Exception as e:
        print(f"[WARN] 保存到数据库失败: {e}")
        log.warning(f"保存评估结果到数据库失败: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="运行分级评估实验")
    parser.add_argument("--quick", action="store_true", help="快速评估（跳过消融实验）")
    parser.add_argument("--pilot", action="store_true", help="仅评估 Pilot KP（5个）")
    parser.add_argument("--ablation", action="store_true", help="仅运行消融实验")
    parser.add_argument("--top-k", type=int, default=10, help="评估的截断位置 K")
    parser.add_argument("--output", type=str,
                        default=str(project_root / "experiments" / "results" / "report.md"),
                        help="输出报告路径")

    args = parser.parse_args()

    print("=" * 80)
    print("[*] Java 知识点匹配系统 - 分级评估")
    print("=" * 80)

    # 确定评估的 KP 列表
    if args.pilot:
        kp_ids = PILOT_KP_IDS
        print(f"[模式] Pilot (5 KP)")
    else:
        kp_ids = get_all_kp_ids()
        print(f"[模式] Full ({len(kp_ids)} KP)")

    print(f"[Top-K] {args.top_k}")
    print(f"[输出] {args.output}")
    print("=" * 80)

    # 初始化服务
    print("\n[1/3] 初始化服务...")
    try:
        search_service = SearchService(db_name=DB_NAME)
        print("[OK] 服务初始化成功")
    except Exception as e:
        print(f"[ERROR] 服务初始化失败: {e}")
        return 1

    eval_results = None
    ablation_results = None

    # 运行评估
    if not args.ablation:
        print(f"\n[2/3] 运行分级评估...")
        eval_results = run_graded_evaluation(search_service, kp_ids, args.top_k)
        print(f"[OK] 评估完成")
        print(f"  Binary Precision: {eval_results['binary_precision']:.1%}")
        print(f"  Graded Precision: {eval_results['graded_precision']:.1%}")
        print(f"  Average nDCG: {eval_results['avg_ndcg']:.3f}")

    # 运行消融实验
    if not args.quick or args.ablation:
        print(f"\n[3/3] 运行消融实验...")
        ablation_results = run_graded_ablation(search_service, kp_ids, args.top_k)
        print("[OK] 消融实验完成")

    # 生成报告
    if eval_results or ablation_results:
        # 如果只运行了消融实验，需要一个基础评估结果
        if eval_results is None:
            eval_results = run_graded_evaluation(search_service, kp_ids, args.top_k)

        print(f"\n[4/4] 生成报告...")
        generate_report(eval_results, ablation_results, args.output, args.pilot)
        print(f"[OK] 报告已保存: {args.output}")
        print(f"[OK] JSON 已保存: {args.output.replace('.md', '.json')}")

        # 保存到数据库
        save_to_database(eval_results, ablation_results, args.pilot)

    # 总结
    print("\n" + "=" * 80)
    print("[SUCCESS] 评估完成！")
    print("=" * 80)

    if eval_results:
        print(f"\n[核心指标]")
        print(f"  Binary Precision: {eval_results['binary_precision']:.1%} (相关结果比例)")
        print(f"  Graded Precision: {eval_results['graded_precision']:.1%}")
        print(f"  Average nDCG@10: {eval_results['avg_ndcg']:.3f}")
        print(f"  不相关比例: {eval_results['G0']/eval_results['total_snippets']*100:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
