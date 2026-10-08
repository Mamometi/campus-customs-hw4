"""PydanticAI agent for the Campus Customs chatbot.

run_chat(message, history, user) -> ChatResponse is what main.py's /api/chat calls.
Model/Portkey setup lives in config.py, tools in tools.py, the persona in
prompts/prompt.md, and request/response shapes in models.py.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from pydantic_ai.usage import UsageLimits
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

import audit
import config
import db
import tools
from models import (
    AgentReply,
    CatalogOverview,
    ChatResponse,
    ChatTurn,
    CustomerProfile,
    PageContext,
    PageResults,
    ProductDetails,
    SearchFilters,
    SearchResult,
    StockReport,
    ToolError,
)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"
MAX_PRODUCT_CARDS = 6      # highlighted cards inside the chat bubble
MAX_PAGE_RESULTS = 60      # cards shown on the page for one chat search
MAX_MODEL_RESULTS = 20     # products the model itself sees per search call


@dataclass
class ChatDeps:
    # Who is chatting: a CustomerProfile when logged in, None for guests.
    customer: CustomerProfile | None = None
    # Where they are on the site, and the product on that page (validated DB row).
    page_path: str = "/"
    current_product: dict | None = None
    # Filled by the search tools during a run: every search's filters and the
    # FULL ordered list of matching product_ids (not just what the model saw).
    searches: list[SearchFilters] = field(default_factory=list)
    search_result_ids: list[str] = field(default_factory=list)

    def record_search(self, filters: SearchFilters, ids: list[str]) -> None:
        self.searches.append(filters)
        for pid in ids:
            if pid not in self.search_result_ids:
                self.search_result_ids.append(pid)


agent = Agent(
    deps_type=ChatDeps,
    output_type=AgentReply,
    name="campus_customs_assistant",
    defer_model_check=True,
)


@agent.instructions
def _system_prompt() -> str:
    # Read on every run so edits to prompts/prompt.md apply without a
    # restart (uvicorn --reload only watches .py files).
    return PROMPT_PATH.read_text(encoding="utf-8")


@agent.instructions
def _session_context(ctx: RunContext[ChatDeps]) -> str:
    """Per-message context: who the customer is and what page they're on."""
    d = ctx.deps
    lines = ["## Session context (from the website, trustworthy)", f"- Today: {date.today():%A, %B %d, %Y}"]

    if d.customer:
        c = d.customer
        lines += [
            f"- Customer: logged in as {c.first_name} {c.last_name} <{c.email}>, member since {c.member_since[:10]}.",
            (
                f"- Returning customer: {c.past_messages} earlier chat messages, last chat {c.last_chat_at[:16]} UTC. "
                "Earlier turns are in the conversation history."
                if c.past_messages and c.last_chat_at
                else "- First chat with this customer."
            ),
        ]
    else:
        lines.append("- Customer: guest (not logged in). Nothing is saved after they leave; don't ask for their name or email.")

    lines.append(f"- Current page: {d.page_path}")
    p = d.current_product
    if p:
        in_stock = [i["size"] for i in p["inventory"] if i["quantity"] > 0]
        sold_out = [i["size"] for i in p["inventory"] if i["quantity"] == 0]
        lines += [
            f"- The customer is viewing the product page for **{p['name']}** (product_id `{p['product_id']}`).",
            f"  - {p['garment_type']}, ${p['price']:g}. Colors on item: {', '.join(p['colors']) or 'not listed'}.",
            f"  - Description: {p['description']}",
            f"  - In stock: {', '.join(in_stock) or 'none'}; sold out: {', '.join(sold_out) or 'none'} (snapshot; use check_stock for exact numbers).",
        ]
    return "\n".join(lines)


