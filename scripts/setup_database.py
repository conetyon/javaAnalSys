#!/usr/bin/env python
"""
数据库设置 - 统一入口脚本

功能：
1. 初始化数据库表结构
2. 加载知识点数据
3. 导入数据集（CodeSearchNet）
4. 导入用户代码项目
5. 完整初始化流程

用法：
    python scripts/setup_database.py --init-schema        # 仅初始化表结构
    python scripts/setup_database.py --load-kp            # 仅加载知识点
    python scripts/setup_database.py --import-dataset     # 仅导入数据集
    python scripts/setup_database.py --import-project <path>  # 导入指定项目
    python scripts/setup_database.py --all                # 完整初始化（推荐）
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.globals import core_logger as log


def init_schema():
    """初始化数据库表结构（含管理员账号）"""
    print("\n" + "=" * 70)
    print("[1] 初始化数据库表结构")
    print("=" * 70)

    try:
        from src.db_manager.database import DatabaseInitializer
        from config import DB_NAME

        db_init = DatabaseInitializer(db_name=DB_NAME)
        db_init.init_db()

        print("[OK] 数据库表结构初始化完成")

        # 自动创建管理员账号
        create_admin_user()

        return True
    except Exception as e:
        print(f"[ERROR] 表结构初始化失败: {e}")
        log.error(f"表结构初始化失败", exc_info=True)
        return False


def load_knowledge_points():
    """加载知识点数据"""
    print("\n" + "=" * 70)
    print("[2] 加载知识点数据")
    print("=" * 70)

    try:
        from src.db_manager import KnowledgePointManager
        from config import DB_NAME

        kp_manager = KnowledgePointManager(db_name=DB_NAME)

        # 检查是否已有数据
        existing = kp_manager.get_tree_structure()
        if existing:
            print(f"[INFO] 数据库中已有 {len(existing)} 个知识点")
            user_input = input("是否重新加载？（会清空现有数据）[y/N]: ")
            if user_input.lower() != 'y':
                print("[SKIP] 保留现有知识点数据")
                return True

        # 执行导入
        kp_dml_path = project_root / "kp_dml.sql"
        if not kp_dml_path.exists():
            print(f"[ERROR] 找不到知识点数据文件: {kp_dml_path}")
            return False

        print(f"[INFO] 从 {kp_dml_path.name} 导入知识点...")

        # 读取SQL文件并执行
        from lib.client.db import MySQLClient
        client = MySQLClient(db=DB_NAME)

        with open(kp_dml_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 分割并执行SQL语句
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        for stmt in statements:
            if stmt:
                client.execute(stmt)

        # 验证
        kps = kp_manager.get_tree_structure()
        print(f"[OK] 成功加载 {len(kps)} 个知识点")
        return True

    except Exception as e:
        print(f"[ERROR] 知识点加载失败: {e}")
        log.error(f"知识点加载失败", exc_info=True)
        return False


def import_dataset():
    """导入CodeSearchNet数据集"""
    print("\n" + "=" * 70)
    print("[3] 导入CodeSearchNet数据集")
    print("=" * 70)

    try:
        # 导入内部实现
        from scripts._internal.import_utils.import_codesearchnet_to_db import import_codesearchnet_to_db
        from lib.client.db import MySQLClient
        from config import DB_NAME

        print("[INFO] 检查现有数据...")

        # 检查数据完整性
        client = MySQLClient(db=DB_NAME)
        result = client.fetch_one("""
            SELECT COUNT(*) as count FROM code_snippets s
            JOIN code_files f ON s.file_id = f.id
            WHERE f.source = 'codesearchnet'
        """)
        existing_count = result['count'] if result else 0

        # 期望的数据量（CodeSearchNet Java 子集）
        expected_count = 20022

        if existing_count > 0:
            completion_rate = (existing_count / expected_count) * 100
            print(f"[INFO] 数据库中已有 {existing_count} 条 CodeSearchNet 数据")
            print(f"[INFO] 完整度: {completion_rate:.1f}% (期望 {expected_count} 条)")

            if existing_count >= expected_count * 0.95:  # 95% 以上认为完整
                print("[OK] 数据已完整，跳过导入")
                return True
            else:
                print("[WARN] 数据不完整，需要清除并重新导入")
                user_input = input("是否清除现有数据并重新导入？[Y/n]: ")
                if user_input.lower() in ['', 'y', 'yes']:
                    print("[INFO] 清除现有 CodeSearchNet 数据...")
                    client.execute("""
                        DELETE s FROM code_snippets s
                        JOIN code_files f ON s.file_id = f.id
                        WHERE f.source = 'codesearchnet'
                    """)
                    client.execute("""
                        DELETE FROM code_files
                        WHERE source = 'codesearchnet'
                    """)
                    print("[OK] 已清除现有数据")
                else:
                    print("[SKIP] 保留现有数据")
                    return True

        # 设置处理文件路径
        processed_file = project_root / 'experiments' / 'datasets' / 'processed' / 'codesearchnet' / 'java_train_processed.jsonl'

        if not processed_file.exists():
            print(f"[ERROR] 找不到处理后的数据集文件: {processed_file}")
            print("[INFO] 请先运行预处理脚本:")
            print("       python experiments/datasets/preprocess_codesearchnet.py")
            return False

        print("[INFO] 开始导入 CodeSearchNet 数据集...")
        print(f"[INFO] 这可能需要 5-10 分钟，请耐心等待...")

        # 调用导入函数（skip_if_exists=False，因为我们已经检查过了）
        import_codesearchnet_to_db(
            processed_file=processed_file,
            max_samples=None,  # 导入全部
            clear_existing=False,  # 已经手动清理过了
            skip_if_exists=False  # 不跳过，强制导入
        )

        print("[OK] 数据集导入完成")
        return True

    except Exception as e:
        print(f"[ERROR] 数据集导入失败: {e}")
        log.error(f"数据集导入失败", exc_info=True)
        return False


def import_project(project_path: str):
    """导入用户代码项目"""
    print("\n" + "=" * 70)
    print(f"[4] 导入用户项目: {project_path}")
    print("=" * 70)

    try:
        project_path_obj = Path(project_path)
        if not project_path_obj.exists():
            print(f"[ERROR] 项目路径不存在: {project_path}")
            return False

        # 确保数据库表存在（幂等）
        print("[INFO] 检查数据库表结构...")
        from src.db_manager.database import DatabaseInitializer
        from config import DB_NAME
        db_init = DatabaseInitializer(db_name=DB_NAME)
        db_init.init_db()
        print("[OK] 数据库表结构已就绪")

        # 导入内部实现
        from scripts._internal.import_utils.import_code_repos import import_repository

        print(f"[INFO] 扫描项目: {project_path}")
        progress = import_repository(str(project_path_obj))

        if progress.total_files == 0:
            print(f"[WARN] 未发现任何 Java 文件")
            return True

        # 显示统计信息
        if progress.unique_snippets > 0:
            dup_info = f" ({progress.duplicate_snippets} 内容重复跳过)" if progress.duplicate_snippets > 0 else ""
            file_info = f"{progress.files_with_methods} 文件"
            if progress.files_all_duplicates > 0:
                file_info += f" ({progress.files_all_duplicates} 全重复跳过)"
            print(f"[OK] 导入完成: {file_info}, {progress.unique_snippets} 新片段{dup_info}")
        else:
            # 全部已存在时，显示扫描数量
            print(f"[OK] 导入完成: 扫描 {progress.total_snippets} 个片段, 全部内容已存在于数据库")
        return progress.failed_files == 0

    except Exception as e:
        print(f"[ERROR] 项目导入失败: {e}")
        log.error(f"项目导入失败", exc_info=True)
        return False


def import_all_projects(repos_dir: str = "code_repos"):
    """一键导入所有代码项目（支持单个文件或目录）"""
    print("\n" + "=" * 70)
    print(f"[4] 一键导入所有项目: {repos_dir}")
    print("=" * 70)

    try:
        repos_path = Path(repos_dir)
        if not repos_path.exists():
            print(f"[ERROR] 路径不存在: {repos_dir}")
            return False

        # 确保数据库表存在（幂等）
        print("[INFO] 检查数据库表结构...")
        from src.db_manager.database import DatabaseInitializer
        from config import DB_NAME
        db_init = DatabaseInitializer(db_name=DB_NAME)
        db_init.init_db()
        print("[OK] 数据库表结构已就绪")

        # 判断是单个文件还是目录
        if repos_path.is_file():
            if not repos_path.suffix == '.java':
                print(f"[ERROR] 不是 Java 文件: {repos_dir}")
                return False

            print(f"[INFO] 导入单个文件: {repos_path.name}")

            # 使用 import_repository 导入单个文件所在目录（flat 模式）
            from scripts._internal.import_utils.import_code_repos import import_java_file, ImportProgress
            from src.java_analyzer.analyzer import JavaAnalyzer
            from lib.client.db import MySQLClient

            analyzer = JavaAnalyzer()
            client = MySQLClient(db=DB_NAME)
            progress = ImportProgress()
            progress.total_files = 1

            import_java_file(str(repos_path), analyzer, client, progress, show_progress=True)

            # 显示统计信息
            if progress.unique_snippets > 0:
                print(f"[OK] 导入完成: 1 文件, {progress.unique_snippets} 新片段")
            elif progress.files_all_duplicates > 0:
                print(f"[OK] 导入完成: 文件内容已全部存在于数据库")
            elif progress.files_no_methods > 0:
                print(f"[OK] 导入完成: 文件无可提取的方法")
            else:
                print(f"[OK] 导入完成: 扫描 {progress.total_snippets} 个片段, 全部内容已存在于数据库")
            return progress.failed_files == 0

        # 目录模式：走原有逻辑
        # 导入内部实现
        from scripts._internal.import_utils.import_code_repos import import_all_repositories

        print(f"[INFO] 扫描目录: {repos_dir}")
        print("[INFO] 递归发现所有 .java 文件（自动跳过 target/build/.git 等目录）")

        progress = import_all_repositories(str(repos_path))

        if progress.total_files == 0:
            print(f"[WARN] 未发现任何 Java 文件")
            return True  # 不算失败

        # 显示统计信息
        if progress.unique_snippets > 0:
            dup_info = f" ({progress.duplicate_snippets} 内容重复跳过)" if progress.duplicate_snippets > 0 else ""
            file_info = f"{progress.files_with_methods} 文件"
            if progress.files_all_duplicates > 0:
                file_info += f" ({progress.files_all_duplicates} 全重复跳过)"
            print(f"[OK] 导入完成: {file_info}, {progress.unique_snippets} 新片段{dup_info}")
        else:
            # 全部已存在时，显示扫描数量
            print(f"[OK] 导入完成: 扫描 {progress.total_snippets} 个片段, 全部内容已存在于数据库")
        return progress.failed_files == 0

    except Exception as e:
        print(f"[ERROR] 批量导入失败: {e}")
        log.error(f"批量导入失败", exc_info=True)
        return False


def analyze_sample_code():
    """分析示例代码（可选）"""
    print("\n" + "=" * 70)
    print("[*] 分析示例代码")
    print("=" * 70)

    try:
        sample_code = project_root / "sample_code.java"
        if not sample_code.exists():
            print("[SKIP] 示例代码文件不存在，跳过")
            return True

        from scripts._internal.init.analyze_sample_code import analyze_sample_code as analyze_func

        print(f"[INFO] 分析 {sample_code.name}...")
        success = analyze_func()

        if success:
            print("[OK] 示例代码分析完成")
        else:
            print("[WARN] 示例代码分析未完成")
        return True  # 非关键步骤，失败不影响整体

    except Exception as e:
        print(f"[WARN] 示例代码分析失败: {e}")
        return True  # 非关键步骤，失败不影响整体


def create_admin_user():
    """创建预置管理员账号（从 .env 读取凭证）"""
    print("\n" + "=" * 70)
    print("[*] 创建管理员账号")
    print("=" * 70)

    try:
        import os
        import bcrypt
        from dotenv import load_dotenv
        from lib.client.db import MySQLClient
        from config import DB_NAME

        load_dotenv()

        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD')

        if not password:
            print("[WARN] ADMIN_PASSWORD 未在 .env 中设置，跳过管理员创建")
            print("       请在 .env 文件中添加: ADMIN_PASSWORD=your-secure-password")
            return True  # 非关键步骤

        # Check if users table exists
        client = MySQLClient(db=DB_NAME)
        try:
            client.fetch_one("SELECT 1 FROM users LIMIT 1")
        except Exception:
            print("[SKIP] users 表不存在，跳过管理员创建")
            return True

        # Check if admin already exists
        existing = client.fetch_one(
            "SELECT id FROM users WHERE username = %s",
            (username,)
        )
        if existing:
            print(f"[OK] 管理员账号 '{username}' 已存在")
            return True

        # Create admin user
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        client.execute(
            """INSERT INTO users (username, password_hash, role)
               VALUES (%s, %s, 'admin')""",
            (username, password_hash)
        )

        print(f"[OK] 管理员账号 '{username}' 已创建")
        return True

    except Exception as e:
        print(f"[WARN] 管理员创建失败: {e}")
        return True  # 非关键步骤，失败不影响整体


def run_all():
    """完整初始化流程"""
    print("\n" + "=" * 80)
    print(" " * 25 + "数据库完整初始化")
    print("=" * 80)

    steps = [
        ("初始化表结构", init_schema),
        ("加载知识点", load_knowledge_points),
        ("导入数据集", import_dataset),
        ("分析示例代码", analyze_sample_code),
    ]

    for i, (name, func) in enumerate(steps, 1):
        print(f"\n[步骤 {i}/{len(steps)}] {name}")
        if not func():
            print(f"\n[ERROR] 初始化失败于步骤: {name}")
            return False

    print("\n" + "=" * 80)
    print(" " * 25 + "初始化完成！")
    print("=" * 80)
    print("\n后续操作：")
    print("  - 启动API: python run_api.py")
    print("  - 运行实验: python scripts/run_experiments.py")
    print("  - 导入项目: python scripts/setup_database.py --import-project <path>")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="数据库设置统一入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  完整初始化（推荐）:
    python scripts/setup_database.py --all

  分步初始化:
    python scripts/setup_database.py --init-schema
    python scripts/setup_database.py --load-kp
    python scripts/setup_database.py --import-dataset

  导入用户项目:
    python scripts/setup_database.py --import-project /path/to/project

  一键导入 code_repos 所有项目:
    python scripts/setup_database.py --import-all-projects
    python scripts/setup_database.py --import-all-projects --repos-dir ./my_repos
        """
    )

    parser.add_argument("--init-schema", action="store_true",
                       help="初始化数据库表结构")
    parser.add_argument("--load-kp", action="store_true",
                       help="加载知识点数据")
    parser.add_argument("--import-dataset", action="store_true",
                       help="导入CodeSearchNet数据集")
    parser.add_argument("--import-project", type=str, metavar="PATH",
                       help="导入指定的代码项目")
    parser.add_argument("--import-all-projects", action="store_true",
                       help="一键导入 code_repos 目录下所有项目")
    parser.add_argument("--repos-dir", type=str, default="code_repos",
                       help="指定项目根目录（默认: code_repos）")
    parser.add_argument("--all", action="store_true",
                       help="完整初始化（推荐）")

    args = parser.parse_args()

    # 如果没有任何操作参数，显示帮助（排除有默认值的参数）
    action_args = {k: v for k, v in vars(args).items() if k != 'repos_dir'}
    if not any(action_args.values()):
        parser.print_help()
        return 1

    success = True

    try:
        if args.all:
            success = run_all()
        else:
            if args.init_schema:
                success = success and init_schema()
            if args.load_kp:
                success = success and load_knowledge_points()
            if args.import_dataset:
                success = success and import_dataset()
            if args.import_project:
                success = success and import_project(args.import_project)
            if args.import_all_projects:
                success = success and import_all_projects(args.repos_dir)

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n[WARN] 用户中断")
        return 130
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}")
        log.error("数据库设置失败", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
