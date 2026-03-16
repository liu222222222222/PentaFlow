# 启动脚本 - app\run_server.py
import sys
import os
import uvicorn

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app

if __name__ == "__main__":
    print("🚀 启动 AI Impact Index V2 服务器...")
    print("   地址: http://localhost:8000")
    print("   API 文档: http://localhost:8000/docs")
    print("   按 Ctrl+C 停止服务器")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )