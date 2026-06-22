"""Pure Python tools exposed to ADK agents.

ADK turns callables in an Agent's tools list into function tools. Keep the
signatures typed and docstrings direct because the model sees those names,
parameters, and descriptions when deciding how to call a tool.

本文件覆盖 4 种工具形态：
  1. 普通函数        → ADK 自动包成 FunctionTool
  2. ToolContext 参数 → 工具内部读写 session.state
  3. async 函数      → 仍按 FunctionTool 走（短任务）
  4. LongRunningFunctionTool 包装 → 显式告诉 ADK"这是个长任务，调用方应等待"
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from google.adk.tools import LongRunningFunctionTool
from google.adk.tools.tool_context import ToolContext

# ---------------------------------------------------------------------------
# 数据：本地 mock 的城市天气 / 时区
# ---------------------------------------------------------------------------

SUPPORTED_CITIES = {
    "beijing": {
        "display_name": "北京",
        "timezone": "Asia/Shanghai",
        "weather": "晴，气温 25 摄氏度，微风，适合通勤和户外活动。",
    },
    "北京": {
        "display_name": "北京",
        "timezone": "Asia/Shanghai",
        "weather": "晴，气温 25 摄氏度，微风，适合通勤和户外活动。",
    },
    "shanghai": {
        "display_name": "上海",
        "timezone": "Asia/Shanghai",
        "weather": "多云，气温 27 摄氏度，湿度偏高，建议带伞备用。",
    },
    "上海": {
        "display_name": "上海",
        "timezone": "Asia/Shanghai",
        "weather": "多云，气温 27 摄氏度，湿度偏高，建议带伞备用。",
    },
    "new york": {
        "display_name": "New York",
        "timezone": "America/New_York",
        "weather": "Sunny, 24 degrees Celsius, light wind.",
    },
    "纽约": {
        "display_name": "New York",
        "timezone": "America/New_York",
        "weather": "Sunny, 24 degrees Celsius, light wind.",
    },
}


def _lookup_city(city: str) -> Optional[Dict[str, str]]:
    cleaned_city = city.strip()
    return SUPPORTED_CITIES.get(cleaned_city.lower()) or SUPPORTED_CITIES.get(
        cleaned_city
    )


# ---------------------------------------------------------------------------
# 1) 普通 FunctionTool：天气 + 时间
# ---------------------------------------------------------------------------

def get_weather(city: str) -> dict:
    """Return a small weather report for a supported city."""
    city_info = _lookup_city(city)
    if city_info is None:
        return {
            "status": "error",
            "error_message": f"暂不支持查询 {city} 的天气。",
            "supported_cities": ["北京", "上海", "New York"],
        }

    return {
        "status": "success",
        "city": city_info["display_name"],
        "report": city_info["weather"],
    }


def get_current_time(city: str) -> dict:
    """Return the current local time for a supported city."""
    city_info = _lookup_city(city)
    if city_info is None:
        return {
            "status": "error",
            "error_message": f"暂不支持查询 {city} 的时区。",
            "supported_cities": ["北京", "上海", "New York"],
        }

    timezone = ZoneInfo(city_info["timezone"])
    now = datetime.now(timezone)
    return {
        "status": "success",
        "city": city_info["display_name"],
        "timezone": city_info["timezone"],
        "time": now.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
    }


# ---------------------------------------------------------------------------
# 2) ToolContext：把用户偏好写进 session.state，供后续指令模板使用
# ---------------------------------------------------------------------------

def remember_user_preference(
    key: str, value: str, tool_context: ToolContext
) -> dict:
    """Store a user preference (e.g. units=celsius, language=zh) in session state.

    `tool_context` 是 ADK 在调用工具时注入的关键字参数。
    通过 `tool_context.state` 写入的值，在同一 session 内可被任意 Agent
    通过指令模板 `{key}` 直接读取——这是 ADK 多 Agent 共享数据的核心机制。
    """
    if not key or not value:
        return {"status": "error", "error_message": "key 和 value 不能为空"}

    # state 自动会按 session prefix 写入，当前 Agent 写入的内容
    # 会覆盖到 session.state[key]，所有 Agent 都可见。
    tool_context.state[key] = value
    return {"status": "success", "stored": {key: value}}


# ---------------------------------------------------------------------------
# 3) LongRunningFunctionTool：模拟"耗时任务"，调用方需要异步等待结果
# ---------------------------------------------------------------------------

async def _fetch_weather_forecast_impl(city: str, days: int) -> dict:
    city_info = _lookup_city(city)
    if city_info is None:
        return {
            "status": "error",
            "error_message": f"暂不支持 {city} 的天气预报。",
        }
    days = max(1, min(days, 7))  # 上限 7 天
    # 模拟 IO 耗时
    await asyncio.sleep(0.5)
    return {
        "status": "success",
        "city": city_info["display_name"],
        "days": days,
        "forecast": [f"第 {i + 1} 天：晴转多云，{20 + i}℃" for i in range(days)],
    }


def fetch_weather_forecast(city: str, days: int = 3) -> dict:
    """Fetch a multi-day forecast for a supported city.

    ADK 用 LongRunningFunctionTool 包装后，会告诉 LLM：这个工具返回较慢，
    请在调用后让出执行权，外部会重新喂入结果。常用于真实 API、数据库、
    人机协作（Human-in-the-Loop）等场景。
    """
    # 同步入口里跑异步逻辑，演示用；真实工程可直接写 async def。
    return asyncio.run(_fetch_weather_forecast_impl(city, days))


# LongRunningFunctionTool 必须包装可调用对象；导出后供 agent.py 注册。
long_running_forecast = LongRunningFunctionTool(func=fetch_weather_forecast)


# ---------------------------------------------------------------------------
# 4) 简单计算工具：用于 SequentialAgent pipeline 的最后一步
# ---------------------------------------------------------------------------

def celsius_to_fahrenheit(celsius: float) -> dict:
    """Convert a temperature from Celsius to Fahrenheit."""
    return {
        "status": "success",
        "celsius": celsius,
        "fahrenheit": round(celsius * 9 / 5 + 32, 2),
    }
