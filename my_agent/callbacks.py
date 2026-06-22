"""ADK 回调演示：观察与轻度控制 Agent 行为。

ADK 在 Agent / Model / Tool 三个层面各提供一对回调，总计 6 种：

  Agent  生命周期：before_agent_callback / after_agent_callback
  Model  LLM 调用：before_model_callback  / after_model_callback
  Tool   工具执行：before_tool_callback   / after_tool_callback

回调的作用：
- 观测：在关键节点打印日志、写入会话状态。
- 控制：返回非 None 值会短路后续步骤（Agent/Model/Tool 直接采用返回值）。

注意：回调的 **参数名必须与 ADK 约定一致**，ADK 通过关键字参数注入。
- Agent / Model 回调使用 `callback_context`。
- Tool 回调使用 `tool`、`args`、`tool_context`。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types


# ---------------------------------------------------------------------------
# Agent 生命周期：进入/退出 Agent 时触发
# ---------------------------------------------------------------------------

def log_agent_entry(callback_context: CallbackContext) -> Optional[genai_types.Content]:
    """Agent 开始工作前：打印身份、初始化该 Agent 专属的 state 段。"""
    agent_name = callback_context.agent_name
    print(f"\n[before_agent] ▶ {agent_name} 即将处理本轮请求")

    # 用 state 做轻量"埋点"：每个 Agent 维护自己的调用次数。
    counter_key = f"agent_calls:{agent_name}"
    current = callback_context.state.get(counter_key, 0)
    callback_context.state[counter_key] = current + 1

    # 返回 None 表示放行，让 Agent 继续执行。
    return None


def log_agent_exit(callback_context: CallbackContext) -> Optional[genai_types.Content]:
    """Agent 完成工作后：打印结束信息，可用于审计 / 计时。"""
    agent_name = callback_context.agent_name
    counter = callback_context.state.get(f"agent_calls:{agent_name}", 0)
    print(f"[after_agent]  ◀ {agent_name} 本次请求结束，累计调用 {counter} 次")
    return None


# ---------------------------------------------------------------------------
# LLM 交互：发送请求/收到响应时触发
# ---------------------------------------------------------------------------

def log_model_request(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """LLM 请求前：打印模型名与本轮消息数。"""
    model = getattr(llm_request, "model", "unknown")
    contents = getattr(llm_request, "contents", []) or []
    print(f"  [before_model] → {model} 携带 {len(contents)} 条消息")
    return None


def log_model_response(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """LLM 响应后：粗略打印是否包含工具调用。"""
    content = getattr(llm_response, "content", None)
    parts = getattr(content, "parts", []) if content else []
    has_tool_call = any(getattr(p, "function_call", None) for p in parts)
    print(f"  [after_model]  ← {'触发工具调用' if has_tool_call else '纯文本回复'}")
    return None


# ---------------------------------------------------------------------------
# 工具执行：调用工具前后触发
# ---------------------------------------------------------------------------

def log_tool_call(
    tool: Any, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict[str, Any]]:
    """工具执行前：打印工具名与入参摘要。"""
    tool_name = getattr(tool, "name", getattr(tool, "__name__", str(tool)))
    print(f"    [before_tool] ⚙ {tool_name}({args})")
    return None


def log_tool_result(
    tool: Any,
    args: Dict[str, Any],
    tool_context: ToolContext,
    tool_response: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """工具执行后：打印结果状态，便于排查"工具到底返回了什么"。"""
    tool_name = getattr(tool, "name", getattr(tool, "__name__", str(tool)))
    status = (
        tool_response.get("status") if isinstance(tool_response, dict) else "n/a"
    )
    print(f"    [after_tool]  ✓ {tool_name} → status={status}")
    return None
