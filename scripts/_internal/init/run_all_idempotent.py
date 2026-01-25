#!/usr/bin/env python
"""
完整数据初始化脚本 - 增强版（幂等）

功能：
1. 初始化数据库schema
2. 加载知识点数据（幂等）
3. 分析并加载代码片段（幂等）
4. 可选：导入CodeSearchNet数据集

用法：
    python scripts/init_data/run_all_idempotent.py                    # 基础初始化
    python scripts/init_data/run_all_idempotent.py --with-codesearchnet  # 包含CodeSearchNet
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def run_step(step_name, script_path, *args, check=True):
    """运行初始化步骤"""
    print(f"\n{'='*70}")
    print(f"[{step_name}]")
    print(f"{'='*70}")

    cmd = [sys.executable, str(script_path)] + list(args)
    result = subprocess.run(cmd, cwd=str(project_root), encoding='utf-8',
                          capture_output=False, check=False)

    if check and result.returncode != 0:
        print(f"\n[ERROR] {step_name} failed with code {result.returncode}")
        return False

    print(f"[OK] {step_name} completed")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="完整数据初始化（幂等）")
    parser.add_argument("--with-codesearchnet", action="store_true",
                        help="导入CodeSearchNet数据集（耗时较长）")
    parser.add_argument("--skip-sample-code", action="store_true",
                        help="跳过sample_code.java分析")

    args = parser.parse_args()

    print("=" * 70)
    print("[*] Java知识点匹配系统 - 完整数据初始化（幂等）")
    print("=" * 70)
    print(f"项目根目录: {project_root}")
    print(f"导入CodeSearchNet: {'是' if args.with_codesearchnet else '否'}")
    print("=" * 70)

    scripts_dir = project_root / "scripts" / "init_data"

    # Step 1: 初始化数据库schema
    if not run_step("Step 1/5: 初始化数据库schema",
                    scripts_dir / "init_schema.py"):
        return 1

    # Step 2: 加载知识点数据（幂等：REPLACE INTO）
    if not run_step("Step 2/5: 加载知识点数据",
                    scripts_dir / "load_knowledge_points.py"):
        return 1

    # Step 3: 分析sample_code.java（可选，幂等：content_hash）
    if not args.skip_sample_code:
        if not run_step("Step 3/5: 分析sample_code.java",
                        scripts_dir / "analyze_sample_code.py"):
            print("[WARN] sample_code.java分析失败，继续...")
    else:
        print("\n[Step 3/5] 跳过sample_code.java分析")

    # Step 4: 导入CodeSearchNet（可选，智能幂等）
    if args.with_codesearchnet:
        # 先检查数据是否完整
        try:
            import sys
            sys.path.insert(0, str(project_root))
            from lib.client.db import MySQLClient
            from config import DB_NAME

            client = MySQLClient(DB_NAME)
            with client as conn:
                cursor = conn._conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM code_snippets s
                    JOIN code_files f ON s.file_id = f.id
                    WHERE f.source = 'codesearchnet'
                """)
                existing_count = cursor.fetchone()[0]

            # 检查processed文件的样本数
            processed_file = project_root / "experiments" / "datasets" / "processed" / "codesearchnet" / "java_train_processed.jsonl"
            if processed_file.exists():
                with open(processed_file, 'r', encoding='utf-8') as f:
                    expected_count = sum(1 for _ in f)

                print(f"\n[检查] CodeSearchNet数据: 已导入 {existing_count}/{expected_count}")

                if existing_count >= expected_count * 0.95:  # 允许5%误差
                    print("[跳过] CodeSearchNet数据已完整，跳过导入")
                    # 跳过Step 4
                else:
                    print(f"[WARN] 数据不完整，将清空并重新导入")
                    codesearchnet_script = project_root / "experiments" / "import_codesearchnet_to_db.py"
                    if not run_step("Step 4/5: 导入CodeSearchNet数据集",
                                    codesearchnet_script,
                                    "--clear-existing",
                                    check=False):
                        print("[WARN] CodeSearchNet导入可能不完整")
            else:
                print("[WARN] 找不到processed文件，将尝试导入")
                codesearchnet_script = project_root / "experiments" / "import_codesearchnet_to_db.py"
                if not run_step("Step 4/5: 导入CodeSearchNet数据集",
                                codesearchnet_script,
                                check=False):
                    print("[WARN] CodeSearchNet导入可能不完整")

        except Exception as e:
            print(f"[WARN] 检查CodeSearchNet数据时出错: {e}，将尝试导入")
            codesearchnet_script = project_root / "experiments" / "import_codesearchnet_to_db.py"
            if not run_step("Step 4/5: 导入CodeSearchNet数据集",
                            codesearchnet_script,
                            check=False):
                print("[WARN] CodeSearchNet导入可能不完整")
    else:
        print("\n[Step 4/5] 跳过CodeSearchNet导入（使用 --with-codesearchnet 启用）")

    # Step 5: 验证数据状态
    if not run_step("Step 5/5: 验证数据状态",
                    scripts_dir / "check_status.py", check=False):
        print("[WARN] 数据验证显示异常")

    # 完成
    print("\n" + "=" * 70)
    print("[SUCCESS] 数据初始化完成！")
    print("=" * 70)
    print("\n下一步：")
    print("  1. 启动API服务：python run_api.py")
    print("  2. 运行评估实验：python scripts/run_evaluation.py")
    print("  3. 检查数据状态：python scripts/init_data/check_status.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
