# py-adk

基于 [Google ADK (Agent Development Kit)](https://github.com/google/adk-python) 的多 Agent 示例项目，使用豆包大模型（火山方舟 ARK OpenAI 兼容接口），通过 LiteLLM 适配接入，并暴露 FastAPI HTTP 接口。

## 功能

- 单 Agent + 多个工具的极简对话模式
- 多 Agent 协作：`sub_agents` 自动委派 / `AgentTool` 工具包装 / `ParallelAgent` 并行 + `SequentialAgent` 汇总
- 通过 FastAPI 暴露对话接口，支持 SSE 流式输出

## 目录结构

```
py-adk/
├── main.py                 # FastAPI 入口
├── my_agent/
│   ├── .env.example        # 环境变量模板
│   ├── __init__.py
│   └── agent.py            # Agent 与工具函数定义
└── .venv/                  # Python 虚拟环境
```

## 环境准备

### 1. 创建并激活虚拟环境

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```powershell
pip install google-adk litellm fastapi uvicorn
```

### 3. 配置环境变量

```powershell
Copy-Item my_agent\.env.example my_agent\.env
```

编辑 `my_agent/.env`，填入真实值：

```env
OPENAI_API_KEY=<你的 ARK API Key>
OPENAI_API_BASE=https://ark.cn-beijing.volces.com/api/v3
```

> **注意**：在火山方舟控制台需要先「开通」模型 `doubao-seed-2-0-mini-260215`，否则会报 `has not activated the model` 错误。

## 运行

### 方式一：ADK 内置 Web UI

```powershell
adk web my_agent
```

访问 `http://localhost:8000` 使用图形界面。

### 方式二：FastAPI

```powershell
uvicorn main:app --reload --port 8000
```

- Swagger 文档：`http://localhost:8000/docs`
- 对话接口：`POST /apps/{agent_name}/users/{user_id}/sessions/{session_id}/messages`

## 多 Agent 模式

`my_agent/agent.py` 中展示了三种多 Agent 模式，按需启用：

| 模式 | 写法 | 适用场景 |
|---|---|---|
| `sub_agents` 自动委派 | `sub_agents=[a, b]` | 简单路由，单一职责分发 |
| `AgentTool` 工具包装 | `tools=[AgentTool(a), AgentTool(b)]` | 保留子 Agent 独立配置，根 Agent 整合 |
| `ParallelAgent` + `SequentialAgent` | 套两层工作流 | 强制并行 + 显式汇总节点 |

切换方式：注释/取消注释文件中对应 `root_agent` 定义，最后一个生效。

## 关键配置说明

### 关闭深度思考

豆包 `doubao-seed-2-0-mini` 默认开启 CoT，会先输出一长段 `thought`。在 `LiteLlm` 构造时关闭：

```python
MODEL = LiteLlm(
    model="openai/doubao-seed-2-0-mini-260215",
    extra_body={"thinking": {"type": "disabled"}},
)
```

### LiteLLM 模型名前缀

- `openai/<model>`：走 OpenAI 兼容接口（推荐用于 ARK）
- `volcengine/<model>`：走火山引擎原生 endpoint
- `doubao/<model>`：旧版前缀，部分版本已弃用

## API 调用示例

创建会话：

```bash
curl -X POST http://localhost:8000/apps/weather_time_pipeline/users/u1/sessions/s1
```

发送消息（SSE 流式）：

```bash
curl -X POST http://localhost:8000/apps/weather_time_pipeline/users/u1/sessions/s1:run \
  -H "Content-Type: application/json" \
  -d '{
    "new_message": {
      "role": "user",
      "parts": [{"text": "北京天气"}]
    }
  }'
```

## 常见问题

**Q: 报 `LLM Provider NOT provided`？**
A: 模型名用了 LiteLLM 不识别的前缀。改用 `openai/<model>`。

**Q: 报 `Missing credentials`？**
A: `.env` 没读到，或变量名不是 `OPENAI_API_KEY`。

**Q: 报 `has not activated the model`？**
A: ARK 控制台没开通该模型，先去「模型市场」开通。

**Q: 回复里有一大段 `thought`？**
A: 模型开启了深度思考，按上面"关闭深度思考"小节配置。
