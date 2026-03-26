# 启动脚本 - app\run_server.py
import sys
import os
import uvicorn
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("启动 AI Impact Index V2 服务器...")
    logger.info("   地址: http://localhost:8000")
    logger.info("   API 文档: http://localhost:8000/docs")
    logger.info("   按 Ctrl+C 停止服务器")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )