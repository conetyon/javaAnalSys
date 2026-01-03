# main.py
"""
离线任务入口
用于执行数据库初始化、代码分析、匹配测试等离线操作

用法:
    python main.py                    # 运行完整流程
    python main.py --init-db          # 仅初始化数据库
    python main.py --analyze FILE     # 分析指定文件
    python main.py --match KP_IDS     # 运行匹配测试
"""
import argparse
import sys
import traceback

from scripts.offline_tasks import (
    init_database,
    analyze_code_file,
    run_matching_test,
    run_full_pipeline,
    print_knowledge_tree,
)

# 默认配置
DEFAULT_SAMPLE_FILE = "./sample_code.java"
DEFAULT_KP_IDS = [10001]        # 例如 print 相关知识点 10010, 10011, 10031, 10034, 10083
DEFAULT_TARGET_DIFFICULTY = 0.6
DEFAULT_TOP_K = 5


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Java 知识点匹配系统 - 离线任务工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                           # 运行完整流程（初始化 + 分析 + 匹配）
  python main.py --init-db                 # 仅初始化数据库
  python main.py --analyze sample.java     # 分析指定 Java 文件
  python main.py --match 10011,10012       # 对指定知识点运行匹配测试
  python main.py --tree                    # 打印知识点树结构
        """
    )

    parser.add_argument(
        "--init-db",
        action="store_true",
        help="仅初始化数据库（创建表结构和预置数据）"
    )

    parser.add_argument(
        "--analyze",
        type=str,
        metavar="FILE",
        help="分析指定的 Java 文件"
    )

    parser.add_argument(
        "--match",
        type=str,
        metavar="KP_IDS",
        help="对指定知识点运行匹配测试（逗号分隔，如: 10011,10012）"
    )

    parser.add_argument(
        "--tree",
        action="store_true",
        help="打印知识点树结构"
    )

    parser.add_argument(
        "--sample",
        type=str,
        default=DEFAULT_SAMPLE_FILE,
        metavar="FILE",
        help=f"样本代码文件路径（默认: {DEFAULT_SAMPLE_FILE}）"
    )

    parser.add_argument(
        "--difficulty",
        type=float,
        default=DEFAULT_TARGET_DIFFICULTY,
        metavar="FLOAT",
        help=f"目标难度 0-1（默认: {DEFAULT_TARGET_DIFFICULTY}）"
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        metavar="INT",
        help=f"返回结果数量（默认: {DEFAULT_TOP_K}）"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    try:
        # 仅初始化数据库
        if args.init_db:
            print("\n=== 初始化数据库 ===")
            success = init_database()
            if success:
                print("[SUCCESS] 数据库初始化完成")
            else:
                print("[FAILED] 数据库初始化失败")
                sys.exit(1)
            return

        # 打印知识点树
        if args.tree:
            print("\n=== 知识点树结构 ===")
            print_knowledge_tree()
            return

        # 分析指定文件
        if args.analyze:
            print(f"\n=== 分析文件: {args.analyze} ===")
            snippets = analyze_code_file(args.analyze)
            print(f"[SUCCESS] 检测到 {len(snippets)} 个代码片段")
            return

        # 运行匹配测试
        if args.match:
            kp_ids = [int(x.strip()) for x in args.match.split(",")]
            print(f"\n=== 匹配测试: {kp_ids} ===")
            results = run_matching_test(
                kp_ids=kp_ids,
                target_difficulty=args.difficulty,
                top_k=args.top_k
            )
            # 打印结果摘要
            for kp_id, matches in results.items():
                print(f"\n知识点 {kp_id}: {len(matches)} 条匹配结果")
                for i, m in enumerate(matches, 1):
                    print(f"  [{i}] score={m.get('score')}, ast={m.get('ast_ratio')}, kw={m.get('keyword_score')}")
            return

        # 默认：运行完整流程
        print("\n" + "=" * 60)
        print("Java 知识点匹配系统 - 离线任务")
        print("=" * 60)

        # 解析知识点 ID
        kp_ids = DEFAULT_KP_IDS

        run_full_pipeline(
            sample_file=args.sample,
            kp_ids=kp_ids,
            target_difficulty=args.difficulty,
            top_k=args.top_k
        )

    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        sys.exit(0)
    except Exception as e:
        traceback.print_exc()
        print(f"\n[CRITICAL ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
