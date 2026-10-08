"""Append-only audit trail of agent activity (P12).

One record per chat turn goes to output/audit_trail.json (a JSON array):
when it happened, who (guest / user id, never names or emails), what page,
a short redacted copy of the message, every tool call with short args and
results, the reply, usage, and why the agent stopped.

Appending is safe: a process-wide lock serializes writers, the file is read,
the record appended, and the result written to a temp file that atomically
replaces the original. Existing records are never dropped. If the file is
unreadable it's moved aside (audit_trail.corrupt-<time>.json), not overwritten.
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = Path(os.getenv("AUDIT_PATH") or ROOT / "output" / "audit_trail.json")

MAX_TEXT = 300     # user message / reply preview
MAX_RESULT = 400   # tool result preview
MAX_ARGS = 300

_lock = threading.Lock()

# ---------- Redaction: keep personal data out of the log ----------
_REDACTIONS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[card-number]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[ssn]"),
    (re.compile(r"(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b"), "[phone]"),
    (re.compile(r"(?i)(password|passcode|pwd)\s*[:=is]*\s*\S+"), r"\1 [redacted]"),
]


def redact(text: str) -> str:
    for pattern, repl in _REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def short(value: Any, limit: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    text = redact(text)
    return text if len(text) <= limit else text[:limit] + "…"


# ---------- Manipulation heuristics (flag only; the prompt decides how to respond) ----------
_INJECTION_PATTERNS = {
    "override_instructions": r"\b(ignore|disregard|forget|override)\b.{0,40}\b(instructions|rules|prompt|guidelines)\b",
    "prompt_extraction": r"\b(system prompt|your (instructions|prompt|rules)|reveal .{0,20}prompt|repeat .{0,20}above)\b",
    "role_hijack": r"\b(you are now|act as|pretend (to be|you are)|developer mode|jailbreak|DAN mode)\b",
    "fake_authority": r"\b(i am|i'm) (the|a|an) (admin|administrator|developer|owner|manager)\b|\badmin (mode|override)\b",
    "discount_fishing": r"\b(free|100% off|discount code|coupon|promo code|price match|give me .{0,15} for free)\b",
    "other_customer_data": r"\b(other (customers|users)|another (customer|user)|(last|previous|that) (customer|user|buyer)|someone else'?s|list (all )?(users|customers|emails)|who (bought|ordered))\b",
    "secrets": r"\b(api key|portkey|secret key|password hash|database (file|dump)|\.env)\b",
}
_WELLBEING = r"\b(kill myself|suicid|self[- ]harm|hurt myself|want to die|end my life)\b"


def safety_flags(message: str) -> list[str]:
    text = message.lower()
    flags = [name for name, pat in _INJECTION_PATTERNS.items() if re.search(pat, text, re.I)]
    if re.search(_WELLBEING, text, re.I):
        flags.append("wellbeing_concern")
    if redact(message) != message:
        flags.append("sensitive_data_shared")  # email/card/phone/password in the message (redacted in the log)
    return flags


# ---------- Building and writing records ----------
def summarize_tool_calls(messages: list) -> list[dict]:
    """Pair each ToolCallPart with its ToolReturnPart from a PydanticAI run."""
    calls: dict[str, dict] = {}
    for msg in messages:
        for part in getattr(msg, "parts", []):
            kind = type(part).__name__
            if kind == "ToolCallPart" and part.tool_name != "final_result":
                args = part.args_as_dict() if hasattr(part, "args_as_dict") else part.args
                calls[part.tool_call_id] = {"tool": part.tool_name, "args": short(args, MAX_ARGS), "result": None, "ok": None}
            elif kind in ("ToolReturnPart", "RetryPromptPart") and getattr(part, "tool_call_id", None) in calls:
                entry = calls[part.tool_call_id]
                content = getattr(part, "content", "")
                if hasattr(content, "model_dump"):
                    content = content.model_dump()
                entry["result"] = short(content, MAX_RESULT)
                entry["ok"] = kind == "ToolReturnPart" and not (isinstance(content, dict) and "error" in content)
    return list(calls.values())


def new_record(*, actor: str, page_path: str, message: str, model: str) -> dict:
    return {
        "id": uuid.uuid4().hex[:12],
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "actor": actor,                     # "guest" or "user:<id>" (no names/emails)
        "page": page_path[:200],
        "model": model,
        "user_message": short(message, MAX_TEXT),
        "safety_flags": safety_flags(message),
    }


def append(record: dict) -> None:
    """Append one record to the audit trail without ever discarding earlier ones."""
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        records: list = []
        if AUDIT_PATH.exists():
            try:
                records = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
                if not isinstance(records, list):
                    raise ValueError("audit trail is not a JSON array")
            except (json.JSONDecodeError, ValueError):
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                AUDIT_PATH.replace(AUDIT_PATH.with_name(f"audit_trail.corrupt-{stamp}.json"))
                records = []
        records.append(record)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)
