#!/usr/bin/env python
"""
实验主入口脚本 - 一键运行完整实验流程

功能：
1. 检查数据库连接
2. 自动初始化数据（如果需要）
3. 生成测试标注（如果不存在）
4. 运行评估实验
5. 生成报告

用法：
    python scripts/run_experiments.py              # 完整实验
    python scripts/run_experiments.py --quick      # 快速评估（跳过基线和消融）
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.globals import core_logger as log


def check_database_connection():
    """检查数据库连接和基础状态"""
    print("\n[1/5] 检查数据库连接...")
    try:
        from lib.client.db import MySQLClient
        from config import DB_NAME
        import mysql.connector
        from lib.globals import Cfg

        # 首先检查数据库本身是否存在
        db_cfg = Cfg.db.get(DB_NAME)
        try:
            # 连接 MySQL Server（不指定数据库）
            conn = mysql.connector.connect(
                host=db_cfg.host,
                port=db_cfg.port,
                user=db_cfg.user,
                password=db_cfg.password
            )
            cursor = conn.cursor()
            cursor.execute(f"SHOW DATABASES LIKE '{db_cfg.db}'")
            db_exists = cursor.fetchone() is not None
            cursor.close()
            conn.close()

            if not db_exists:
                print(f"[INFO] 数据库 '{db_cfg.db}' 不存在，将自动创建")
                return True  # 继续执行，让初始化流程创建数据库
            else:
                print(f"[OK] 数据库 '{db_cfg.db}' 已存在")

        except Exception as e:
            print(f"[ERROR] MySQL连接失败: {e}")
            print("\n请检查:")
            print("  1. MySQL服务是否启动")
            print("  2. config/db.yaml 配置是否正确")
            print(f"  3. MySQL用户 '{db_cfg.user}' 权限是否正确")
            return False

        # 检查表是否存在
        try:
            client = MySQLClient(DB_NAME)
            with client as conn:
                cursor = conn._conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM knowledge_points")
                kp_count = cursor.fetchone()[0]
                cursor.close()

            print(f"[OK] 数据已初始化 (知识点数: {kp_count})")
            return True

        except Exception as e:
            # 表不存在是正常的，继续初始化流程
            error_msg = str(e)
            if "doesn't exist" in error_msg or "1146" in error_msg:
                print(f"[INFO] 数据表未初始化，将自动创建")
                return True
            else:
                # 其他错误则报告
                print(f"[WARN] 检查表状态时出错: {e}")
                return True  # 继续执行，让初始化流程处理

    except Exception as e:
        print(f"[ERROR] 数据库检查失败: {e}")
        print("\n请检查:")
        print("  1. MySQL服务是否启动")
        print("  2. config/db.yaml 配置是否正确")
        return False


def initialize_data_if_needed():
    """
    如果数据不足，初始化数据

    Returns:
        tuple: (success: bool, data_was_initialized: bool)
    """
    print("\n[2/5] 检查数据完整性...")

    try:
        from lib.client.db import MySQLClient
        from config import DB_NAME

        client = MySQLClient(DB_NAME)

        # 检查知识点数量
        kp_count = 0
        try:
            print("  正在查询知识点数量...")
            with client as conn:
                cursor = conn._conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM knowledge_points")
                kp_count = cursor.fetchone()[0]
                cursor.close()
            print(f"  知识点: {kp_count}")
        except Exception as e:
            error_msg = str(e)
            if "doesn't exist" in error_msg or "1146" in error_msg:
                print(f"  知识点表不存在，需要初始化")
            else:
                print(f"  [WARN] 查询知识点数量时出错: {e}")

        # 检查CodeSearchNet数据
        print("  正在检查CodeSearchNet数据...")
        codesearchnet_count = 0
        try:
            with client as conn:
                cursor = conn._conn.cursor()

                # 先检查source字段是否存在
                cursor.execute("SHOW COLUMNS FROM code_files LIKE 'source'")
                has_source = cursor.fetchone() is not None

                if has_source:
                    cursor.execute("""
                        SELECT COUNT(*) FROM code_snippets s
                        JOIN code_files f ON s.file_id = f.id
                        WHERE f.source = 'codesearchnet'
                    """)
                    codesearchnet_count = cursor.fetchone()[0]
                else:
                    print("  [INFO] schema需要更新（将在初始化时自动处理）")

                cursor.close()
        except Exception as e:
            error_msg = str(e)
            if "doesn't exist" in error_msg or "1146" in error_msg:
                print(f"  code_snippets表不存在，需要初始化")
            else:
                print(f"  [WARN] 检查CodeSearchNet数据时出错: {e}")

        print(f"  CodeSearchNet数据: {codesearchnet_count} 片段")

        # 检查是否需要初始化
        needs_init = kp_count < 100 or codesearchnet_count == 0

        if needs_init:
            print("\n[WARN] 数据不完整，开始初始化...")
            print("  这可能需要5-10分钟，请稍候...\n")

            setup_script = project_root / "scripts" / "setup_database.py"
            result = subprocess.run(
                [sys.executable, str(setup_script), "--all"],
                cwd=str(project_root)
            )

            if result.returncode != 0:
                print("[ERROR] 数据初始化失败")
                return False, False

            print("\n[OK] 数据初始化完成")
            return True, True  # 返回成功，并标记数据已初始化
        else:
            print("[OK] 数据完整")
            return True, False  # 返回成功，数据未初始化

    except Exception as e:
        print(f"\n[ERROR] 数据检查失败: {e}")
        log.error(f"数据检查失败: {e}", exc_info=True)
        return False, False


def ensure_ground_truth(force_regenerate=False):
    """
    确保ground truth文件存在且有效

    Args:
        force_regenerate: 是否强制重新生成（当数据刚初始化时应设为True）
    """
    print("\n[3/5] 检查测试标注...")

    ground_truth_path = project_root / "experiments" / "datasets" / "ground_truth" / "codesearchnet_v7.0-final.json"

    # 如果不强制重新生成且文件存在，先验证一下
    if not force_regenerate and ground_truth_path.exists():
        print(f"[INFO] 测试标注已存在，验证snippet ID...")

    init_exp_script = project_root / "scripts" / "_internal" / "init" / "init_experiment_data.py"
    cmd = [sys.executable, str(init_exp_script)]

    # 如果强制重新生成，先删除旧文件
    if force_regenerate and ground_truth_path.exists():
        print("[INFO] 数据已重新初始化，删除旧标注并重新生成...")
        ground_truth_path.unlink()

    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode != 0:
        print("[ERROR] 测试标注生成/验证失败")
        return False

    print("[OK] 测试标注已就绪")
    return True


def run_evaluation(quick_mode=False):
    """运行评估实验"""
    print("\n[4/5] 运行评估实验...")

    eval_script = project_root / "scripts" / "_internal" / "run_evaluation.py"
    cmd = [sys.executable, str(eval_script)]

    if quick_mode:
        cmd.append("--quick")
        print("  模式: 快速评估（跳过基线和消融）")
    else:
        print("  模式: 完整评估（包含基线对比和消融实验）")

    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode != 0:
        print("[ERROR] 评估实验失败")
        return False

    return True


def show_summary():
    """显示结果摘要"""
    print("\n[5/5] 实验完成摘要")
    print("=" * 70)

    report_path = project_root / "experiments" / "results" / "report.md"
    json_path = project_root / "experiments" / "results" / "report.json"

    if report_path.exists():
        print(f"[OK] 评估报告: {report_path}")

        # 读取并显示核心指标
        import json
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'single_evaluation' in data:
                top1 = data['single_evaluation'].get('top1_accuracy', 0)
                mrr = data['single_evaluation'].get('mrr', 0)
                print(f"\n[核心指标]")
                print(f"  Top-1 Accuracy: {top1:.2%}")
                print(f"  MRR: {mrr:.4f}")

                target = 0.95
                if top1 >= target:
                    print(f"  状态: [OK] 达标 (目标: ≥{target:.0%})")
                else:
                    print(f"  状态: [WARN] 未达标 (目标: ≥{target:.0%})")

    print("\n" + "=" * 70)
    print("\n[提示]")
    print("  - 查看完整报告: cat experiments/results/report.md")
    print("  - 查看数据状态: python scripts/init_data/check_status.py")
    print("  - 重新运行: python scripts/run_experiments.py")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Java知识点匹配系统 - 完整实验流程")
    parser.add_argument("--quick", action="store_true", help="快速评估（跳过基线和消融）")
    args = parser.parse_args()

    print("=" * 70)
    print("[*] Java知识点匹配系统 - 实验流程")
    print("=" * 70)

    # Step 1: 检查数据库连接
    if not check_database_connection():
        return 1

    # Step 2: 初始化数据（如果需要）
    success, data_was_initialized = initialize_data_if_needed()
    if not success:
        return 1

    # Step 3: 确保ground truth存在（如果数据刚初始化，则强制重新生成）
    if not ensure_ground_truth(force_regenerate=data_was_initialized):
        return 1

    # Step 4: 运行评估
    if not run_evaluation(quick_mode=args.quick):
        return 1

    # Step 5: 显示摘要
    show_summary()

    print("\n[SUCCESS] 实验流程完成！\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
