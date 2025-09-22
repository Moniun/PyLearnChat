#!/usr/bin/env python3
"""API服务器模块"""

import os
import sys
import json
from typing import Dict, List, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from utils.logger import get_logger
from utils.config import SystemConfig
from src.education_system import PythonEducationSystem


# 请求模型
class CodeExecutionRequest(BaseModel):
    code: str = Field(..., description="要执行的Python代码")


class QuizGenerationRequest(BaseModel):
    topic: str = Field(..., description="测验主题")
    difficulty: str = Field(default="medium", description="难度级别")
    num_questions: int = Field(default=5, description="问题数量")


class AnswerCheckRequest(BaseModel):
    question: str = Field(..., description="问题内容")
    user_answer: str = Field(..., description="用户答案")


class ConceptExplanationRequest(BaseModel):
    concept: str = Field(..., description="要解释的概念")
    level: str = Field(default="beginner", description="解释级别")


class QueryRequest(BaseModel):
    query: str = Field(..., description="用户查询")


# 全局变量存储教育系统实例
_education_system = None
_config = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _education_system, _config
    
    # 应用启动时初始化
    logger = get_logger("api_server")
    logger.info("API服务器启动中...")
    
    # 这里我们不重新初始化，而是使用main.py中创建的实例
    # 因为FastAPI启动在单独的进程中，所以这个部分在实际运行时可能需要调整
    
    yield
    
    # 应用关闭时清理
    logger.info("API服务器关闭中...")


def create_app(education_system: PythonEducationSystem, config: SystemConfig) -> FastAPI:
    """创建FastAPI应用"""
    global _education_system, _config
    _education_system = education_system
    _config = config
    
    app = FastAPI(title="Python编程教育系统API", version="1.0.0", lifespan=lifespan)
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 根路径
    @app.get("/")
    async def root():
        return {
            "message": "Python编程教育系统API",
            "version": "1.0.0",
            "endpoints": ["/execute_code", "/generate_quiz", "/check_answer", "/explain_concept", "/query"]
        }
    
    # 执行代码端点
    @app.post("/execute_code")
    async def execute_code_endpoint(request: CodeExecutionRequest):
        try:
            if not _education_system:
                raise HTTPException(status_code=503, detail="系统未初始化")
            
            result = _education_system.execute_code(request.code)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # # 生成测验端点
    # @app.post("/generate_quiz")
    # async def generate_quiz_endpoint(request: QuizGenerationRequest):
    #     try:
    #         if not _education_system:
    #             raise HTTPException(status_code=503, detail="系统未初始化")
            
    #         result = _education_system.generate_quiz(
    #             topic=request.topic,
    #             difficulty=request.difficulty,
    #             num_questions=request.num_questions
    #         )
    #         return result
    #     except Exception as e:
    #         raise HTTPException(status_code=500, detail=str(e))
    
    # # 检查答案端点
    # @app.post("/check_answer")
    # async def check_answer_endpoint(request: AnswerCheckRequest):
    #     try:
    #         if not _education_system:
    #             raise HTTPException(status_code=503, detail="系统未初始化")
            
    #         result = _education_system.check_answer(
    #             question=request.question,
    #             user_answer=request.user_answer
    #         )
    #         return result
    #     except Exception as e:
    #         raise HTTPException(status_code=500, detail=str(e))
    
    # # 解释概念端点
    # @app.post("/explain_concept")
    # async def explain_concept_endpoint(request: ConceptExplanationRequest):
    #     try:
    #         if not _education_system:
    #             raise HTTPException(status_code=503, detail="系统未初始化")
            
    #         result = _education_system.explain_concept(
    #             concept=request.concept,
    #             level=request.level
    #         )
    #         return result
    #     except Exception as e:
    #         raise HTTPException(status_code=500, detail=str(e))
    
    # 通用查询端点
    @app.post("/query")
    async def query_endpoint(request: QueryRequest):
        try:
            if not _education_system:
                raise HTTPException(status_code=503, detail="系统未初始化")
            
            result = await _education_system.handle_query(request.query)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # 健康检查端点
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "system_initialized": _education_system is not None
        }
    
    return app

def start_server(education_system: PythonEducationSystem, config: SystemConfig):
    """启动API服务器"""
    logger = get_logger("api_server")
    
    # 创建FastAPI应用
    app = create_app(education_system, config)
    
    logger.info(f"API服务器启动在端口 {config.api_port}...")
    logger.info("请访问 http://localhost:{config.api_port} 查看API文档")
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.api_port,
        reload=config.debug
    )