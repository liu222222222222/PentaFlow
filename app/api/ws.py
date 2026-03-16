from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
from datetime import datetime


router = APIRouter()

# WebSocket 连接管理
active_connections: Dict[str, WebSocket] = {}


@router.websocket("/ws/analysis/{task_id}")
async def websocket_analysis_endpoint(websocket: WebSocket, task_id: str):
    """用于实时分析进度的WebSocket端点"""
    await websocket.accept()
    
    # 存储连接
    active_connections[task_id] = websocket
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            # 在实际应用中，可以处理来自客户端的指令
            # 比如请求最新进度、取消任务等
            
            # 发送响应
            await websocket.send_text(json.dumps({
                "type": "echo",
                "message": f"Received: {data}",
                "task_id": task_id
            }))
    except WebSocketDisconnect:
        # 从活动连接中移除
        if task_id in active_connections:
            del active_connections[task_id]
    except Exception as e:
        print(f"WebSocket error for task {task_id}: {e}")
        if task_id in active_connections:
            del active_connections[task_id]


async def broadcast_to_task(task_id: str, message: Dict):
    """向特定任务的WebSocket连接广播消息"""
    if task_id in active_connections:
        try:
            await active_connections[task_id].send_text(json.dumps(message))
            return True
        except Exception as e:
            print(f"Broadcast error for task {task_id}: {e}")
            # 移除失效连接
            del active_connections[task_id]
            return False
    return False