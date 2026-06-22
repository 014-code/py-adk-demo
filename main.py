"""Optional FastAPI entrypoint for serving the ADK agent.

The official quickstart mainly uses `adk run` and `adk web`. This module is a
small wrapper for teams that want to mount the same agent package in their own
ASGI process.
"""

from __future__ import annotations

from pathlib import Path

from google.adk.cli.fast_api import get_fast_api_app

# ADK discovers agents from AGENTS_DIR. Passing the repository root lets it find
# the my_agent/ package, whose agent.py exposes the required root_agent object.
AGENTS_DIR = str(Path(__file__).resolve().parent)

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    session_service_uri="memory://",
    allow_origins=["*"],
    web=True,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)