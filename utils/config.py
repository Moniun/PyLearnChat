#!/usr/bin/env python3
"""配置管理模块"""

import os
import yaml
from pydantic import BaseModel, Field
from typing import Dict, Optional, List
from dotenv import load_dotenv


class LLMConfig(BaseModel):
    """大语言模型配置"""
    api_key: str
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1000
    base_url: Optional[str] = None  # 自定义API基础URL


class RAGConfig(BaseModel):
    """RAG检索配置"""
    vector_store_path: str = "./data/vector_store"
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedding_model: str = "text-embedding-ada-002"


class HippoConfig(BaseModel):
    """Hippo模型配置"""
    input_dim: int = 384
    hidden_dim: int = 128
    hippo_type: str = "LegS"
    middle_dim: int = 1024
    ffn_dim: int = 512
    output_dim: int = 512
    text_encoder_path: str = "D:/models/all-MiniLM-L6-v2"
    
    # 训练相关配置
    data_path: str = "dialogues_no_kw.json"  # 数据保存路径
    num_samples: int = 800  # 生成的样本数量
    max_seq_len: int = 10  # 最大对话轮数
    save_path: str = "hippo_no_kw_model.pt"  # 模型保存路径
    epochs: int = 8  # 训练轮数
    batch_size: int = 4  # 批次大小
    lr: float = 1e-4  # 学习率


class SystemConfig(BaseModel):
    """系统配置"""
    llm: LLMConfig
    rag: RAGConfig
    hippo: HippoConfig = Field(default_factory=HippoConfig)
    api_port: int = 8888
    debug: bool = False
    data_dir: str = "./data"
    models_dir: str = "./models"
    allowed_functions: List[str] = Field(default_factory=lambda: [
        "execute_code", "generate_quiz", "check_answer", 
        "explain_concept", "search_knowledge", "other_questions"
    ])


def load_config(config_path: str = "./config.yaml") -> SystemConfig:
    """加载配置文件"""
    # 加载.env文件中的环境变量
    load_dotenv()
    
    # 如果配置文件不存在，创建默认配置文件
    if not os.path.exists(config_path):
        # 优先从环境变量获取API密钥
        api_key_from_env = os.environ.get("LLM_API_KEY")
        
        default_config = SystemConfig(
            llm=LLMConfig(api_key=api_key_from_env or "your-api-key-here"),
            rag=RAGConfig(),
            hippo=HippoConfig()
        )
        
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 保存默认配置
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config.model_dump(), f, allow_unicode=True)
            
        print(f"默认配置文件已创建: {config_path}")
        print("请编辑配置文件设置API密钥等信息")
        
        return default_config
    
    # 加载现有的配置文件
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    # 如果环境变量中有API密钥，则使用它覆盖配置文件中的值
    api_key_from_env = os.environ.get("LLM_API_KEY")
    if api_key_from_env:
        if "llm" not in config_data:
            config_data["llm"] = {}
        config_data["llm"]["api_key"] = api_key_from_env
    
    # 验证并返回配置
    return SystemConfig(**config_data)