"""Pydantic models shared by main.py, agent.py, and tools.py."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class User(BaseModel):
    id: int
    name: str
    first_name: str
    last_name: str
    email: str


# ---------- Chat ----------

class ChatTurn(BaseModel):
    """One earlier message (from the DB for logged-in users, from the client for guests)."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)
    # Products shown with an assistant message, so "the first one" still
    # resolves after a reload / in a later session.
    product_ids: list[str] = Field(default_factory=list, max_length=12)


class PageContext(BaseModel):
    """Where the customer is on the site when they send a message."""

    path: str = Field(default="/", max_length=300)
    product_id: str | None = Field(default=None, max_length=120)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)
    page: PageContext | None = None


class CustomerProfile(BaseModel):
    """Logged-in customer details passed to the agent via ChatDeps (never for guests)."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str
    past_messages: int  # chat messages saved before this turn
    last_chat_at: str | None = None


class AgentReply(BaseModel):
    """Structured output the agent must produce for every turn."""

    reply: str = Field(
        description="Your message to the customer, in Markdown. Friendly, concise, factual."
    )
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "product_id values (exactly as returned by the tools) of the products you "
            "mention or recommend in the reply, most relevant first, at most 6. "
            "Empty if no specific products are discussed."
        ),
    )
    show_results_on_page: bool = Field(
        default=False,
        description=(
            "True when the customer is browsing or searching for a SET of products "
            "(e.g. 'what hoodies do you have?', 'show me Saybrook gear', 'anything under $40?') "
            "and you ran search_products or find_alternatives. The website will then show ALL "
            "matching results as product cards on the page. False for questions about one "
            "specific item, stock checks, small talk, or when nothing matched."
        ),
    )
    quick_replies: list[str] = Field(
        default_factory=list,
        max_length=4,
        description=(
            "When you ask a clarifying question, 2–4 short tappable answers (≤ 4 words each), "
            "e.g. ['Hoodie', 'Crewneck', 'T-shirt', 'Not sure']. Empty otherwise."
        ),
    )
    results_title: str | None = Field(
        default=None,
        description="Short heading for the on-page results, e.g. 'Hoodies', 'Navy crewnecks in M'. Only when show_results_on_page is true.",
    )


class SearchFilters(BaseModel):
    """The arguments the agent passed to a search tool (echoed to the frontend)."""

    query: str = ""
    category: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    size: str | None = None
    color: str | None = None
    sort: str = "relevance"


class PageResults(BaseModel):
    """Search results the frontend renders as product cards on the page."""

    title: str
    query: str  # the customer's chat message that produced these results
    total: int
    filters: list[SearchFilters]  # one entry per search the agent ran this turn
    products: list[dict]  # full product contract (db.build_product), in result order


class ChatResponse(BaseModel):
    """What /api/chat returns to the frontend."""

    reply: str
    products: list[dict] = Field(default_factory=list)  # chat cards the agent highlighted (≤ 6)
    page_results: PageResults | None = None  # full search results to show on the page
    quick_replies: list[str] = Field(default_factory=list)  # tappable answers to a clarifying question
    tools_used: list[str] = Field(default_factory=list)


class ChatHistoryMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    products: list[dict] = Field(default_factory=list)
    created_at: str


# ---------- Agent tool outputs (tools.py) ----------
# Every tool returns one of these so the model sees a consistent, typed shape
# built from the SQLite catalogue + inventory tables.

StockStatus = Literal["in_stock", "low_stock", "sold_out"]


class SizeStock(BaseModel):
    size: str
    quantity: int
    status: StockStatus = Field(description="sold_out = 0 units, low_stock = 1–5 units, in_stock = 6+")


class ProductSummary(BaseModel):
    """One product as returned by search_products / find_alternatives."""

    product_id: str
    name: str
    category: str
    garment_type: str
    price: float
    colors: list[str] = Field(description="Colors that appear on the item, including print/graphic colors")
    description: str
    stock_status: StockStatus = Field(description="Overall: sold_out if every size is 0, low_stock if total ≤ 10")
    total_stock: int
    sizes_in_stock: list[str]
    low_stock_sizes: list[str]
    sold_out_sizes: list[str]
    quantity_by_size: dict[str, int] = Field(
        default_factory=dict, description="Exact units per size. Quote these; never estimate stock"
    )


class ProductRef(BaseModel):
    """Minimal pointer to a product."""

    product_id: str
    name: str
    price: float
    sizes_in_stock: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    match: Literal["all", "partial", "none"] = Field(
        description="all = every keyword matched; partial = closest items, not exact; none = nothing found"
    )
    total_found: int
    products: list[ProductSummary]
    sold_out_in_requested_size: list[ProductRef] = Field(
        default_factory=list,
        description="Items that matched the search but are SOLD OUT in the requested size",
    )
    note: str | None = None
    alternatives: list["ProductSummary"] = Field(
        default_factory=list,
        description="In-stock substitutes, filled automatically when the exact request can't be met. Recommend these.",
    )
    alternatives_reason: str | None = Field(
        default=None, description="Why alternatives were suggested and which filters were relaxed"
    )


class ProductDetails(ProductSummary):
    """Full record from get_product_details."""

    search_tags: list[str]
    inventory: list[SizeStock]


class StockReport(BaseModel):
    product_id: str
    name: str
    price: float
    requested_size: str | None = None
    requested_size_status: StockStatus | None = None
    requested_size_quantity: int | None = None
    sizes: list[SizeStock]
    sizes_in_stock: list[str]
    summary: str = Field(description="Plain-English stock statement, safe to relay to the customer")
    alternatives: list[ProductSummary] = Field(
        default_factory=list,
        description="Similar items IN STOCK in the requested size, filled automatically when that size is sold out",
    )


class CategoryInfo(BaseModel):
    category: str
    count: int
    min_price: float
    max_price: float


class CatalogOverview(BaseModel):
    categories: list[CategoryInfo]
    sizes: list[str]
    total_products: int
    note: str


class ToolError(BaseModel):
    error: str
    suggestions: list[ProductRef] = Field(
        default_factory=list, description="Close matches by name, if any"
    )
