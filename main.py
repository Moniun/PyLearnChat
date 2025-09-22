#!/usr/bin/env python3
"""Python编程教育系统主入口文件"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.education_system import PythonEducationSystem
from api.server import start_server
from utils.config import load_config


def main():
    """主函数，启动Python编程教育系统"""
    try:
        # 加载配置
        config = load_config()
        print("配置加载成功")
        
        # 初始化教育系统
        education_system = PythonEducationSystem(config)
        print("教育系统初始化成功")
        
        # 启动API服务器
        start_server(education_system, config)
        
    except Exception as e:
        print(f"系统启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()