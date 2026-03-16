"""WebSocket 管理器，用于处理任务特定的WebSocket连接"""
import json
from typing import Dict, Optional
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

# 用于存储任务特定的WebSocket连接
task_websockets: Dict[str, WebSocket] = {}


async def send_progress_update_to_task(task_id: str, update_data: Dict):
    """发送进度更新到特定任务的WebSocket连接"""
    global task_websockets
    
    if task_id in task_websockets:
        ws = task_websockets[task_id]
        try:
            await ws.send_text(json.dumps(update_data, ensure_ascii=False))
            logger.info(f"✅ 成功发送消息到任务 {task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 发送WebSocket消息失败 {task_id}: {e}")
            # 移除无效连接
            if task_id in task_websockets:
                del task_websockets[task_id]
            return False
    else:
        logger.warning(f"⚠️ 未找到任务 {task_id} 的WebSocket连接")
        return False


def register_task_websocket(task_id: str, websocket: WebSocket):
    """注册任务的WebSocket连接"""
    global task_websockets
    task_websockets[task_id] = websocket
    logger.info(f"✅ Task {task_id} registered to WebSocket connection")


def unregister_task_websocket(task_id: str):
    """取消注册任务的WebSocket连接"""
    global task_websockets
    if task_id in task_websockets:
        del task_websockets[task_id]
        logger.info(f"✅ Task {task_id} unregistered from WebSocket connection")


def get_task_websocket(task_id: str) -> Optional[WebSocket]:
    """获取任务的WebSocket连接"""
    return task_websockets.get(task_id)


def get_all_task_websockets():
    """获取所有任务WebSocket连接"""
    return task_websockets