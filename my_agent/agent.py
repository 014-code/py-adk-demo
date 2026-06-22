"""ADK 发现入口。

官方 quickstart 约定每个 Agent 包暴露一个名为 `root_agent` 的对象。
ADK CLI、Web UI 和 FastAPI 包装器都会从这里加载根 Agent。

本文件用到的 ADK 知识点（自上而下）：
  - LlmAgent (Agent) + sub_agents            多 Agent 委派
  - AgentTool                                把 Agent 当工具显式调用
  - SequentialAgent                          工作流 Agent（顺序流水线）
  - output_key                               把 Agent 输出写入 session.state
  - instruction 里的 {key} 占位符             从 state 读取上游结果
  - 6 类回调                                 agent/model/tool × before/after
"""

from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import AgentTool

from .callbacks import (
    log_agent_entry,
    log_agent_exit,
    log_model_request,
    log_model_response,
    log_tool_call,
    log_tool_result,
)
from .config import MODEL
from .prompts import (
    CITY_REPORT_INSTRUCTION,
    ROOT_INSTRUCTION,
    TIME_INSTRUCTION,
    TRAVEL_TIP_INSTRUCTION,
    WEATHER_INSTRUCTION,
)
from .tools import (
    celsius_to_fahrenheit,
    get_current_time,
    get_weather,
    long_running_forecast,
    remember_user_preference,
)

# ---------------------------------------------------------------------------
# 1) 业务子 Agent：天气 / 时间
#    - output_key: 把"最终回复文本"写进 session.state，供根 Agent 模板读取
#    - 回调链：观测 Agent / Model / Tool 三个层面
# ---------------------------------------------------------------------------

weather_agent = Agent(
    name="weather_agent",
    model=MODEL,
    description="查询城市天气，并返回简洁中文天气摘要。",
    instruction=WEATHER_INSTRUCTION,
    tools=[get_weather],
    output_key="weather_info",
    # Agent 生命周期
    before_agent_callback=log_agent_entry,
    after_agent_callback=log_agent_exit,
    # LLM 交互
    before_model_callback=log_model_request,
    after_model_callback=log_model_response,
    # 工具执行
    before_tool_callback=log_tool_call,
    after_tool_callback=log_tool_result,
)

time_agent = Agent(
    name="time_agent",
    model=MODEL,
    description="查询城市当前时间，并说明其 IANA 时区。",
    instruction=TIME_INSTRUCTION,
    tools=[get_current_time],
    output_key="time_info",
    before_agent_callback=log_agent_entry,
    after_agent_callback=log_agent_exit,
    before_model_callback=log_model_request,
    after_model_callback=log_model_response,
    before_tool_callback=log_tool_call,
    after_tool_callback=log_tool_result,
)

# ---------------------------------------------------------------------------
# 2) SequentialAgent：演示"工作流 Agent"模式
#
# 工作流 Agent 本身不调用 LLM，仅按固定顺序调度子 Agent。
# 子 Agent 通过 output_key 写入 state，下游通过 {key} 模板读取——这是
# ADK 多 Agent 流水线（Pipeline）的标准做法。
# ---------------------------------------------------------------------------

city_report_agent = Agent(
    name="city_report_agent",
    model=MODEL,
    description="生成简短的城市报告（天气+时间）。",
    instruction=CITY_REPORT_INSTRUCTION,
    tools=[get_weather, get_current_time],
    output_key="city_report",
)

convert_agent = Agent(
    name="convert_agent",
    model=MODEL,
    description="从城市报告里抽取一个温度数值，调用工具转华氏度。",
    instruction="从以下城市报告里读出摄氏温度数字（整数或小数），"
                "然后调用 celsius_to_fahrenheit 工具换算。\n\n"
                "城市报告：{city_report}",
    tools=[celsius_to_fahrenheit],
    output_key="celsius_temperature",
)

travel_tip_agent = Agent(
    name="travel_tip_agent",
    model=MODEL,
    description="基于城市报告与温度给出出行建议。",
    instruction=TRAVEL_TIP_INSTRUCTION,
    output_key="travel_tip",
)

travel_pipeline = SequentialAgent(
    name="travel_pipeline",
    description="城市报告 → 温度换算 → 出行建议 三步流水线。",
    sub_agents=[city_report_agent, convert_agent, travel_tip_agent],
)

# ---------------------------------------------------------------------------
# 3) AgentTool：把 Agent 显式暴露为"工具"
#
# 与 sub_agents 的差异：
#   - sub_agents  -> LLM 通过子 Agent 的 description 自动选人（隐式委派）
#   - AgentTool   -> LLM 主动把 Agent 当成普通工具调用（显式调用）
# 适合：让 LLM 显式选择"我需要一份完整出行方案"这种场景。
# ---------------------------------------------------------------------------

travel_pipeline_tool = AgentTool(agent=travel_pipeline)

# ---------------------------------------------------------------------------
# 4) 根 Agent：协调天气/时间子 Agent + 可选调用 travel_pipeline
# ---------------------------------------------------------------------------

root_agent = Agent(
    name="weather_time_assistant",
    model=MODEL,
    description="按用户意图调度天气和时间专家，并汇总为自然中文回答。",
    instruction=ROOT_INSTRUCTION,
    sub_agents=[weather_agent, time_agent],
    tools=[remember_user_preference, long_running_forecast, travel_pipeline_tool],
    output_key="final_answer",
    before_agent_callback=log_agent_entry,
    after_agent_callback=log_agent_exit,
    before_model_callback=log_model_request,
    after_model_callback=log_model_response,
    before_tool_callback=log_tool_call,
    after_tool_callback=log_tool_result,
)
