#!/usr/bin/env python
# run_api.py
"""
API 服务启动入口

用法:
    python run_api.py                    # 启动 API 服务（默认端口 5000）
    python run_api.py --port 8080        # 指定端口
    python run_api.py --host 0.0.0.0     # 指定主机
    python run_api.py --debug            # 开启调试模式
"""
import argparse
import sys

from api import create_app
from lib.globals import api_logger as log


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Java 知识点匹配系统 - API 服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_api.py                      # 启动服务（默认 http://127.0.0.1:5000）
  python run_api.py --port 8080          # 使用端口 8080
  python run_api.py --host 0.0.0.0       # 允许外部访问
  python run_api.py --debug              # 开启调试模式（热重载）
        """
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务监听地址（默认: 0.0.0.0）"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="服务监听端口（默认: 5000）"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启调试模式（热重载、详细错误信息）"
    )

    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="禁用自动重载（仅在 debug 模式下有效）"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    print("\n" + "=" * 60)
    print("Java 知识点匹配系统 - API 服务")
    print("=" * 60)

    # 创建 Flask 应用
    app = create_app()

    # 打印启动信息
    print(f"\n服务地址: http://{args.host}:{args.port}")
    print(f"调试模式: {'开启' if args.debug else '关闭'}")
    print("\n可用接口:")
    print("  GET  /                          - 服务信息")
    print("  GET  /health                    - 健康检查")
    print("  GET  /api/knowledge/tree        - 获取知识点树")
    print("  GET  /api/knowledge/list        - 获取知识点列表")
    print("  GET  /api/knowledge/{id}        - 获取知识点详情")
    print("  GET  /api/knowledge/{id}/children - 获取子节点")
    print("  POST /api/match                 - 知识点匹配")
    print("  POST /api/match/batch           - 批量匹配")
    print("  GET  /api/match/health          - 匹配服务健康检查")
    print("\n" + "-" * 60)

    log.info(f"Starting API server on {args.host}:{args.port}")

    try:
        # 启动服务
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=args.debug and not args.no_reload
        )
    except KeyboardInterrupt:
        print("\n[INFO] 服务已停止")
        sys.exit(0)
    except Exception as e:
        log.error(f"服务启动失败: {e}", exc_info=True)
        print(f"\n[ERROR] 服务启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
