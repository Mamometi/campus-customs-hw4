"""Environment + Portkey/model configuration (same setup as Lectures/11).

Loads .env from backend/ and every folder above it (nearest wins), so the
class-wide AI Foundations/.env with PORTKEY_API_KEY works without copying it.

The course Portkey account is itself the provider: requests carry only
x-portkey-api-key and name the model as `@integration-slug/model`
(e.g. @azure-openai-global/gpt-6-luna). gpt-6-luna needs the Responses API
for function tools.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

BACKEND_DIR = Path(__file__).resolve().parent
for folder in [BACKEND_DIR, *BACKEND_DIR.parents]:
    if (folder / ".env").exists():
        load_dotenv(folder / ".env", override=False)

ASSISTANT_NAME = "Handsome Dan"
# Course budget assumes luna. Override with MODEL_NAME in .env.
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")
PORTKEY_PROVIDER = os.getenv("PORTKEY_PROVIDER", "@azure-openai-global").rstrip("/")

# How many past chat messages (user + assistant) are sent to the model as context.
HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "20"))

# Per-message agent limits (P12): stop runaway tool loops and cost.
AGENT_REQUEST_LIMIT = int(os.getenv("AGENT_REQUEST_LIMIT", "8"))      # model calls per message
AGENT_TOOL_CALLS_LIMIT = int(os.getenv("AGENT_TOOL_CALLS_LIMIT", "10"))  # tool executions per message
AGENT_TOTAL_TOKENS_LIMIT = int(os.getenv("AGENT_TOTAL_TOKENS_LIMIT", "150000"))


def _portkey_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    return "" if key.startswith("your-") else key  # .env.example placeholder counts as unset


def api_key_set() -> bool:
    return bool(_portkey_key())


def require_api_key() -> str:
    key = _portkey_key()
    if not key:
        raise RuntimeError(
            "PORTKEY_API_KEY is missing. Put it in hw4/.env (copy .env.example)."
        )
    return key


_models: dict[tuple[str, int], object] = {}


def build_model(model_name: str = MODEL_NAME):
    """One model/HTTP client per event loop (an AsyncOpenAI client can't be
    reused across loops, e.g. separate test clients or worker restarts)."""
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = 0
    key = (model_name, loop_id)
    if key not in _models:
        _models[key] = _build_model(model_name)
    return _models[key]


def _build_model(model_name: str):
    # Imported lazily so the storefront API still starts without the openai extras.
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    key = require_api_key()
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key},
        timeout=120,
        max_retries=1,
    )
    routed = f"{PORTKEY_PROVIDER}/{model_name}" if PORTKEY_PROVIDER else model_name
    return OpenAIResponsesModel(routed, provider=OpenAIProvider(openai_client=client))
