import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent, ParallelAgent, SequentialAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool

# 关键：导入 LiteLLM 适配器
from google.adk.models.lite_llm import LiteLlm

MODEL = LiteLlm(
    model="openai/doubao-seed-2-0-mini-260215",
    # 关闭深度思考，避免每次回复都先吐一大段 thought
    # 豆包 OpenAI 兼容接口支持 thinking.type=disabled
    extra_body={"thinking": {"type": "disabled"}},
)


# ---------- 工具函数 ----------
def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city."""
    if city.lower() in ["beijing", "北京"]:
        return {
            "status": "success",
            "report": "北京今天天气晴朗，温度25摄氏度（77华氏度）。",
        }
    return {"status": "error", "error_message": f"抱歉，我没有'{city}'的天气信息。"}


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    if city.lower() in ["beijing", "北京"]:
        tz_identifier = "Asia/Shanghai"
    else:
        return {"status": "error", "error_message": f"抱歉，我没有{city}的时区信息。"}

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = f'{city}的当前时间是 {now.strftime("%Y年%m月%d日 %H:%M:%S %Z%z")}'
    return {"status": "success", "report": report}


# ---------- 子 Agent：天气专家 ----------
weather_agent = Agent(
    name="weather_agent",
    model=MODEL,
    description="专门回答城市天气问题",
    instruction="你是一个天气助手，只能回答天气相关问题，用中文回复。",
    tools=[get_weather],
)


# # ---------- 子 Agent：时间专家 ----------
time_agent = Agent(
    name="time_agent",
    model=MODEL,
    description="专门回答城市时间问题",
    instruction="你是一个时间助手，只能回答时间相关问题，用中文回复。",
    tools=[get_current_time],
)


# # ---------- 根 Agent：分发到子 Agent ----------
# # 模式 1：sub_agents 自动委派（LLM 根据子 agent 的 description 决定路由）
# root_agent = Agent(
#     name="dispatcher",
#     model=MODEL,
#     description="总调度：根据用户问题分发给天气或时间专家",
#     instruction=(
#         "你是总调度。当用户问天气就交给 weather_agent，问时间就交给 time_agent。"
#         "如果都不是，就自己用中文简短回答。"
#     ),
#     sub_agents=[weather_agent, time_agent],
# )


# ---------- 模式 3：ParallelAgent（并行执行 + 汇总） ----------

# 并行节点：天气和时间同时跑
parallel_node = ParallelAgent(
    name="parallel_weather_time",
    sub_agents=[weather_agent, time_agent],
)

# 汇总节点：拿到两份结果后合成最终回复
summarizer_agent = Agent(
    name="summarizer",
    model=MODEL,
    description="把天气和时间结果汇总成一条友好回复",
    instruction=(
        "你会收到天气和时间的查询结果（可能只有其中一个）。"
        "请用中文把它们整理成一条自然、简洁的回复。不要重复执行工具。"
    ),
)

# 根 Agent：先并行收集，再汇总
root_agent = SequentialAgent(
    name="weather_time_pipeline",
    sub_agents=[parallel_node, summarizer_agent],
)
