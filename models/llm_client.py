#!/usr/bin/env python3
"""大语言模型客户端模块"""

import os
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from langchain.chat_models import ChatOpenAI
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
    
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """生成文本响应"""
        try:
            messages = []
            
            # 添加系统提示
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # 添加用户提示
            messages.append(HumanMessage(content=prompt))
            
            # 调用LLM生成响应
            response = self.llm.invoke(messages)
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"LLM生成失败: {e}")
            return f"生成响应失败: {str(e)}"
    
    def stream_generate(self, prompt: str, system_prompt: str = ""):
        """流式生成文本响应"""
        try:
            messages = []
            
            # 添加系统提示
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # 添加用户提示
            messages.append(HumanMessage(content=prompt))
            
            # 流式调用LLM生成响应
            for chunk in self.llm.stream(messages):
                if chunk.content:
                    yield chunk.content
            
        except Exception as e:
            self.logger.error(f"LLM流式生成失败: {e}")
            yield f"生成响应失败: {str(e)}"
    

    
    async def ask_with_tools(self, query: str, context: str, tools: List[BaseTool]) -> Dict[str, Any]:
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
            result = await agent.ainvoke({
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