#!/usr/bin/env python3
"""RAG（检索增强生成）管理器模块"""

import os
import glob
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA

from utils.logger import get_logger
from utils.config import RAGConfig
from models.llm_client import LLMClient


class RAGManager:
    """RAG管理器，负责文档加载、嵌入和检索"""
    
    def __init__(self, config: RAGConfig, llm_client: LLMClient):
        """初始化RAG管理器"""
        self.config = config
        self.llm_client = llm_client
        self.logger = get_logger("rag_manager")
        
        # 初始化嵌入模型
        self.embeddings = OpenAIEmbeddings(model=config.embedding_model)
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # 初始化向量存储
        self.vector_store = self._init_vector_store()
    
    def _init_vector_store(self) -> Chroma:
        """初始化向量存储"""
        try:
            # 创建向量存储目录
            os.makedirs(self.config.vector_store_path, exist_ok=True)
            
            # 初始化向量存储
            vector_store = Chroma(
                persist_directory=self.config.vector_store_path,
                embedding_function=self.embeddings
            )
            
            return vector_store
            
        except Exception as e:
            self.logger.error(f"初始化向量存储失败: {e}")
            # 返回一个临时的向量存储作为备选
            return Chroma(embedding_function=self.embeddings)
    
    def _load_document(self, file_path: str) -> List[Document]:
        """加载单个文档"""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
            elif file_ext == ".md":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
            elif file_ext == ".pdf":
                # 这里简化处理，实际应用中需要使用pdf解析库
                self.logger.warning(f"PDF文件支持尚未完全实现: {file_path}")
                return []
                
            elif file_ext in [".docx", ".doc"]:
                # 这里简化处理，实际应用中需要使用docx解析库
                self.logger.warning(f"Word文件支持尚未完全实现: {file_path}")
                return []
                
            else:
                self.logger.warning(f"不支持的文件格式: {file_ext}")
                return []
                
            # 创建文档对象
            document = Document(
                page_content=content,
                metadata={"source": file_path}
            )
            
            # 分割文档
            return self.text_splitter.split_documents([document])
            
        except Exception as e:
            self.logger.error(f"加载文档失败 {file_path}: {e}")
            return []
    
    def load_documents(self, directory: str) -> int:
        """从目录加载所有文档"""
        try:
            if not os.path.exists(directory):
                self.logger.warning(f"目录不存在: {directory}")
                return 0
                
            # 获取所有支持的文件
            supported_extensions = ["*.txt", "*.md", "*.pdf", "*.docx", "*.doc"]
            files = []
            
            for ext in supported_extensions:
                files.extend(glob.glob(os.path.join(directory, "**", ext), recursive=True))
            
            if not files:
                self.logger.warning(f"未找到任何文档: {directory}")
                return 0
                
            # 加载所有文档
            all_docs = []
            for file_path in files:
                docs = self._load_document(file_path)
                all_docs.extend(docs)
                
            # 添加到向量存储
            if all_docs:
                self.vector_store.add_documents(all_docs)
                self.vector_store.persist()
                self.logger.info(f"已加载 {len(all_docs)} 个文档片段")
                
            return len(all_docs)
            
        except Exception as e:
            self.logger.error(f"加载文档目录失败 {directory}: {e}")
            return 0
    
    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加单个文档内容"""
        try:
            if not content.strip():
                self.logger.warning("尝试添加空文档")
                return False
                
            # 创建文档对象
            document = Document(
                page_content=content,
                metadata=metadata or {}
            )
            
            # 分割文档
            docs = self.text_splitter.split_documents([document])
            
            # 添加到向量存储
            self.vector_store.add_documents(docs)
            self.vector_store.persist()
            
            self.logger.info(f"已添加 {len(docs)} 个文档片段")
            return True
            
        except Exception as e:
            self.logger.error(f"添加文档失败: {e}")
            return False
    
    def retrieve(self, query: str, k: int = 3) -> str:
        """根据查询检索相关文档"""
        try:
            if not self.vector_store._collection.count() > 0:
                self.logger.warning("向量存储为空，无法检索")
                return ""
                
            # 检索相关文档
            results = self.vector_store.similarity_search(query, k=k)
            
            # 格式化结果
            context = "\n\n".join([f"来源: {doc.metadata.get('source', '未知')}\n内容: {doc.page_content}" for doc in results])
            
            return context
            
        except Exception as e:
            self.logger.error(f"检索文档失败: {e}")
            return ""
    
    def ask_rag(self, query: str, k: int = 3) -> str:
        """使用RAG回答问题"""
        try:
            # 检索相关文档
            context = self.retrieve(query, k=k)
            
            # 如果没有检索到相关文档，直接使用LLM回答
            if not context:
                return self.llm_client.generate(query)
                
            # 构造带上下文的提示
            prompt = f"""
            请根据提供的上下文信息回答问题。如果上下文信息不足，请根据你的知识回答。
            
            上下文信息：
            {context}
            
            问题：
            {query}
            
            回答：
            """
            
            # 使用LLM生成回答
            return self.llm_client.generate(prompt)
            
        except Exception as e:
            self.logger.error(f"RAG回答失败: {e}")
            return f"回答问题失败: {str(e)}"
    
    def clear_vector_store(self) -> bool:
        """清空向量存储"""
        try:
            # 删除向量存储文件
            if os.path.exists(self.config.vector_store_path):
                for file in glob.glob(os.path.join(self.config.vector_store_path, "*")):
                    os.remove(file)
                    
            # 重新初始化向量存储
            self.vector_store = self._init_vector_store()
            
            self.logger.info("向量存储已清空")
            return True
            
        except Exception as e:
            self.logger.error(f"清空向量存储失败: {e}")
            return False