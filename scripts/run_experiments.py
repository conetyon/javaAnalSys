#!/usr/bin/env python
"""
实验主入口脚本 - 一键运行分级评估实验

功能：
1. 检查数据库连接
2. 自动初始化数据（如果需要）
3. 运行分级评估实验
4. 生成报告

用法：
    python scripts/run_experiments.py              # 完整实验（32 KP + 消融）
    python scripts/run_experiments.py --quick      # 快速评估（跳过消融实验）
    python scripts/run_experiments.py --pilot      # 仅评估 Pilot KP（5个）
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.globals import core_logger as log


def check_database_connection():
    """检查数据库连接和基础状态"""
    print("\n[1/4] 检查数据库连接...")
    try:
        from lib.client.db import MySQLClient
        from config import DB_NAME
        import mysql.connector
        from lib.globals import Cfg

        # 首先检查数据库本身是否存在
        db_cfg = Cfg.db.get(DB_NAME)
        try:
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
                return True
            else:
                print(f"[OK] 数据库 '{db_cfg.db}' 已存在")

        except Exception as e:
            print(f"[ERROR] MySQL连接失败: {e}")
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
            error_msg = str(e)
            if "doesn't exist" in error_msg or "1146" in error_msg:
                print(f"[INFO] 数据表未初始化，将自动创建")
                return True
            else:
                print(f"[WARN] 检查表状态时出错: {e}")
                return True

    except Exception as e:
        print(f"[ERROR] 数据库检查失败: {e}")
        return False


def initialize_data_if_needed():
    """如果数据不足，初始化数据"""
    print("\n[2/4] 检查数据完整性...")

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

        # 检查CodeSearchNet数据
        print("  正在检查CodeSearchNet数据...")
        codesearchnet_count = 0
        try:
            with client as conn:
                cursor = conn._conn.cursor()
                cursor.execute("SHOW COLUMNS FROM code_files LIKE 'source'")
                has_source = cursor.fetchone() is not None

                if has_source:
                    cursor.execute("""
                        SELECT COUNT(*) FROM code_snippets s
                        JOIN code_files f ON s.file_id = f.id
                        WHERE f.source = 'codesearchnet'
                    """)
                    codesearchnet_count = cursor.fetchone()[0]

                cursor.close()
        except Exception as e:
            error_msg = str(e)
            if "doesn't exist" in error_msg or "1146" in error_msg:
                print(f"  code_snippets表不存在，需要初始化")

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
                return False

            print("\n[OK] 数据初始化完成")
            return True
        else:
            print("[OK] 数据完整")
            return True

    except Exception as e:
        print(f"\n[ERROR] 数据检查失败: {e}")
        log.error(f"数据检查失败: {e}", exc_info=True)
        return False


def run_evaluation(quick_mode=False, pilot_mode=False):
    """运行分级评估实验"""
    print("\n[3/4] 运行分级评估实验...")

    eval_script = project_root / "scripts" / "_internal" / "run_evaluation.py"
    cmd = [sys.executable, str(eval_script)]

    if quick_mode:
        cmd.append("--quick")
        print("  模式: 快速评估（跳过消融实验）")
    else:
        print("  模式: 完整评估（包含消融实验）")

    if pilot_mode:
        cmd.append("--pilot")
        print("  范围: Pilot (5 KP)")
    else:
        print("  范围: Full (32 KP)")

    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode != 0:
        print("[ERROR] 评估实验失败")
        return False

    return True


def show_summary():
    """显示结果摘要"""
    print("\n[4/4] 实验完成摘要")
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

            if 'evaluation' in data:
                eval_data = data['evaluation']
                binary_prec = eval_data.get('binary_precision', 0)
                graded_prec = eval_data.get('graded_precision', 0)
                avg_ndcg = eval_data.get('avg_ndcg', 0)
                g0_ratio = eval_data.get('G0', 0) / eval_data.get('total_snippets', 1)

                print(f"\n[核心指标]")
                print(f"  Binary Precision: {binary_prec:.1%} (相关结果比例)")
                print(f"  Graded Precision: {graded_prec:.1%}")
                print(f"  Average nDCG@10: {avg_ndcg:.3f}")
                print(f"  不相关比例: {g0_ratio:.1%}")

    print("\n" + "=" * 70)
    print("\n[提示]")
    print("  - 查看完整报告: cat experiments/results/report.md")
    print("  - 重新运行: python scripts/run_experiments.py")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Java知识点匹配系统 - 分级评估实验")
    parser.add_argument("--quick", action="store_true", help="快速评估（跳过消融实验）")
    parser.add_argument("--pilot", action="store_true", help="仅评估 Pilot KP（5个）")
    args = parser.parse_args()

    print("=" * 70)
    print("[*] Java知识点匹配系统 - 分级评估实验")
    print("=" * 70)

    # Step 1: 检查数据库连接
    if not check_database_connection():
        return 1

    # Step 2: 初始化数据（如果需要）
    if not initialize_data_if_needed():
        return 1

    # Step 3: 运行评估
    if not run_evaluation(quick_mode=args.quick, pilot_mode=args.pilot):
        return 1

    # Step 4: 显示摘要
    show_summary()

    print("\n[SUCCESS] 实验流程完成！\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
