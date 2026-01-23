#!/usr/bin/env python3
"""
SAPAS 健康检查脚本
检查所有服务的运行状态
"""

import sys
import os
import requests
import subprocess
from typing import List, Tuple

# 颜色输出
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
NC = '\033[0m'

# 配置
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8081')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
DB_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://root:J7aXgk2BJUj=@localhost:5432/sapas_db')


def print_status(message: str, status: str) -> None:
    """打印状态信息"""
    if status == 'ok':
        print(f"{GREEN}✓{NC} {message}")
    elif status == 'error':
        print(f"{RED}✗{NC} {message}")
    elif status == 'warning':
        print(f"{YELLOW}⚠{NC} {message}")
    elif status == 'info':
        print(f"{BLUE}ℹ{NC} {message}")


def check_backend() -> bool:
    """检查后端服务"""
    try:
        response = requests.get(f'{BACKEND_URL}/health', timeout=5)
        if response.status_code == 200:
            print_status(f'后端服务正常运行 ({BACKEND_URL})', 'ok')
            return True
        else:
            print_status(f'后端服务返回错误状态码: {response.status_code}', 'error')
            return False
    except requests.exceptions.ConnectionError:
        print_status(f'后端服务无法访问 ({BACKEND_URL})', 'error')
        return False
    except Exception as e:
        print_status(f'后端服务检查失败: {str(e)}', 'error')
        return False


def check_frontend() -> bool:
    """检查前端服务"""
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print_status(f'前端服务正常运行 ({FRONTEND_URL})', 'ok')
            return True
        else:
            print_status(f'前端服务返回错误状态码: {response.status_code}', 'error')
            return False
    except requests.exceptions.ConnectionError:
        print_status(f'前端服务无法访问 ({FRONTEND_URL})', 'warning')
        return False
    except Exception as e:
        print_status(f'前端服务检查失败: {str(e)}', 'warning')
        return False


def check_docker_services() -> List[str]:
    """检查 Docker 服务状态"""
    issues = []

    try:
        # 检查 PostgreSQL
        result = subprocess.run(
            ['docker', 'compose', 'ps', '--services', '--filter', 'status=running'],
            capture_output=True,
            text=True,
            timeout=5
        )

        running_services = result.stdout.strip().split('\n') if result.stdout.strip() else []

        if 'postgres' not in running_services:
            print_status('PostgreSQL 容器未运行', 'error')
            issues.append('postgres')
        else:
            print_status('PostgreSQL 容器运行中', 'ok')

        if 'redis' not in running_services:
            print_status('Redis 容器未运行', 'error')
            issues.append('redis')
        else:
            print_status('Redis 容器运行中', 'ok')

    except FileNotFoundError:
        print_status('Docker 未安装或不在 PATH 中', 'warning')
    except subprocess.TimeoutExpired:
        print_status('Docker 命令超时', 'error')
        issues.append('docker')
    except Exception as e:
        print_status(f'Docker 检查失败: {str(e)}', 'error')
        issues.append('docker')

    return issues


def check_database_connection() -> bool:
    """检查数据库连接"""
    try:
        import asyncpg

        async def test_connection():
            conn = await asyncpg.connect(DB_URL)
            await conn.close()
            return True

        import asyncio
        result = asyncio.run(test_connection())

        if result:
            print_status('数据库连接正常', 'ok')
        else:
            print_status('数据库连接失败', 'error')
        return result

    except ImportError:
        print_status('asyncpg 未安装，跳过数据库连接检查', 'warning')
        return True
    except Exception as e:
        print_status(f'数据库连接检查失败: {str(e)}', 'error')
        return False


def check_redis_connection() -> bool:
    """检查 Redis 连接"""
    try:
        import redis

        r = redis.from_url('redis://localhost:6379/0')
        r.ping()
        print_status('Redis 连接正常', 'ok')
        return True

    except ImportError:
        print_status('redis 未安装，跳过 Redis 连接检查', 'warning')
        return True
    except redis.ConnectionError:
        print_status('Redis 连接失败', 'error')
        return False
    except Exception as e:
        print_status(f'Redis 连接检查失败: {str(e)}', 'error')
        return False


def check_dependencies() -> List[str]:
    """检查 Python 依赖"""
    issues = []

    print_status('检查 Python 依赖...', 'info')

    # 检查关键依赖
    critical_packages = [
        'fastapi',
        'sqlalchemy',
        'akshare',
        'pandas',
        'redis',
    ]

    for package in critical_packages:
        try:
            __import__(package)
        except ImportError:
            print_status(f'依赖包 {package} 未安装', 'error')
            issues.append(package)

    if not issues:
        print_status('所有关键依赖已安装', 'ok')

    return issues


def main():
    """主函数"""
    print(BLUE)
    print('=' * 60)
    print('  SAPAS 健康检查')
    print('  Stock Analysis Processing Automated Service')
    print('=' * 60)
    print(NC)

    all_ok = True

    # 1. 检查 Docker 服务
    print('\n' + '=' * 60)
    print('  Docker 服务检查')
    print('=' * 60)
    docker_issues = check_docker_services()
    if docker_issues:
        all_ok = False

    # 2. 检查依赖
    print('\n' + '=' * 60)
    print('  依赖检查')
    print('=' * 60)
    dep_issues = check_dependencies()
    if dep_issues:
        all_ok = False

    # 3. 检查后端服务
    print('\n' + '=' * 60)
    print('  后端服务检查')
    print('=' * 60)
    if not check_backend():
        all_ok = False

    # 4. 检查前端服务
    print('\n' + '=' * 60)
    print('  前端服务检查')
    print('=' * 60)
    check_frontend()  # 前端不是必须的

    # 5. 检查数据库连接
    print('\n' + '=' * 60)
    print('  数据库连接检查')
    print('=' * 60)
    if not check_database_connection():
        all_ok = False

    # 6. 检查 Redis 连接
    print('\n' + '=' * 60)
    print('  Redis 连接检查')
    print('=' * 60)
    if not check_redis_connection():
        all_ok = False

    # 总结
    print('\n' + '=' * 60)
    if all_ok:
        print(GREEN + '  ✓ 所有检查通过！系统运行正常' + NC)
    else:
        print(RED + '  ✗ 发现问题，请查看上面的错误信息' + NC)
        print('\n建议操作:')

        if docker_issues:
            print('  - 启动 Docker 服务: docker-compose up -d')

        if dep_issues:
            print(f'  - 安装缺失的依赖: pip install {" ".join(dep_issues)}')

        if 'backend' in str(docker_issues + dep_issues):
            print('  - 启动后端: python -m uvicorn src.main:app')
    print('=' * 60)

    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