@agent.tool
def search_products(
    ctx: RunContext[ChatDeps],
    query: str = "",
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    size: str | None = None,
    color: str | None = None,
    sort: tools.SortKey = "relevance",
    limit: int = 8,
) -> SearchResult:
    """Search the catalogue by keywords and filters. Returns price, description, colors and per-size stock for each match.

    Use for "do you have…", "show me…", "what's the cheapest…", or any request that names a kind of item.

    Args:
        query: Keywords, e.g. "hoodie", "Saybrook", "hockey", "Harvard", "bulldog". Empty when only filtering.
        category: One of Hoodies, Crewnecks, Quarter-Zips, T-Shirts, Long Sleeve, Jackets & Fleece.
        min_price: Minimum price in USD.
        max_price: Maximum price in USD.
        size: Only return items IN STOCK in this size (XS, S, M, L, XL, XXL). Items sold out in that size are listed in sold_out_in_requested_size.
        color: Color word, e.g. "navy", "gray", "white".
        sort: "relevance" (default), "price_asc" for cheapest first, "price_desc" for most expensive first.
        limit: Max results (default 8, max 20).
    """
    full = tools.search_products(query, category, min_price, max_price, size, color, sort, MAX_PAGE_RESULTS)
    ctx.deps.record_search(
        SearchFilters(query=query, category=category, min_price=min_price, max_price=max_price, size=size, color=color, sort=sort),
        # No exact match -> the automatic alternatives are what the page should show.
        [p.product_id for p in (full.products or full.alternatives)],
    )
    return full.model_copy(update={"products": full.products[: max(1, min(limit, MAX_MODEL_RESULTS))]})


@agent.tool_plain
def get_product_details(product_id: str) -> ProductDetails | ToolError:
    """Full record for one product: description, price, colors, tags, and quantity + status for every size.

    Use when the customer asks about a specific item's details, or before describing an item you haven't looked up this turn.

    Args:
        product_id: Exact product_id from a previous tool result, e.g. "basic-hoodie-big-yale".
    """
    return tools.get_product_details(product_id)


@agent.tool_plain
def check_stock(product_id: str, size: str | None = None) -> StockReport | ToolError:
    """Live stock for one product, optionally one size. Returns status (in_stock / low_stock / sold_out), quantity, and a plain-English summary.

    ALWAYS use before saying whether a specific item is available in a size.

    Args:
        product_id: Exact product_id from a previous tool result.
        size: XS, S, M, L, XL, or XXL ("medium", "2XL" are understood). Omit for all sizes.
    """
    return tools.check_stock(product_id, size)


@agent.tool
def find_alternatives(ctx: RunContext[ChatDeps], product_id: str, size: str | None = None, limit: int = 4) -> SearchResult | ToolError:
    """Similar items (same category, closest price) that ARE in stock, optionally in a given size.

    Use right after check_stock/search shows something is sold out, so you can offer a real alternative.

    Args:
        product_id: The product that is sold out (or that the customer liked).
        size: Size the customer needs. Only items in stock in this size are returned.
        limit: Max alternatives (default 4).
    """
    result = tools.find_alternatives(product_id, size, limit)
    if isinstance(result, SearchResult):
        ctx.deps.record_search(
            SearchFilters(query=f"similar to {product_id}", size=size),
            [p.product_id for p in result.products],
        )
    return result


@agent.tool_plain
def list_categories() -> CatalogOverview:
    """Categories we carry with product counts and price ranges, plus available sizes. Use for broad "what do you sell?" questions."""
    return tools.list_categories()


def to_model_history(turns: list[ChatTurn]) -> list[ModelMessage]:
    """Convert stored/client chat turns into PydanticAI message history.

    Assistant turns get a note listing the products shown with them, so
    references like "the first one" survive reloads and new sessions.
    """
    history: list[ModelMessage] = []
    for t in turns[-config.HISTORY_LIMIT:]:
        if t.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=t.content)]))
            continue
        text = t.content
        refs = [f"{p['name']} (`{p['product_id']}`)" for pid in t.product_ids[:6] if (p := db.get_product(pid))]
        if refs:
            text += "\n\n[Products shown with this message: " + "; ".join(refs) + "]"
        history.append(ModelResponse(parts=[TextPart(content=text)]))
    return history


def _tools_used(messages: list[ModelMessage]) -> list[str]:
    used: list[str] = []
    for msg in messages:
        for part in getattr(msg, "parts", []):
            if type(part).__name__ == "ToolCallPart" and part.tool_name not in used:
                used.append(part.tool_name)
    # The structured-output tool is plumbing, not a catalogue lookup.
    return [t for t in used if t != "final_result"]


FILTERED_REPLY = (
    "I can't help with that one, but I'd be happy to help you find some great Yale gear. "
    "What are you shopping for today?"
)

LIMIT_REPLY = (
    "Sorry, that one took me more digging than I'm allowed in a single message. "
    "Could you narrow it down a bit, like a category, size, or price range?"
)


