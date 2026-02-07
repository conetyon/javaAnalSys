#!/usr/bin/env python
# scripts/run_evaluation.py
"""
评估脚本 - 运行完整的评估实验并生成报告

用法：
    python scripts/run_evaluation.py                    # 运行完整评估（包括消融实验）
    python scripts/run_evaluation.py --quick            # 快速评估（仅评估混合策略）
    python scripts/run_evaluation.py --ablation-only    # 仅运行消融实验
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from experiments.evaluation.experiment import (
    load_ground_truth,
    run_single_evaluation,
    run_ablation_study,
    generate_experiment_report,
)
from src.services.search_service import SearchService
from src.db_manager import CodeLibraryManager, KnowledgePointManager
from lib.globals import core_logger as log


def main():
    # 使用基于项目根目录的绝对路径
    default_ground_truth = str(project_root / "experiments" / "datasets" / "ground_truth" / "codesearchnet_v7.0-final.json")
    default_output = str(project_root / "experiments" / "results" / "report.md")

    parser = argparse.ArgumentParser(description="运行 Java 知识点匹配系统评估实验")
    parser.add_argument("--quick", action="store_true", help="快速评估（仅评估混合策略）")
    parser.add_argument("--ablation-only", action="store_true", help="仅运行消融实验")
    parser.add_argument("--ground-truth", type=str, default=default_ground_truth,
                        help="标注数据集路径")
    parser.add_argument("--output", type=str, default=default_output,
                        help="输出报告路径")
    parser.add_argument("--top-k", type=int, default=10, help="评估的截断位置 K")

    args = parser.parse_args()

    print("=" * 80)
    print("[*] Java 知识点匹配系统 - 评估实验")
    print("=" * 80)
    print(f"标注数据: {args.ground_truth}")
    print(f"输出路径: {args.output}")
    print(f"截断位置: Top-{args.top_k}")
    print("=" * 80)

    # 1. 加载标注数据
    print("\n[1/3] 加载标注数据集...")
    try:
        test_cases = load_ground_truth(args.ground_truth)
        print(f"[OK] 成功加载 {len(test_cases)} 个测试用例")
    except Exception as e:
        print(f"[ERROR] 加载标注数据失败: {e}")
        return 1

    # 2. 初始化服务
    print("\n[2/3] 初始化搜索服务...")
    try:
        from config import DB_NAME
        search_service = SearchService(db_name=DB_NAME)
        code_manager = CodeLibraryManager(db_name=DB_NAME)
        kp_manager = KnowledgePointManager(db_name=DB_NAME)
        print("[OK] 搜索服务初始化成功")
    except Exception as e:
        print(f"[ERROR] 服务初始化失败: {e}")
        log.error("服务初始化失败", exc_info=True)
        return 1

    # 3. 运行评估实验
    print("\n[3/3] 运行评估实验...")
    all_results = {}

    try:
        # 3.1 混合策略评估（必须运行）
        if not args.ablation_only:
            print("\n[实验 1] 混合策略评估...")
            single_results = run_single_evaluation(search_service, test_cases, args.top_k)
            all_results["single_evaluation"] = single_results
            all_results["num_test_cases"] = len(test_cases)
            print(f"[OK] 混合策略评估完成 - Top-1 Accuracy: {single_results['top1_accuracy']:.2%}")

        # 3.2 消融实验（可选）
        if not args.quick:
            print("\n[实验 2] 消融实验...")
            ablation_results = run_ablation_study(search_service, test_cases, args.top_k)
            all_results["ablation_study"] = ablation_results
            print("[OK] 消融实验完成")

            # 打印消融表格
            print("\n" + "=" * 80)
            print("消融实验结果汇总：")
            print("-" * 80)
            print(f"{'配置':<30} {'Top-1 Acc':>12} {'P@10':>10} {'MRR':>10}")
            print("-" * 80)
            for res in ablation_results:
                print(f"{res['method']:<30} {res['top1_accuracy']:>11.2%} "
                      f"{res['precision@10']:>9.2%} {res['mrr']:>10.4f}")
            print("=" * 80)

    except Exception as e:
        print(f"[ERROR] 实验执行失败: {e}")
        log.error("实验执行失败", exc_info=True)
        return 1

    # 4. 生成实验报告
    print("\n[4/4] 生成实验报告...")
    try:
        report = generate_experiment_report(all_results, args.output)
        print(f"[OK] 报告已保存到: {args.output}")
        print(f"[OK] JSON 数据已保存到: {args.output.replace('.md', '.json')}")
    except Exception as e:
        print(f"[ERROR] 报告生成失败: {e}")
        log.error("报告生成失败", exc_info=True)
        return 1

    # 5. 总结
    print("\n" + "=" * 80)
    print("[SUCCESS] 评估实验完成！")
    print("=" * 80)

    if "single_evaluation" in all_results:
        top1 = all_results["single_evaluation"]["top1_accuracy"]
        target = 0.95
        status = "[OK] 达标" if top1 >= target else "[WARN] 未达标"
        print(f"\n[指标] 核心指标：Top-1 Accuracy = {top1:.2%} (目标: >={target:.0%}) {status}")

    print(f"\n[文件] 查看完整报告: {args.output}")
    print("\n提示: 使用论文绘图时，可以直接使用 JSON 数据文件")

    return 0


if __name__ == "__main__":
    sys.exit(main())
