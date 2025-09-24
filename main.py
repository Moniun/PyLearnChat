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
        
    except FileNotFoundError as e:
        print(f"配置文件未找到: {e}")
        print("请确保配置文件存在且路径正确")
        sys.exit(1)
    except ValueError as e:
        print(f"配置参数错误: {e}")
        print("请检查配置文件中的参数是否正确")
        sys.exit(1)
    except RuntimeError as e:
        print(f"运行时错误: {e}")
        print("可能是LLM客户端或教育系统初始化失败")
        print("请检查API密钥、网络连接或配置参数")
        sys.exit(1)
    except ImportError as e:
        print(f"缺少依赖库: {e}")
        print("请安装所需的依赖库")
        sys.exit(1)
    except Exception as e:
        print(f"系统启动失败: {e}")
        print("请查看详细错误信息以获取更多帮助")
        sys.exit(1)


if __name__ == "__main__":
    main()