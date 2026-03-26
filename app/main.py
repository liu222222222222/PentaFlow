from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import logging
from datetime import datetime
import json
import sys
import os
# 添加项目根路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.api.v1.events import router as events_router
from app.api.v1.analysis import router as analysis_router
from config import settings


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Impact Index - 多智能体沙盘推演系统 V2"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(events_router, prefix="/api/v1", tags=["events"])
app.include_router(analysis_router, prefix="/api/v1", tags=["analysis"])

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# 添加根路径访问新的 React 前端
@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "frontend", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
            # 修复路径，将 ./ 替换为 /static/frontend/
            content = content.replace('href="./', 'href="/static/frontend/')
            content = content.replace('src="./', 'src="/static/frontend/')
            return content
    # 如果 React 构建文件不存在，回退到旧版
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

# 添加 timeline.html 访问路径
@app.get("/timeline.html", response_class=HTMLResponse)
async def read_timeline():
    timeline_path = os.path.join(os.path.dirname(__file__), "timeline.html")
    with open(timeline_path, "r", encoding="utf-8") as f:
        return f.read()

# 添加旧版 index.html 访问路径
@app.get("/legacy", response_class=HTMLResponse)
async def read_legacy_index():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

# Websocket 连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket 连接断开，当前连接数: {len(self.active_connections)}")
        else:
            logger.warning(f"尝试断开不存在的WebSocket连接")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # 如果发送失败，移除连接
                self.disconnect(connection)

manager = ConnectionManager()

from app.services.websocket_service import register_task_websocket, unregister_task_websocket

# WebSocket 端点用于实时进度推送
@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    task_id = None
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # 保持连接，等待客户端消息（或仅用于发送服务器消息）
            data = await websocket.receive_text()
            logger.info(f"WebSocket received: {data}")
            
            # 尝试解析客户端发送的任务ID注册消息
            try:
                message_data = json.loads(data)
                if message_data.get("type") == "register_task" and "task_id" in message_data:
                    task_id = message_data["task_id"]
                    register_task_websocket(task_id, websocket)
                    logger.info(f"✅ Task {task_id} registered to WebSocket connection")
                    
                    # 发送确认消息
                    await websocket.send_text(
                        json.dumps({"type": "task_registered", "task_id": task_id}, ensure_ascii=False)
                    )
                    logger.info(f"✅ Confirmation sent for task {task_id}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                # 如果不是JSON消息，忽略
                pass
    except WebSocketDisconnect:
        logger.info("WebSocket disconnecting...")
        if task_id:
            unregister_task_websocket(task_id)
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected and cleaned up")

# 全局推演引擎实例 - 延迟初始化
simulation_engine = None

@app.on_event("startup")
async def startup_event():
    logger.info("应用启动")
    # 初始化推演引擎
    from app.services.analysis_service import SimulationEngine
    global simulation_engine
    simulation_engine = SimulationEngine()
    await simulation_engine.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("应用关闭")
    # 清理资源
    for connection in manager.active_connections[:]:
        manager.disconnect(connection)

@app.get("/index.html", response_class=HTMLResponse)
async def get_index():
    """返回 index.html 的内容"""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version
    }