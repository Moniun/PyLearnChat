#!/usr/bin/env python3
"""大语言模型客户端模块"""

import os
import threading
import atexit
from typing import Dict, List, Any, Optional, Tuple
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    FunctionMessage,
    ChatMessage
)
from langchain.tools import BaseTool
from utils.logger import get_logger
from utils.config import LLMConfig


class LLMClient:
    """大语言模型客户端"""
    
    def __init__(self, config: LLMConfig):
        """初始化LLM客户端"""
        self.config = config
        self.logger = get_logger("llm_client")
        
        # 设置API密钥
        if config.api_key and config.api_key != "your-api-key-here":
            os.environ["OPENAI_API_KEY"] = config.api_key
        else:
            self.logger.warning("未设置有效的API密钥，请在配置文件中设置")
        
        # 初始化ChatOpenAI客户端
        chat_params = {
            "model_name": config.model_name,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }
        
        # 如果配置了base_url，则添加到参数中
        if config.base_url:
            chat_params["openai_api_base"] = config.base_url
            self.logger.info(f"使用自定义base_url: {config.base_url}")
        
        self.llm = ChatOpenAI(**chat_params)
        
        # 流式输出中止控制
        self.abort_flag = False
        self.abort_lock = threading.Lock()
        self.request_id = None
        self.request_lock = threading.Lock()
        
        # 历史消息存储 - 简单的内存存储
        self.chat_history = []
        self.history_lock = threading.Lock()
        
        # 注册程序退出时的清理函数
        atexit.register(self.clear_chat_history)
    
    def set_abort_flag(self, flag: bool, request_id: str = None):
        """设置中止标志
        如果request_id为None，则中止所有请求
        """
        with self.abort_lock:
            if request_id is None:
                # 中止所有请求
                self.abort_flag = flag
                self.logger.info(f"设置全局中止标志: {flag}")
                return True
            elif self.request_id == request_id:
                # 中止特定请求
                self.abort_flag = flag
                self.logger.info(f"设置中止标志: {flag}, 请求ID: {request_id}")
                return True
            return False
    
    def cleanup(self):
        """清理LLM客户端资源"""
        self.logger.info("清理LLM客户端资源...")
        # 中止所有正在进行的请求
        self.set_abort_flag(True)  # 不带request_id会中止所有请求
        
        # 清理会话历史
        self.clear_chat_history()
        
        # 重置请求ID
        with self.request_lock:
            self.request_id = None
        
        self.logger.info("LLM客户端资源清理完成")
    
    def get_abort_flag(self) -> bool:
        """获取中止标志"""
        with self.abort_lock:
            return self.abort_flag
    
    def set_request_id(self, request_id: str):
        """设置当前请求ID"""
        with self.request_lock:
            self.request_id = request_id
    
    def clear_chat_history(self):
        """清空所有历史消息"""
        with self.history_lock:
            self.chat_history.clear()
            self.logger.info("历史消息已清空")
    
    def __del__(self):
        """对象被垃圾回收时自动清理历史消息"""
        try:
            self.clear_chat_history()
        except Exception as e:
            # 避免析构函数中的异常影响程序退出
            pass
    
    def ask_with_tools(self, query: str, context: str, tools: List[BaseTool], stream: bool = True, request_id: str = None, session_id: Optional[str] = None):
        """使用工具调用回答问题，支持历史消息参考"""
        try:
            # 构造系统提示
            system_prompt = f"""
            你是一个Python编程教育助手。请根据用户的问题、参考资料和提供的上下文，使用适当的工具来回答问题。
            每次回答都使用工具，如果遇到和Python无关的问题或你不知道使用什么工具，则使用“other_questions”工具。
            
            参考信息：
            {context}
            
            你可以使用以下工具：
            {[tool.name for tool in tools]}
            """
            
            # 构造消息列表，包含系统消息和历史消息
            messages = [SystemMessage(content=system_prompt)]
            
            # 获取并添加历史消息
            with self.history_lock:
                messages.extend(self.chat_history.copy())
            
            # 添加当前用户消息
            messages.append(HumanMessage(content=query))
            
            # 初始化工具调用链
            from langchain.chains import ConversationChain
            from langchain.memory import ConversationBufferMemory
            from langchain.agents import AgentType, initialize_agent
            
            agent = initialize_agent(
                tools,
                self.llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True
            )
            
            # 运行代理
            # 传入完整的会话历史作为chat_history
            chat_history = messages if len(messages) > 1 else []
            result = agent.invoke({
                "input": query,
                "chat_history": chat_history
            })

            # 保存用户问题到历史消息
            with self.history_lock:
                self.chat_history.append(HumanMessage(content=query))

            return {
                "type": "response",
                "content": result["output"]
            }
            
        except Exception as e:
            self.logger.error(f"工具调用失败: {e}")
            return {
                "type": "error",
                "content": f"处理请求失败: {str(e)}"
            }
        finally:
            # 重置中止标志
            if stream and request_id:
                self.set_abort_flag(False, request_id)

    def generate(self, prompt: str, stream: bool = True, request_id: str = None, session_id: Optional[str] = None):
        """生成文本响应，支持流式输出和历史消息参考"""
        try:
            system_prompt = f"""
            你是一个Python编程教育助手。请根据用户的问题和提供的上下文，回答问题。
            """

            # 构造消息列表，包含系统消息和历史消息
            messages = [SystemMessage(content=system_prompt)]
            
            # 获取并添加历史消息
            with self.history_lock:
                messages.extend(self.chat_history.copy())
            
            # 添加当前用户消息
            messages.append(HumanMessage(content=prompt))
            
            # 非流式输出
            if not stream:
                response = self.llm.invoke(messages)
                
                # 保存AI回答到历史消息
                with self.history_lock:
                    self.chat_history.append(AIMessage(content=response.content))
                
                return response.content
            
            # 流式输出
            # 设置请求ID和重置中止标志
            if request_id:
                self.set_request_id(request_id)
                self.set_abort_flag(False, request_id)
                
            # 流式生成响应
            full_response = ""
            is_completed = False
            
            try:
                for chunk in self.llm.stream(messages):
                    # 检查中止标志
                    if request_id and self.get_abort_flag():
                        self.logger.info("流式生成被中止")
                        yield "[系统提示] 输出已中止"
                        break
                    
                    if chunk.content:
                        full_response += chunk.content
                        yield chunk.content
                else:
                    # 循环正常完成（没有被break）
                    is_completed = True
            finally:
                # 只有当响应完整生成（没有中途停止）时，才保存到历史消息
                if is_completed and full_response:
                    with self.history_lock:
                        self.chat_history.append(AIMessage(content=full_response))
            
        except Exception as e:
            self.logger.error(f"LLM生成失败: {e}")
            if stream:
                yield f"生成响应失败: {str(e)}"
            else:
                return f"生成响应失败: {str(e)}"
        finally:
            # 重置中止标志
            if stream and request_id:
                self.set_abort_flag(False, request_id)