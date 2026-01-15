#!/usr/bin/env python
"""
SAPAS 启动脚本
股票数据分析与处理自动化服务

用法:
    python run.py <command> [options]

命令:
    server   启动后端 API 服务器 (默认端口 8081)
    web      启动前端开发服务器 (默认端口 5173)
    dev      同时启动前端和后端 (推荐)
    help     显示帮助信息

数据同步说明:
    服务启动时会自动执行以下操作：
    - 检查并同步股票列表（如果为空）
    - 同步自选股的K线数据（如果有缺失）

    定时任务（服务运行期间自动执行）：
    - 盘后同步: 每个交易日 15:30 自动同步自选股数据
    - 股票列表更新: 每周一 9:00 自动更新
    - 盘中更新: 交易时段每 30 分钟检查更新

示例:
    python run.py server              # 启动后端
    python run.py web                 # 启动前端
    python run.py dev                 # 同时启动前后端（推荐）
    python run.py server --port 8080  # 指定端口
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent


def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print("   SAPAS - Stock Analysis Processing Automated Service")
    print("   股票数据分析与处理自动化服务")
    print("=" * 60)
    print()


def print_help():
    """打印帮助信息"""
    print(__doc__)
    print()
    print("选项:")
    print("  --host HOST    服务器地址 (默认: 0.0.0.0)")
    print("  --port PORT    服务器端口 (后端默认: 8081, 前端默认: 5173)")
    print("  --reload       启用热重载")
    print()
    print("环境要求:")
    print("  - Python 3.11+")
    print("  - Node.js 18+ (用于前端)")
    print("  - PostgreSQL 15+")
    print()


def start_server(host: str, port: int, reload: bool):
    """启动后端 API 服务器"""
    import uvicorn
    from src.config import settings

    print(f"🚀 启动后端服务器...")
    print(f"   地址: http://{host}:{port}")
    print(f"   API 文档: http://{host}:{port}/docs")
    print(f"   健康检查: http://{host}:{port}/health")
    print()

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload or settings.debug,
        log_level=settings.log_level.lower(),
    )


def start_web(port: int = 5173):
    """启动前端开发服务器"""
    web_dir = ROOT_DIR / "web"

    if not web_dir.exists():
        print("❌ 前端目录不存在，请先初始化前端项目")
        sys.exit(1)

    # 检查 node_modules
    if not (web_dir / "node_modules").exists():
        print("📦 安装前端依赖...")
        subprocess.run(["npm", "install"], cwd=web_dir, shell=True)

    print(f"🌐 启动前端服务器...")
    print(f"   地址: http://localhost:{port}")
    print()

    env = os.environ.copy()
    env["PORT"] = str(port)
    subprocess.run(["npm", "run", "dev"], cwd=web_dir, shell=True, env=env)


def start_dev():
    """同时启动前后端（开发模式）"""
    import signal
    import time

    print("🔥 开发模式：同时启动前后端")
    print()

    web_dir = ROOT_DIR / "web"

    # 检查前端依赖
    if not (web_dir / "node_modules").exists():
        print("📦 安装前端依赖...")
        subprocess.run(["npm", "install"], cwd=web_dir, shell=True)

    # 使用 subprocess 启动后端（独立进程）
    print("🚀 启动后端服务器 (端口 8081)...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.main:app",
         "--host", "0.0.0.0", "--port", "8081", "--reload"],
        cwd=ROOT_DIR
    )

    # 等待后端启动
    time.sleep(2)

    # 启动前端（独立进程）
    print("🌐 启动前端服务器 (端口 5173)...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=web_dir,
        shell=True
    )

    print()
    print("=" * 50)
    print("  后端: http://localhost:8081")
    print("  前端: http://localhost:5173")
    print("  按 Ctrl+C 停止所有服务")
    print("=" * 50)
    print()

    # 捕获退出信号
    def cleanup(signum, frame):
        print("\n🛑 正在停止服务...")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # 等待进程结束
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        cleanup(None, None)


def main():
    parser = argparse.ArgumentParser(
        description="SAPAS 启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py server              # 启动后端
  python run.py web                 # 启动前端
  python run.py dev                 # 同时启动前后端（推荐）
        """
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=["server", "web", "dev", "help"],
        help="要执行的命令"
    )
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    parser.add_argument("--port", type=int, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="启用热重载")

    args = parser.parse_args()

    if args.command == "help":
        print_banner()
        print_help()
        return

    print_banner()

    if args.command == "server":
        port = args.port or 8081
        start_server(args.host, port, args.reload)

    elif args.command == "web":
        port = args.port or 5173
        start_web(port)

    elif args.command == "dev":
        start_dev()


if __name__ == "__main__":
    main()