async def run_chat(
    message: str,
    history: list[ChatTurn],
    customer: CustomerProfile | None = None,
    page: PageContext | None = None,
) -> ChatResponse:
    """Run one chat turn under usage limits and append an audit record (P12)."""
    deps = ChatDeps(
        customer=customer,
        page_path=page.path if page else "/",
        # Only trust product ids that exist in the DB.
        current_product=db.get_product(page.product_id) if page and page.product_id else None,
    )
    record = audit.new_record(
        actor=f"user:{customer.user_id}" if customer else "guest",
        page_path=deps.page_path,
        message=message,
        model=config.MODEL_NAME,
    )
    record["history_turns"] = min(len(history), config.HISTORY_LIMIT)
    started = time.monotonic()
    limits = UsageLimits(
        request_limit=config.AGENT_REQUEST_LIMIT,
        tool_calls_limit=config.AGENT_TOOL_CALLS_LIMIT,
        total_tokens_limit=config.AGENT_TOTAL_TOKENS_LIMIT,
    )

    try:
        result = await agent.run(
            message,
            model=config.build_model(),
            deps=deps,
            message_history=to_model_history(history),
            usage_limits=limits,
        )
    except ModelHTTPError as exc:
        # The provider's own safety layer (e.g. Azure content filter / prompt shield)
        # rejected the request: answer with a safe refusal instead of an error page.
        if exc.status_code == 400 and "content management policy" in str(exc.body):
            record.update(
                tool_calls=[], reply_preview=FILTERED_REPLY, why_it_stopped="provider_content_filter",
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            audit.append(record)
            return ChatResponse(reply=FILTERED_REPLY)
        record.update(tool_calls=[], why_it_stopped=f"error: ModelHTTPError {exc.status_code}",
                      duration_ms=int((time.monotonic() - started) * 1000))
        audit.append(record)
        raise
    except UsageLimitExceeded as exc:
        record.update(
            tool_calls=[], reply_preview=audit.short(LIMIT_REPLY, audit.MAX_TEXT),
            why_it_stopped=f"usage_limit: {exc}", duration_ms=int((time.monotonic() - started) * 1000),
        )
        audit.append(record)
        return ChatResponse(reply=LIMIT_REPLY)
    except Exception as exc:
        record.update(
            tool_calls=[], why_it_stopped=f"error: {type(exc).__name__}: {audit.short(str(exc), 200)}",
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        audit.append(record)
        raise

    # From here on the run succeeded; always write the audit record, even if
    # building the response fails.
    try:
        output: AgentReply = result.output

        # Only show cards for real products, in the order the agent chose.
        products: list[dict] = []
        for pid in dict.fromkeys(output.product_ids):
            p = db.get_product(pid)
            if p is not None:
                products.append(p)
            if len(products) >= MAX_PRODUCT_CARDS:
                break

        response = ChatResponse(
            reply=output.reply,
            products=products,
            page_results=_page_results(message, output, deps),
            quick_replies=[q.strip()[:40] for q in output.quick_replies if q.strip()][:4],
            tools_used=_tools_used(result.new_messages()),
        )
    except Exception as exc:
        record.update(
            tool_calls=audit.summarize_tool_calls(result.new_messages()),
            why_it_stopped=f"error building response: {type(exc).__name__}: {audit.short(str(exc), 200)}",
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        audit.append(record)
        raise

    calls = audit.summarize_tool_calls(result.new_messages())
    usage = result.usage() if callable(result.usage) else result.usage  # method in older PydanticAI, property now
    dropped = [pid for pid in output.product_ids if pid not in {p["product_id"] for p in products}]
    record.update(
        tool_calls=calls,
        reply_preview=audit.short(output.reply, audit.MAX_TEXT),
        product_ids=[p["product_id"] for p in products],
        invalid_product_ids_dropped=dropped,
        page_results=response.page_results.total if response.page_results else 0,
        asked_clarifying_question=bool(response.quick_replies),
        why_it_stopped=(
            f"final_answer after {len(calls)} tool call(s)" if calls else "final_answer without tools"
        ),
        usage={
            "requests": usage.requests,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        },
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    audit.append(record)
    return response


def _page_results(message: str, output: AgentReply, deps: ChatDeps) -> PageResults | None:
    """Full search results for the page, if the agent marked this as a browse/search turn.

    The product list comes from what the tools actually returned (recorded in
    deps), never from model-written text, so every card is a real DB row.
    """
    if not output.show_results_on_page or not deps.search_result_ids:
        return None
    products = [p for pid in deps.search_result_ids[:MAX_PAGE_RESULTS] if (p := db.get_product(pid))]
    if not products:
        return None
    return PageResults(
        title=(output.results_title or "Results").strip()[:80],
        query=message,
        total=len(deps.search_result_ids),
        filters=deps.searches,
        products=products,
    )
