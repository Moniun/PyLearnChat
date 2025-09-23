#!/usr/bin/env python3
"""API服务器模块"""

import os
import sys
import json
from typing import Dict, List, Any, Optional, Generator
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from utils.logger import get_logger
from utils.config import SystemConfig
from src.education_system import PythonEducationSystem


# 请求模型
class CodeExecutionRequest(BaseModel):
    code: str = Field(..., description="要执行的Python代码")


class QueryRequest(BaseModel):
    query: str = Field(..., description="用户查询")


class AbortRequest(BaseModel):
    request_id: Optional[str] = Field(None, description="要中止的请求ID")


# 全局变量存储教育系统实例
_education_system = None
_config = None
# 全局日志器
logger = get_logger("api_server")


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
    
    
    # 通用查询端点
    @app.post("/query")
    async def query(request: QueryRequest):
        """处理用户查询请求"""
        try:
            if not _education_system:
                raise HTTPException(status_code=503, detail="系统未初始化")
            
            response = await _education_system.handle_query(request.query)
            return JSONResponse(content=response)
        except Exception as e:
            logger.error(f"查询处理失败: {e}")
            raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}")

    @app.post("/stream_query")
    def stream_query(request: QueryRequest):
        """处理用户流式查询请求"""
        def event_generator():
            try:
                # 获取流式响应
                for chunk in _education_system.stream_query(request.query):
                    # 发送文本块
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                # 发送结束信号
                yield "data: {\"done\": true}\n\n"
            except Exception as e:
                logger.error(f"流式查询处理失败: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    
    # 中止流式输出端点
    @app.post("/abort_stream")
    async def abort_stream(request: AbortRequest):
        """中止正在进行的流式输出"""
        try:
            if not _education_system:
                raise HTTPException(status_code=503, detail="系统未初始化")
            
            result = _education_system.abort_stream(request.request_id)
            if result.get("success"):
                return JSONResponse(content=result)
            else:
                raise HTTPException(status_code=400, detail=result.get("error", "中止失败"))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"中止流式输出失败: {e}")
            raise HTTPException(status_code=500, detail=f"中止处理失败: {str(e)}")
    
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