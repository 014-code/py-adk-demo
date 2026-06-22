"""程序化运行 ADK Agent（脱离 adk run / adk web）。

知识点：Runner 是 ADK 的执行引擎。`adk run` 内部就是用 Runner
跑起来的；`InMemoryRunner` 把 SessionService 替换成内存版，
适合脚本、单元测试、CI 场景。

用法：
    python -m my_agent.runner
    python -m my_agent.runner "北京现在天气怎样？"
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from .agent import root_agent


APP_NAME = "py-adk-demo"


async def _run_once(user_text: str) -> str:
    """单轮对话：建一个临时 session，喂入用户输入，收集最终回复。"""
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id="demo-user", session_id=str(uuid.uuid4())
    )

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_text)],
    )

    final_text = ""
    # run_async 是异步事件流；最后一个 partial=False 的事件即最终回复。
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""

    # 同时把 session.state 也打出来，便于观察 output_key 的效果
    state = await runner.session_service.get_session(
        app_name=APP_NAME, user_id=session.user_id, session_id=session.id
    )
    print("\n--- session.state ---")
    for key, value in state.state.items():
        print(f"  {key}: {value}")
    return final_text


async def _main(user_text: str) -> None:
    print(f"\nUSER: {user_text}")
    reply = await _run_once(user_text)
    print(f"\nAGENT: {reply}\n")


def cli() -> None:
    parser = argparse.ArgumentParser(description="用 InMemoryRunner 跑一遍 root_agent")
    parser.add_argument(
        "query",
        nargs="?",
        default="北京现在天气和时间怎么样？给我一份出行建议。",
        help="用户输入",
    )
    args = parser.parse_args()
    asyncio.run(_main(args.query))


if __name__ == "__main__":
    cli()
