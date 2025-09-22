#!/usr/bin/env python3
"""Python编程教育系统核心模块"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.tools import BaseTool, StructuredTool, tool

from utils.config import SystemConfig
from utils.logger import get_logger
from models.llm_client import LLMClient
from models.rag_manager import RAGManager
from utils.code_executor import CodeExecutor


class PythonEducationSystem:
    """Python编程教育系统主类"""
    
    def __init__(self, config: SystemConfig):
        """初始化教育系统"""
        self.config = config
        self.logger = get_logger("education_system")
        
        # 初始化组件
        self.llm_client = LLMClient(config.llm)
        self.rag_manager = RAGManager(config.rag, self.llm_client)
        self.code_executor = CodeExecutor()
        
        # 初始化知识库
        self._init_knowledge_base()
        
        # 注册工具函数
        self.tools = self._register_tools()
    
    def _init_knowledge_base(self):
        """初始化知识库"""
        try:
            # 检查是否有现有文档
            knowledge_dir = os.path.join(self.config.data_dir, "knowledge")
            if os.path.exists(knowledge_dir) and os.listdir(knowledge_dir):
                self.rag_manager.load_documents(knowledge_dir)
                self.logger.info(f"已加载知识库文档: {knowledge_dir}")
            else:
                self.logger.info("知识库为空，使用默认配置")
        except Exception as e:
            self.logger.error(f"初始化知识库失败: {e}")
    
    def _register_tools(self) -> List[BaseTool]:
        """注册工具函数"""
        tools = []
        
        # 根据配置注册允许的工具
        if "execute_code" in self.config.allowed_functions:
            tools.append(StructuredTool.from_function(
                func=self.execute_code,
                name="execute_code",
                description="执行Python代码并返回结果"
            ))
        
        if "generate_quiz" in self.config.allowed_functions:
            tools.append(StructuredTool.from_function(
                func=self.generate_quiz,
                name="generate_quiz",
                description="根据主题生成编程测验"
            ))
        
        if "check_answer" in self.config.allowed_functions:
            tools.append(StructuredTool.from_function(
                func=self.check_answer,
                name="check_answer",
                description="检查用户的答案是否正确"
            ))
        
        if "explain_concept" in self.config.allowed_functions:
            tools.append(StructuredTool.from_function(
                func=self.explain_concept,
                name="explain_concept",
                description="解释编程概念"
            ))
        
        # 新工具：搜索知识库
        if "search_knowledge" in self.config.allowed_functions:
            tools.append(StructuredTool.from_function(
                func=self.search_knowledge,
                name="search_knowledge",
                description="在知识库中搜索特定信息"
            ))
        
        # 这里可以继续添加更多工具...
        
        return tools
    
    def search_knowledge(self, query: str, k: int = 5) -> Dict[str, Any]:
        """在知识库中搜索特定信息"""
        try:
            # 使用RAG检索相关文档
            results = self.rag_manager.retrieve(query, k=k)
            
            return {
                "success": True,
                "query": query,
                "response": results
            }
        except Exception as e:
            self.logger.error(f"搜索知识库失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_code(self, code: str) -> Dict[str, Any]:
        """执行Python代码并返回结果"""
        try:
            result = self.code_executor.execute(code)
            return {
                "success": True,
                "output": result["output"],
                "error": result.get("error", "")
            }
        except Exception as e:
            self.logger.error(f"代码执行失败: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    def generate_quiz(self, topic: str, difficulty: str = "medium", num_questions: int = 5) -> Dict[str, Any]:
        """根据主题生成编程测验"""
        try:
            # 使用RAG检索相关知识
            context = self.rag_manager.retrieve(topic, k=3)
            
            # 调用LLM生成测验
            prompt = f"""
            为学习Python编程的学生生成{num_questions}道关于{topic}的测验题，难度为{difficulty}。
            请提供问题、选项（如果是选择题）、正确答案和解释。
            
            相关知识参考：
            {context}
            """
            
            response = self.llm_client.generate(prompt)
            
            # 解析测验结果
            # 这里简化处理，实际应用中可能需要更复杂的解析
            return {
                "success": True,
                "topic": topic,
                "difficulty": difficulty,
                "response": response
            }
        except Exception as e:
            self.logger.error(f"生成测验失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_answer(self, question: str, user_answer: str) -> Dict[str, Any]:
        """检查用户的答案是否正确"""
        try:
            prompt = f"""
            作为Python编程老师，请判断用户的答案是否正确，并提供反馈。
            
            问题: {question}
            用户答案: {user_answer}
            
            请返回：
            - is_correct: 布尔值，表示答案是否正确
            - feedback: 对答案的反馈和解释
            """
            
            response = self.llm_client.generate(prompt)
            
            # 解析结果
            # 这里简化处理，实际应用中可能需要更复杂的解析
            return {
                "success": True,
                "is_correct": "正确" in response,
                "response": response
            }
        except Exception as e:
            self.logger.error(f"检查答案失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def explain_concept(self, concept: str, level: str = "beginner") -> Dict[str, Any]:
        """解释编程概念"""
        try:
            # 使用RAG检索相关知识
            context = self.rag_manager.retrieve(concept, k=3)
            
            # 调用LLM生成解释
            prompt = f"""
            请以{level}水平解释Python编程中的{concept}概念。
            请使用简单易懂的语言，必要时提供代码示例。
            
            相关知识参考：
            {context}
            """
            
            response = self.llm_client.generate(prompt)
            
            return {
                "success": True,
                "concept": concept,
                "level": level,
                "response": response
            }
        except Exception as e:
            self.logger.error(f"解释概念失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def handle_query(self, query: str) -> Dict[str, Any]:
        """处理用户查询"""
        try:
            # 使用RAG检索相关知识
            context = self.rag_manager.retrieve(query, k=3)
            
            # 调用LLM处理查询，可能会使用工具
            response = await self.llm_client.ask_with_tools(query, context, self.tools)
            # 每个工具的result需要统一，不然会有奇怪的返回

            # 提取action的值,从而判断是否要调用工具
            content_dict = response['content']
            content_json = json.loads(content_dict)
            action = content_json['action']
            action_input = content_json['action_input']

            # 根据是否调用工具调用来继续执行工具
            try:
                if action != "Final Answer":
                    # 判断调用什么工具
                    target_tool = getattr(self, action, None)
                    
                    if target_tool is None:
                        # 如果找不到对应的工具，返回错误信息
                        final_response = f"错误: 找不到名为'{action}'的工具函数"
                        self.logger.error(f"找不到工具函数: {action}")
                    else:
                        # 开始调用工具
                        answer_dict = target_tool(**action_input)
                        # 安全地获取response字段
                        final_response = answer_dict.get('response', "工具返回结果格式不正确")
                else:
                    final_response = action_input
            except Exception as e:
                # 捕获所有可能的异常
                error_message = f"工具调用过程中发生错误: {str(e)}"
                final_response = error_message
                self.logger.error(f"工具调用异常: {str(e)}", exc_info=True)

            return {
                "success": True,
                "response": final_response # str
            }
        except Exception as e:
            self.logger.error(f"处理查询失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }