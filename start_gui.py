#!/usr/bin/env python3
"""启动Python编程教育系统前端界面"""

import os
import sys
import subprocess
import time
from pathlib import Path
import webbrowser

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from utils.logger import get_logger
from utils.config import load_config


def check_backend_status(config):
    """检查后端服务是否正在运行"""
    try:
        import requests
        response = requests.get(f"http://localhost:{config.api_port}/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "healthy"
    except (requests.exceptions.RequestException, ImportError):
        pass
    return False


def start_backend_if_needed(config):
    """如果后端服务未运行，则启动它"""
    if check_backend_status(config):
        print("后端服务已在运行")
        return None
    
    print("正在启动后端服务...")
    # 在Windows上使用shell=True可以正确打开新的命令窗口
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent,
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE  # 在Windows上创建新窗口
    )
    
    # 增强的等待逻辑
    max_wait_time = 60  # 增加到60秒
    print(f"等待后端服务初始化，最多等待{max_wait_time}秒...")
    start_time = time.time()
    retry_interval = 1
    
    while time.time() - start_time < max_wait_time:
        time.sleep(retry_interval)
        
        # 每3次尝试后增加等待间隔
        if (time.time() - start_time) % 3 == 0 and retry_interval < 3:
            retry_interval += 0.5
            
        if check_backend_status(config):
            print("后端服务启动成功")
            # 执行预热API调用，确保所有资源都已加载
            try:
                import requests
                requests.get(f"http://localhost:{config.api_port}/query?query=ping", timeout=2)
                print("后端服务预热完成")
            except Exception as e:
                print(f"后端服务预热过程中出现异常，但不影响继续使用: {e}")
            return process
        
        elapsed = int(time.time() - start_time)
        print(f"已等待{elapsed}秒...")
    
    print("警告: 后端服务可能未完全启动，正在继续启动GUI，请稍后刷新页面")
    return process


def start_gui():
    """启动GUI界面"""
    # 加载配置
    try:
        config = load_config()
    except Exception as e:
        print(f"加载配置失败: {e}")
        config = None
    
    # 启动后端服务（如果需要）
    backend_process = start_backend_if_needed(config)
    
    # 启动GUI界面
    print("正在启动前端界面...")
    try:
        # 确保gui目录存在
        gui_dir = os.path.join(Path(__file__).parent, "gui")
        if not os.path.exists(gui_dir):
            os.makedirs(gui_dir)
            print(f"创建GUI目录: {gui_dir}")
        
        # 运行GUI应用
        gui_process = subprocess.Popen(
            [sys.executable, os.path.join("gui", "gradio_app.py")],
            cwd=Path(__file__).parent,
            shell=True
        )
        
        # 等待GUI进程结束
        gui_process.wait()
        
        # 如果我们启动了后端进程，在GUI关闭后也关闭后端
        if backend_process and check_backend_status(config):
            print("正在关闭后端服务...")
            # 在Windows上，我们需要使用taskkill来终止进程树
            if os.name == 'nt':  # Windows系统
                subprocess.run(f"taskkill /F /PID {backend_process.pid} /T", shell=True)
            else:  # Unix-like系统
                backend_process.terminate()
                backend_process.wait()
        
    except Exception as e:
        print(f"启动GUI界面失败: {e}")
        # 如果发生错误，确保后端进程被终止
        if backend_process:
            try:
                if os.name == 'nt':
                    subprocess.run(f"taskkill /F /PID {backend_process.pid} /T", shell=True)
                else:
                    backend_process.terminate()
                    backend_process.wait()
            except:
                pass
        sys.exit(1)


if __name__ == "__main__":
    start_gui()