# py-adk

基于 Google ADK (Agent Development Kit) 的 Python 示例项目。它把官方 get-started / quickstart 里的核心概念落到一个清晰的小工程里：`root_agent`、函数工具、子 Agent 委派、`.env` 配置、LiteLLM 模型适配，以及 CLI/Web/API 三种运行方式。

## 代码结构

```text
py-adk/
|-- main.py                 # FastAPI 包装入口
|-- requirements.txt        # 项目依赖
`-- my_agent/
    |-- .env.example        # ADK 会从 agent 包目录加载 .env
    |-- __init__.py         # 让 my_agent 成为可导入包
    |-- agent.py            # ADK 发现入口，必须暴露 root_agent
    |-- callbacks.py        # 6 类回调：agent / model / tool × before / after
    |-- config.py           # 模型与运行配置（LiteLlm）
    |-- prompts.py          # Agent 指令集中管理（支持 {state_key} 模板）
    |-- runner.py           # InMemoryRunner 程序化调用 demo
    `-- tools.py            # 函数工具、ToolContext 写状态、LongRunningFunctionTool
```

## ADK 知识点对照

下表标注了本项目覆盖的 ADK 特性及其在代码中的位置。

| ADK 特性 | 作用 | 在本项目的位置 |
| --- | --- | --- |
| `LlmAgent` (即 `Agent`) | 由 LLM 驱动的 Agent | [agent.py](my_agent/agent.py) 中 4 个 `Agent(...)` |
| `sub_agents` | 父 Agent 通过 description 委派给子 Agent | `root_agent.sub_agents=[weather_agent, time_agent]` |
| `AgentTool` | 把 Agent 当作"工具"显式调用 | `travel_pipeline_tool = AgentTool(agent=travel_pipeline)` |
| `SequentialAgent` | 顺序执行子 Agent 的工作流 Agent | `travel_pipeline` |
| `output_key` | 把 Agent 最终回复写入 `session.state` | `weather_agent.output_key="weather_info"` 等 |
| instruction 模板 `{key}` | 从 `session.state` 读上游 Agent 的结果 | `ROOT_INSTRUCTION` 中的 `{weather_info}` / `{time_info}` |
| `ToolContext` | 工具内部读写 `session.state` | `remember_user_preference(tool_context)` |
| `LongRunningFunctionTool` | 标记长耗时工具，调用方需异步等待 | `long_running_forecast` |
| 6 类回调 | Agent/Model/Tool × before/after | [callbacks.py](my_agent/callbacks.py) 全部 6 个函数 |
| `InMemoryRunner` | 脱离 CLI/Web 的程序化运行入口 | [runner.py](my_agent/runner.py) |
| `LiteLlm` | 通过 OpenAI 兼容协议接入各类 LLM | [config.py](my_agent/config.py) |
| `get_fast_api_app` | ADK 自带的 FastAPI 包装 | [main.py](main.py) |

## 环境准备

ADK 2.3.0 要求 Python 3.10+。当前仓库里的 `.venv` 指向的 Python 3.12 已失效，建议重建虚拟环境。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`LiteLlm` 走的是 `google-adk[extensions]` extras；如果只装了基础包会提示 `LiteLLM support requires: pip install google-adk[extensions]`。

Windows 终端如果中文输出乱码，先打开 UTF-8：

```powershell
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## 配置模型

复制环境变量模板：

```powershell
Copy-Item my_agent\.env.example my_agent\.env
```

编辑 `my_agent/.env`：

```env
OPENAI_API_KEY=你的 ARK API Key
OPENAI_API_BASE=https://ark.cn-beijing.volces.com/api/v3
ADK_MODEL=openai/doubao-seed-2-0-mini-260215
```

`config.py` 里默认关闭豆包深度思考输出：

```python
extra_body={"thinking": {"type": "disabled"}}
```

## 运行方式

命令行单轮或交互调试：

```powershell
adk run my_agent
adk run my_agent "北京现在天气和时间怎样？"
```

启动 ADK Web UI：

```powershell
adk web --port 8000 .
```

浏览器访问 `http://127.0.0.1:8000`，选择 `my_agent`。

启动本项目的 FastAPI 包装入口：

```powershell
uvicorn main:app --port 8000
```

也可以直接使用 ADK 官方 API server：

```powershell
adk api_server --port 8000 .
```

用 `InMemoryRunner` 程序化跑一遍（无需启动 Web/CLI，适合脚本和测试）：

```powershell
python -m my_agent.runner
python -m my_agent.runner "请给我一份上海出行建议"
```

## 运行时会看到什么

`InMemoryRunner` 与 `adk run` / `adk web` 共享同一份 Agent 定义，因此会话开始时 6 类回调会按以下顺序打印日志：

```text
[before_agent] ▶ weather_time_assistant 即将处理本轮请求
  [before_model] → openai/doubao-seed-2-0-mini-260215 携带 1 条消息
  [after_model]  ← 触发工具调用
    [before_tool] ⚙ remember_user_preference(...)
    [after_tool]  ✓ remember_user_preference → status=success
  [before_model] → ... 携带 3 条消息
  [after_model]  ← 触发工具调用
    [before_tool] ⚙ travel_pipeline(...)
      [before_agent] ▶ travel_pipeline ...
        ...
      [after_agent]  ◀ travel_pipeline ...
    [after_tool]  ✓ travel_pipeline → status=success
  [after_model]  ← 纯文本回复
[after_agent]  ◀ weather_time_assistant 本次请求结束，累计调用 1 次
```

`--- session.state ---` 段会显示 `weather_info` / `time_info` / `city_report` / `celsius_temperature` / `travel_tip` / `final_answer` 等 key 的实际值，可用来验证 `output_key` 与 `{key}` 模板是否生效。

## 扩展方式

- 新增工具时，把纯函数放到 `my_agent/tools.py`，给参数写类型和 docstring；需要写状态时加 `tool_context: ToolContext`；长耗时工具用 `LongRunningFunctionTool` 包装。
- 新增子 Agent 时，在 `agent.py` 里创建新的 `Agent` 实例并 `output_key=...`；如果需要流水线就挂到 `SequentialAgent.sub_agents`；如果希望 LLM 显式调用，就用 `AgentTool` 包一下挂到父 Agent 的 `tools`。
- 观测或埋点时，把回调函数注册到 Agent 的 `before_/after_` 槽位，常量模板保持简单。
- 想要自定义运行入口（脚本、CI、单测）就用 `InMemoryRunner` 跑 `run_async` 事件流。

## 常见问题

- `LLM Provider NOT provided`：模型名缺少 LiteLLM provider 前缀，使用 `openai/<model>`。
- `Missing credentials`：确认 `my_agent/.env` 存在，并且变量名是 `OPENAI_API_KEY` / `OPENAI_API_BASE`。
- `has not activated the model`：火山方舟控制台还没有开通对应模型。
- `LiteLLM support requires: pip install google-adk[extensions]`：LiteLlm 不在主包内，需要装 extras。
- `No Python at ... PythonSoftwareFoundation.Python.3.12 ...`：当前 `.venv` 指向的解释器不存在，删除并重建 `.venv`。
- Agent 报错 `Invalid argument` 且提到 `callback_context` / `tool_context`：回调的参数名拼错，ADK 走的是关键字注入，名字必须完全一致。
