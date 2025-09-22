#!/usr/bin/env python3
"""Python编程教育系统Gradio界面"""

import gradio as gr
import requests
import json
import sys
import os
from pathlib import Path
import time
import threading
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.config import load_config

class PythonEducationSystemGradio:
    """Python编程教育系统Gradio界面类"""
    
    def __init__(self):
        """初始化Gradio界面"""
        # 加载配置
        self.config = load_config()
        self.api_url = f"http://localhost:{self.config.api_port}"
        self.logger = get_logger("gradio_gui")
        
        # 任务状态控制
        self.task_lock = threading.Lock()
        self.current_task = None
        self.task_start_time = None
        
        # 初始化对话历史
        self.chat_history = []
        
        # 检查API连接
        if not self.check_api_connection():
            self.logger.error("无法连接到API服务器，请确保后端服务已启动")
            self.chat_history.append((None, "无法连接到后端API服务器，请确保后端服务已启动"))
    
    def check_api_connection(self):
        """检查API连接状态"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.logger.info(f"已连接到API服务器，端口: {self.config.api_port}")
                    return True
        except Exception as e:
            self.logger.error(f"API连接失败: {e}")
        return False
    
    def acquire_task_lock(self, task_name):
        """尝试获取任务锁，如果已被占用则返回False"""
        if not self.task_lock.acquire(blocking=False):
            elapsed_time = time.time() - self.task_start_time if self.task_start_time else 0
            return False, f"系统当前正在执行{self.current_task}任务，请等待{max(0, 30 - int(elapsed_time))}秒后再试"
        
        self.current_task = task_name
        self.task_start_time = time.time()
        return True, ""
    
    def release_task_lock(self):
        """释放任务锁"""
        self.task_lock.release()
        self.current_task = None
        self.task_start_time = None
    
    def handle_chat(self, message, history, uploaded_file=None):
        """处理对话消息"""
        # 尝试获取任务锁
        acquired, task_message = self.acquire_task_lock("对话")
        if not acquired:
            # 返回更新后的历史和空字符串（用于清空输入框）
            return history + [[None, task_message]], ""
        
        try:
            # 显示用户消息
            user_message_parts = []
            display_parts = []
            
            # 处理文本输入
            if message and message.strip():
                user_message_parts.append(message.strip())
                display_parts.append(message.strip())
            
            # 处理文件输入
            if uploaded_file:
                # 处理上传的文件
                file_content = uploaded_file.read().decode('utf-8')
                user_message_parts.append(f"用户上传了文件 {uploaded_file.name}:\n{file_content}")
                
                display_parts.append(f"上传文件: {uploaded_file.name}")
            
            # 如果没有任何输入，添加提示信息
            if not user_message_parts:
                return history + [[None, "请输入问题或上传文件"]], ""
            
            # 构建完整的用户消息和显示内容
            user_message = "\n\n".join(user_message_parts)
            display_message = "\n".join(display_parts)
            
            # 添加到对话历史
            history.append([display_message, None])
            
            # 调用API处理查询
            try:
                response = requests.post(
                    f"{self.api_url}/query",
                    json={"query": user_message},
                    timeout=600  # 可以根据需要调整超时时间
                )

                if response.status_code == 200:
                    try:
                        response_json = response.json()
                        # 安全地获取响应内容
                        if response_json.get("success"):
                            bot_response = response_json.get("response", "抱歉，无法获取响应")
                        else:
                            bot_response = response_json.get("error", "服务器处理失败")
                    except json.JSONDecodeError:
                        bot_response = "无法解析服务器响应格式"
                        self.logger.error(f"解析响应格式失败: {response.text}")
                else:
                    bot_response = f"API请求失败，状态码: {response.status_code}"
                    self.logger.error(f"API请求失败: {response.text}")

            except requests.exceptions.Timeout:
                bot_response = "请求超时，请稍后再试。如果频繁超时，可能是工具执行时间过长。"
                self.logger.error(f"请求超时: {self.api_url}/query")
            except requests.exceptions.ConnectionError:
                bot_response = "无法连接到服务器，请确认后端服务是否正常运行。"
                self.logger.error(f"连接错误: {self.api_url}/query")
            except Exception as e:
                bot_response = f"请求处理失败: {str(e)}"
                self.logger.error(f"请求处理失败: {e}")
            
            # 更新对话历史
            history[-1][1] = bot_response
            # 返回更新后的历史和空字符串（用于清空输入框）
            return history, ""
        finally:
            # 释放任务锁
            self.release_task_lock()
    
    def execute_code(self, code, history):
        """执行Python代码"""
        # 尝试获取任务锁
        acquired, message = self.acquire_task_lock("代码执行")
        if not acquired:
            # 在代码执行区域显示提示消息
            return code, f"\n\n[系统提示] {message}", history
        
        try:
            # 记录执行时间
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result_display = f"=== 代码执行结果 ({start_time}) ===\n\n"
            
            # 调用API执行代码
            try:
                response = requests.post(
                    f"{self.api_url}/execute_code",
                    json={"code": code},
                    timeout=600
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        result_display += "执行成功!\n\n"
                        if data.get("output"):
                            result_display += "输出结果:\n" + data.get("output") + "\n\n"
                        if data.get("return_value"):
                            result_display += "返回值:\n" + str(data.get("return_value")) + "\n"
                    else:
                        result_display += "执行失败!\n\n"
                        if data.get("error"):
                            result_display += "错误信息:\n" + data.get("error") + "\n"
                else:
                    result_display += f"API请求失败，状态码: {response.status_code}\n"
                    self.logger.error(f"API请求失败: {response.text}")
            except Exception as e:
                result_display += f"请求处理失败: {str(e)}\n"
                self.logger.error(f"请求处理失败: {e}")
            
            # 更新代码执行历史
            code_summary = code[:50] + ("..." if len(code) > 50 else "")
            history.append([f"执行代码: {code_summary}", "代码执行完成"])
            
            return code, result_display, history
        finally:
            # 释放任务锁
            self.release_task_lock()
    
    def create_interface(self):
        """创建Gradio界面"""
        
        with gr.Blocks(title="PyLearnChat", theme=gr.themes.Soft()) as interface:
            # 创建标题区域
            with gr.Row(elem_id="title-container"):
                # 将标题放在Gradio界面内部的顶部
                title_markdown = gr.Markdown("""
                # PyLearnChat
                """, elem_id="external-title")
            # 创建左右布局，使用flex容器确保底部对齐
            with gr.Row(elem_id="main-content-container"):
                # 左侧：对话区域
                with gr.Column(scale=1):
                    chatbot = gr.Chatbot(
                        value=self.chat_history,
                        label="对话历史",
                        height=450,  # 减小高度以适应屏幕
                        elem_id="custom-chatbot"  # 添加ID用于自定义CSS
                    )
                    
                    # 创建带悬浮按钮的输入区域
                    with gr.Row(elem_id="chat-input-container"):
                        message = gr.Textbox(
                            placeholder="有问题，尽管问",
                            show_label=False,
                            scale=1,
                            container=False,  # 不使用默认容器
                            lines=5,  # 增加高度为原来的2.5倍（假设原来约为2行）
                            submit_btn=None
                        )
                        # 将按钮添加到同一个容器中
                        submit_button = gr.Button(
                            "▶️",
                            variant="primary",
                            elem_id="floating-submit-btn"
                        )
                        upload_file_button = gr.UploadButton(
                            "📁",
                            file_types=[".py", ".txt"],
                            file_count="single",
                            elem_id="floating-file-btn"
                        )
                        upload_image_button = gr.UploadButton(
                            "🖼️",
                            file_types=[".jpg", ".jpeg", ".png", ".gif"],
                            file_count="single",
                            elem_id="floating-image-btn"
                        )
                
                # 右侧：代码执行区域
                with gr.Column(scale=1):
                    # 创建带悬浮按钮的代码输入区域
                    with gr.Row(elem_id="code-input-container"):
                        code_input = gr.Code(
                            language="python",
                            label="Python代码编辑器",
                            value="# 在这里输入Python代码\nprint('Hello, Python!')\n",
                            lines=12,  # 减小行数以适应屏幕
                            scale=1,
                            interactive=True
                        )
                        run_button = gr.Button(
                            "▶️",
                            variant="primary",
                            elem_id="floating-run-btn"
                        )
                    
                    code_output = gr.Textbox(
                        label="执行结果",
                        lines=10,
                        interactive=False
                    )
            
            # 添加自定义CSS样式
            gr.HTML("""
            <style>
                /* 确保整个界面在屏幕内显示 */
                .gradio-container { max-width: 100% !important; }
                
                /* 标题容器样式 */
                #title-container {
                    width: 100%;
                    margin-bottom: 10px;
                    justify-content: center;
                    display: flex;
                }
                
                /* 外部标题样式 */
                #external-title {
                    text-align: center;
                    margin: 0 auto;
                    padding: 6px 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white !important;
                    border-radius: 8px;
                    width: auto;
                    display: inline-block;
                    font-weight: bold;
                    font-size: 20px !important;
                }
                
                /* 确保标题文本颜色正确 */
                #external-title h1 {
                    color: white !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    line-height: 1.2 !important;
                }
                
                /* 主内容容器样式 - 确保底部对齐 */
                #main-content-container {
                    display: flex;
                    width: 100%;
                    height: calc(100vh - 120px);
                }
                
                /* 左侧和右侧列样式 - 确保底部对齐 */
                #main-content-container .column {
                    display: flex;
                    flex-direction: column;
                }
                
                /* 确保整个页面没有滚动条 */
                body {
                    overflow: hidden;
                }
                
                /* 确保Gradio容器适应屏幕 */
                .gradio-container {
                    min-height: 100vh;
                    height: 100vh;
                    max-height: 100vh;
                }
                
                /* 调整代码输出框高度以确保底部对齐 */
                textarea[data-testid="textbox"] {
                    height: auto !important;
                }
                
                /* 输入框容器样式 */
                #chat-input-container {
                    position: relative;
                    width: 100%;
                }
                
                /* 聊天输入框样式 */
                #chat-input-container textarea {
                    width: 100%;
                    padding-right: 100px;  /* 为悬浮按钮留出空间 */
                    border-radius: 12px;
                    border: 1px solid #ddd;
                    padding: 10px 100px 10px 10px;
                    resize: none;
                    min-height: 100px;
                }
                
                /* 圆形悬浮按钮通用样式 */
                #floating-submit-btn, #floating-file-btn, #floating-image-btn, #floating-run-btn {
                    position: absolute;
                    width: 36px !important;
                    height: 36px !important;
                    min-width: unset !important;
                    border-radius: 50% !important;
                    padding: 0 !important;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    z-index: 10;
                }
                
                /* 聊天区域悬浮按钮定位 - 全部放在右下角 */
                #floating-submit-btn {
                    right: 10px;
                    bottom: 10px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                }
                
                #floating-file-btn {
                    right: 50px;
                    bottom: 10px;
                    background: #4CAF50 !important;
                }
                
                #floating-image-btn {
                    right: 90px;
                    bottom: 10px;
                    background: #2196F3 !important;
                }
                
                /* 代码输入区域样式 */
                #code-input-container {
                    position: relative;
                    width: 100%;
                }
                
                /* 代码运行按钮定位 - 放在右下角 */
                #floating-run-btn {
                    right: 10px;
                    bottom: 10px;
                    background: linear-gradient(135deg, #FF9A9E 0%, #FAD0C4 99%, #FAD0C4 100%) !important;
                }
                
                /* 代码输入框添加滚动条 */
                .gradio-container .code-editor-container {
                    max-height: 320px !important;
                    overflow: auto !important;
                    border-radius: 8px !important;
                }
                
                /* 确保代码编辑器内容可滚动 */
                .gradio-container pre {
                    overflow: auto !important;
                }
                
                /* 调整对话框字体大小 */
                #custom-chatbot .message { font-size: 14px; }
                
                /* 为对话框添加滚动条 */
                #custom-chatbot { overflow-y: auto; }
                
                /* 隐藏滚动条但保留功能 */
                .scroll-hide::-webkit-scrollbar { display: none; }
                .scroll-hide { -ms-overflow-style: none; scrollbar-width: none; }
            </style>
            """)
            
            # 设置按钮点击事件 - 添加message作为outputs以实现输入框清空
            submit_button.click(
                fn=self.handle_chat,
                inputs=[message, chatbot],
                outputs=[chatbot, message]
            )
            
            # 文件上传按钮事件绑定
            upload_file_button.upload(
                fn=self.handle_chat,
                inputs=[message, chatbot, upload_file_button],
                outputs=[chatbot, message]
            )
            
            # 图片上传按钮事件绑定
            upload_image_button.upload(
                fn=self.handle_chat,
                inputs=[message, chatbot, upload_image_button],
                outputs=[chatbot, message]
            )
            
            message.submit(
                fn=self.handle_chat,
                inputs=[message, chatbot],
                outputs=[chatbot, message]
            )
            
            run_button.click(
                fn=self.execute_code,
                inputs=[code_input, chatbot],
                outputs=[code_input, code_output, chatbot]
            )
        
        return interface
    
    def launch(self):
        """启动Gradio界面"""
        interface = self.create_interface()
        self.logger.info("正在启动Gradio界面...")
        
        # 在默认浏览器中打开界面
        interface.launch(
            share=False,  # 设置为True可以生成公开链接
            inbrowser=True,
            server_port=7860,  # Gradio服务端口
            server_name="127.0.0.1"
        )

if __name__ == "__main__":
    # 创建并启动Gradio界面
    gradio_app = PythonEducationSystemGradio()
    gradio_app.launch()