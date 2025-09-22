#!/usr/bin/env python3
"""代码执行器模块"""

import sys
import io
import time
import signal
import traceback
from typing import Dict, Any, Optional
import multiprocessing
from contextlib import redirect_stdout, redirect_stderr


class CodeExecutor:
    """Python代码执行器，可以安全地执行用户提供的代码"""
    
    def __init__(self,
                 timeout: int = 5,  # 执行超时时间（秒）
                 memory_limit: int = 100,  # 内存限制（MB）
                 allowed_modules: Optional[list] = None,
                 disallowed_functions: Optional[list] = None
                 ):
        """初始化代码执行器"""
        self.timeout = timeout
        self.memory_limit = memory_limit
        
        # 默认允许的模块
        self.allowed_modules = allowed_modules or [
            'math', 'random', 'datetime', 'json', 're', 'collections',
            'pandas', 'numpy', 'matplotlib', 'sympy', 'statistics'
        ]
        
        # 默认禁止的函数
        self.disallowed_functions = disallowed_functions or [
            'eval', 'exec', '__import__', 'open', 'getattr', 'setattr',
            'delattr', 'compile', 'globals', 'locals', 'vars',
            'system', 'popen', 'spawn', 'fork', 'kill'
        ]
    
    def _check_safety(self, code: str) -> tuple[bool, str]:
        """检查代码安全性"""
        # 简单的安全检查
        for func in self.disallowed_functions:
            if func in code:
                return False, f"禁止使用的函数: {func}"
        
        # 检查导入的模块
        lines = code.split('\n')
        for line in lines:
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                # 这里简化处理，实际应用中需要更复杂的模块检查
                pass
        
        return True, ""
    
    def _execute_code_in_sandbox(self, code: str, result_queue: multiprocessing.Queue) -> None:
        """在沙箱中执行代码"""
        # 重定向标准输出和标准错误
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        result = {
            "output": "",
            "error": ""
        }
        
        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                # 创建一个安全的全局环境
                safe_globals = {
                    '__builtins__': {
                        'print': print,
                        'len': len,
                        'range': range,
                        'list': list,
                        'dict': dict,
                        'set': set,
                        'tuple': tuple,
                        'str': str,
                        'int': int,
                        'float': float,
                        'bool': bool,
                        'None': None
                    }
                }
                
                # 执行代码
                exec(code, safe_globals)
                
                # 获取输出
                result["output"] = stdout_buffer.getvalue()
                result["error"] = stderr_buffer.getvalue()
                
        except Exception as e:
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
        finally:
            # 将结果放入队列
            result_queue.put(result)
    
    def execute(self, code: str) -> Dict[str, Any]:
        """执行Python代码并返回结果"""
        # 检查代码安全性
        is_safe, message = self._check_safety(code)
        if not is_safe:
            return {
                "output": "",
                "error": f"代码不安全: {message}"
            }
        
        # 创建进程来执行代码
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=self._execute_code_in_sandbox,
            args=(code, result_queue)
        )
        
        try:
            # 启动进程
            process.start()
            
            # 等待进程完成或超时
            process.join(self.timeout)
            
            # 如果进程仍在运行，终止它
            if process.is_alive():
                process.terminate()
                process.join()
                return {
                    "output": "",
                    "error": f"代码执行超时（{self.timeout}秒）"
                }
            
            # 获取结果
            if not result_queue.empty():
                result = result_queue.get()
            else:
                result = {
                    "output": "",
                    "error": "没有获取到执行结果"
                }
            
            return result
            
        except Exception as e:
            return {
                "output": "",
                "error": str(e)
            }