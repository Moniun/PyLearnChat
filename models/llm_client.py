#!/usr/bin/env python3
"""大语言模型客户端模块"""

import os
import threading
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
    
    def generate(self, prompt: str, system_prompt: str = "", stream: bool = True, request_id: str = None):
        """生成文本响应，支持流式输出"""
        try:
            messages = []
            
            # 添加系统提示
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # 添加用户提示
            messages.append(HumanMessage(content=prompt))
            
            # 非流式输出
            if not stream:
                response = self.llm.invoke(messages)
                return response.content
            
            # 流式输出
            # 设置请求ID和重置中止标志
            if request_id:
                self.set_request_id(request_id)
                self.set_abort_flag(False, request_id)
                
            for chunk in self.llm.stream(messages):
                # 检查中止标志
                if request_id and self.get_abort_flag():
                    self.logger.info("流式生成被中止")
                    yield "[系统提示] 输出已中止"
                    break
                
                if chunk.content:
                    yield chunk.content
            
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
    
    def set_abort_flag(self, flag: bool, request_id: str = None):
        """设置中止标志"""
        with self.abort_lock:
            if request_id is None or self.request_id == request_id:
                self.abort_flag = flag
                self.logger.info(f"设置中止标志: {flag}, 请求ID: {request_id}")
                return True
            return False
    
    def get_abort_flag(self) -> bool:
        """获取中止标志"""
        with self.abort_lock:
            return self.abort_flag
    
    def set_request_id(self, request_id: str):
        """设置当前请求ID"""
        with self.request_lock:
            self.request_id = request_id
    
    def ask_with_tools(self, query: str, context: str, tools: List[BaseTool], stream: bool = True, request_id: str = None):
        """使用工具调用回答问题"""
        try:
            # 构造系统提示
            system_prompt = f"""
            你是一个Python编程教育助手。请根据用户的问题和提供的上下文，使用适当的工具来回答问题。
            
            上下文信息：
            {context}
            
            你可以使用以下工具：
            {[tool.name for tool in tools]}
            """
            
            # 构造消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ]
            
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
            result = agent.invoke({
                "input": query,
                "chat_history": messages
            })

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
