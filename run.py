#!/usr/bin/env python3
"""
医学图像处理Web系统启动脚本 - 简化版
"""

import os
import sys
import logging
from app import app


def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('web_system.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def check_dependencies():
    """检查必要依赖"""
    required_packages = {
        'torch': 'PyTorch',
        'flask': 'Flask',
        'nibabel': 'NiBabel',
        'PIL': 'Pillow',
        'numpy': 'NumPy'
    }

    missing_packages = []
    for package, name in required_packages.items():
        try:
            if package == 'PIL':
                import PIL
            else:
                __import__(package)
            print(f"✓ {name} 可用")
        except ImportError:
            missing_packages.append(name)
            print(f"✗ {name} 不可用")

    if missing_packages:
        print(f"\n缺少必要的包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False

    return True


def main():
    """主启动函数"""
    print("=" * 50)
    print("医学图像处理Web系统启动器")
    print("=" * 50)

    # 设置日志
    setup_logging()

    # 检查依赖
    print("\n1. 检查依赖包...")
    if not check_dependencies():
        print("依赖检查失败，请安装缺少的包")
        sys.exit(1)

    # 启动Flask应用
    print("\n2. 启动Web服务器...")
    print("=" * 50)
    print("服务器地址: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)

    try:
        # 直接运行Flask应用
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()