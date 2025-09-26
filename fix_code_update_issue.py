#!/usr/bin/env python3
"""解决代码修改不生效问题的工具脚本"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def clear_pycache():
    """清除项目中的所有.pyc文件和__pycache__目录"""
    print("正在清除Python缓存文件...")
    project_root = Path(__file__).parent
    
    # 统计删除的文件数量
    pyc_files_deleted = 0
    pycache_dirs_deleted = 0
    
    # 遍历项目目录
    for root, dirs, files in os.walk(project_root):
        # 删除所有.pyc文件
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                try:
                    os.remove(pyc_path)
                    pyc_files_deleted += 1
                except Exception as e:
                    print(f"删除文件失败 {pyc_path}: {e}")
        
        # 收集所有__pycache__目录以便后续删除
        for dir_name in dirs:
            if dir_name == '__pycache__':
                pycache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(pycache_path)
                    pycache_dirs_deleted += 1
                except Exception as e:
                    print(f"删除目录失败 {pycache_path}: {e}")
    
    print(f"已清除 {pyc_files_deleted} 个.pyc文件和 {pycache_dirs_deleted} 个__pycache__目录")


def find_and_kill_processes():
    """查找并杀死相关的Python进程"""
    print("正在查找并杀死相关的Python进程...")
    
    # 获取当前进程ID，避免杀死自己
    current_pid = str(os.getpid())
    
    # 在Windows上查找并杀死包含main.py或uvicorn的进程
    try:
        # 获取所有进程
        processes = subprocess.check_output(["tasklist", "/fo", "csv"]).decode("gbk").splitlines()
        
        # 要查找的进程关键字
        keywords = ["main.py", "uvicorn", "start_gui.py"]
        
        # 存储找到的进程ID
        pids_to_kill = []
        
        # 分析进程列表
        for line in processes[1:]:  # 跳过标题行
            try:
                parts = line.split(",")
                if len(parts) >= 2:
                    # 去除引号
                    process_name = parts[0].strip('"')
                    pid = parts[1].strip('"')
                    
                    # 跳过当前进程
                    if pid == current_pid:
                        continue
                    
                    # 检查是否是python进程并且命令行包含关键字
                    if process_name.lower() == "python.exe" or process_name.lower() == "pythonw.exe":
                        # 尝试获取命令行参数
                        try:
                            cmdline = subprocess.check_output(["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"], 
                                                             stderr=subprocess.STDOUT).decode("gbk")
                            
                            # 检查是否包含关键字
                            if any(keyword in cmdline for keyword in keywords):
                                pids_to_kill.append(pid)
                                print(f"找到相关进程: PID={pid}, CommandLine={cmdline.strip()}")
                        except:
                            pass
            except:
                pass
        
        # 杀死找到的进程
        if pids_to_kill:
            print(f"正在杀死 {len(pids_to_kill)} 个进程...")
            for pid in pids_to_kill:
                try:
                    subprocess.run(["taskkill", "/F", "/PID", pid], check=True)
                    print(f"成功：已终止 PID 为 {pid} 的进程。")
                except Exception as e:
                    print(f"杀死进程失败 PID={pid}: {e}")
        else:
            print("没有找到需要杀死的相关进程")
    except Exception as e:
        print(f"查找进程时出错: {e}")


# def fix_education_system():  # 注意这个函数名是为了符合requirements中的命名规范
#     """修复education_system.py中的逻辑错误"""
#     file_path = os.path.join(Path(__file__).parent, "src", "education_system.py")
    
#     print(f"正在修复文件: {file_path}")
    
#     try:
#         # 读取文件内容
#         with open(file_path, 'r', encoding='utf-8') as f:
#             content = f.read()
        
#         # 查找并替换错误的代码
#         old_code = "        except Exception as e:\n            self.logger.error(f\"处理查询失败: {e}\")\n            return {\n                \"success\": False,\n                \"response\": response\n            }"
#         new_code = "        except Exception as e:\n            self.logger.error(f\"处理查询失败: {e}\")\n            return {\n                \"success\": False,\n                \"error\": str(e)\n            }"
        
#         if old_code in content:
#             # 执行替换
#             updated_content = content.replace(old_code, new_code)
            
#             # 写回文件
#             with open(file_path, 'w', encoding='utf-8') as f:
#                 f.write(updated_content)
            
#             print("成功修复education_system.py中的逻辑错误")
#         else:
#             print("文件中未找到需要修复的代码模式，可能已经修复过了")
#     except Exception as e:
#         print(f"修复文件时出错: {e}")


def clear_main():
    """清理所有进程，用于解决代码修改不生效问题"""
    print("===== 开始解决代码修改不生效问题 =====")
    
    # 1. 杀死相关进程
    find_and_kill_processes()
    
    # 2. 清除缓存
    clear_pycache()
    
    # # 3. 修复文件
    # fix_education_system()
    
    print("\n===== 操作完成 =====")
    print("\n现在您可以重新启动系统了。建议的启动步骤：")
    print("1. 确保所有Python相关的命令窗口都已关闭")
    print("2. 重新运行 start_gui.py 启动系统")
    print("\n代码修改不生效的常见原因及解决方案总结：")
    print("1. Python编译缓存问题：Python会将.py文件编译成.pyc文件缓存起来")
    print("   解决：清除__pycache__目录和.pyc文件")
    print("2. 进程未完全终止：修改后的代码无法覆盖正在运行的进程使用的代码")
    print("   解决：确保完全终止所有相关进程后再重启")
    print("3. 文件权限问题：某些情况下可能没有足够权限修改文件")
    print("   解决：以管理员身份运行编辑器或命令提示符")
    print("4. 路径问题：可能修改了错误路径下的文件")
    print("   解决：确认正在修改的文件确实是程序正在使用的文件")


if __name__ == "__main__":
    clear_main()