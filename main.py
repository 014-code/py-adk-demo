"""FastAPI 入口：暴露 ADK Agent 的对话接口

启动：
    uvicorn main:app --reload --port 8000

访问：
    http://localhost:8000/docs        Swagger UI（看接口、调试）
    http://localhost:8000/apps/...    对话接口
"""
import os
from google.adk.cli.fast_api import get_fast_api_app

# agents_dir：指向包含 my_agent/ 的目录（即当前目录）
# ADK 会扫描这个目录下所有形如 my_agent/agent.py 的子目录
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    session_db_url="",          # 空 = 用内存 session，重启会清空
                                # 想持久化可填 sqlite:///sessions.db
    allow_origins=["*"],        # 允许跨域，前端调用时改成具体域名
    web=True,                   # True = 同时在 / 提供 adk web UI
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
