#!/usr/bin/env python3
"""验证后端服务是否正常运行的工具脚本"""

import os
import sys
import requests
import json
from pathlib import Path
import time
import subprocess


def load_config():
    """加载配置文件"""
    config_path = os.path.join(Path(__file__).parent, "config.yaml")
    
    if not os.path.exists(config_path):
        print(f"错误: 找不到配置文件 {config_path}")
        return None
    
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        return config_data
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return None


def check_port_status(port):
    """检查端口是否被占用"""
    try:
        # 在Windows上使用netstat命令检查端口状态
        if os.name == 'nt':  # Windows系统
            output = subprocess.check_output(["netstat", "-ano"], stderr=subprocess.STDOUT).decode("gbk")
            for line in output.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    # 提取PID
                    pid = line.strip().split()[-1]
                    # 尝试获取进程名称
                    try:
                        process_name = subprocess.check_output(["tasklist", "/fi", f"PID eq {pid}"], stderr=subprocess.STDOUT).decode("gbk")
                        return True, f"端口 {port} 已被占用，进程ID: {pid}, 进程信息: {process_name.splitlines()[3].strip()}"
                    except:
                        return True, f"端口 {port} 已被占用，进程ID: {pid}"
        return False, f"端口 {port} 未被占用"
    except Exception as e:
        return None, f"检查端口状态时出错: {e}"


def test_api_connection(config_data):
    """测试API连接"""
    if not config_data:
        return False, "无法加载配置文件"
    
    api_port = config_data.get("api_port", 8000)
    api_url = f"http://localhost:{api_port}"
    
    print(f"\n正在测试API连接 (端口: {api_port})...")
    
    # 检查端口状态
    port_status, port_message = check_port_status(api_port)
    print(port_message)
    
    if not port_status:
        return False, f"端口 {api_port} 未被占用，后端服务可能未启动"
    
    # 尝试连接API健康检查端点
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        print(f"健康检查响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                health_data = response.json()
                print(f"健康检查响应: {json.dumps(health_data, indent=2)}")
                if health_data.get("status") == "healthy":
                    return True, "后端服务运行正常"
                else:
                    return False, f"后端服务状态异常: {health_data}"
            except json.JSONDecodeError:
                return False, f"无法解析健康检查响应: {response.text}"
        else:
            return False, f"健康检查失败，状态码: {response.status_code}, 响应: {response.text}"
    except requests.exceptions.ConnectionError:
        return False, f"无法连接到API服务器，请确认服务是否已启动"
    except requests.exceptions.Timeout:
        return False, f"API请求超时，可能是后端服务响应缓慢或端口错误"
    except Exception as e:
        return False, f"API连接测试失败: {e}"


def list_running_python_processes():
    """列出所有正在运行的Python进程"""
    print("\n正在运行的Python进程:")
    try:
        if os.name == 'nt':  # Windows系统
            # 获取所有进程
            processes = subprocess.check_output(["tasklist", "/fo", "csv"], stderr=subprocess.STDOUT).decode("gbk").splitlines()
            
            python_processes = []
            for line in processes[1:]:  # 跳过标题行
                try:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        # 去除引号
                        process_name = parts[0].strip('"')
                        pid = parts[1].strip('"')
                        
                        # 检查是否是python进程
                        if process_name.lower() == "python.exe" or process_name.lower() == "pythonw.exe":
                            # 尝试获取命令行参数
                            try:
                                cmdline = subprocess.check_output(["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"], 
                                                                 stderr=subprocess.STDOUT).decode("gbk")
                                python_processes.append((pid, process_name, cmdline.strip()))
                            except:
                                python_processes.append((pid, process_name, "无法获取命令行"))
                except:
                    pass
            
            if python_processes:
                for pid, name, cmdline in python_processes:
                    print(f"PID: {pid}, 名称: {name}")
                    print(f"命令行: {cmdline}")
                    print("=" * 80)
            else:
                print("未找到正在运行的Python进程")
    except Exception as e:
        print(f"列出进程时出错: {e}")


def main():
    """主函数"""
    print("===== 后端服务验证工具 =====")
    
    # 加载配置
    config_data = load_config()
    if not config_data:
        print("请确保配置文件存在且格式正确")
        return
    
    print(f"\n配置信息:")
    print(f"API端口: {config_data.get('api_port', 8000)}")
    print(f"调试模式: {config_data.get('debug', False)}")
    print(f"允许的函数: {', '.join(config_data.get('allowed_functions', []))}")
    
    # 测试API连接
    success, message = test_api_connection(config_data)
    print(f"\nAPI连接测试结果: {'成功' if success else '失败'}")
    print(f"{message}")
    
    # 列出所有正在运行的Python进程
    list_running_python_processes()
    
    # 提供问题排查建议
    print("\n===== 问题排查建议 =====")
    if not success:
        api_port = config_data.get("api_port", 8000)
        print(f"\n1. 确保后端服务已启动")
        print(f"   运行: python main.py")
        print(f"   或通过start_gui.py启动整个系统")
        
        print(f"\n2. 检查API端口配置是否一致")
        print(f"   当前配置的API端口: {api_port}")
        
        print(f"\n3. 如果端口被占用，可能需要:")
        print(f"   a) 终止占用端口的进程")
        print(f"   b) 修改config.yaml中的api_port为其他可用端口")
        
        print(f"\n4. 检查网络连接是否正常")
        print(f"   尝试在浏览器中访问: http://localhost:{api_port}/health")
        
        print(f"\n5. 查看日志文件获取更详细的错误信息")
    
    print("\n===== 操作完成 =====")


if __name__ == "__main__":
    main()