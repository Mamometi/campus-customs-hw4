"""Campus Customs storefront API — FastAPI entry point (routes only).

Run from backend/: .venv/bin/python -m uvicorn main:app --reload --port 8000
API docs: http://127.0.0.1:8000/docs
Frontend (Vite): http://127.0.0.1:5173
"""
from __future__ import annotations

import config  # noqa: F401  (loads .env before anything reads os.environ)

import json
import logging
import re
import sqlite3

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import auth
import db
from agent import run_chat
from models import (
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    ChatTurn,
    CustomerProfile,
    LoginRequest,
    SignupRequest,
    User,
)

log = logging.getLogger("campus_customs")

app = FastAPI(title="Campus Customs", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
db.CUTOUT_DIR.mkdir(exist_ok=True)
app.mount("/media/products_cutout", StaticFiles(directory=db.CUTOUT_DIR), name="product-cutouts")
app.mount("/media/products", StaticFiles(directory=db.PRODUCTS_DIR), name="product-images")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "db": db.DB_PATH.name,
        "assistant": config.ASSISTANT_NAME,
        "model": config.MODEL_NAME,
        "portkey_key_set": config.api_key_set(),
    }


# ---------- Products ----------

SORTS = {
    "name": (lambda p: p["name"].lower(), False),
    "price_asc": (lambda p: p["price"], False),
    "price_desc": (lambda p: p["price"], True),
}


@app.get("/api/products")
def list_products(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    size: str | None = Query(default=None, description="Only items in stock in this size (XS–XXL)"),
    sort: str = Query(default="name"),
):
    products = db.list_products()
    if category:
        products = [p for p in products if p["category"] == category]
    if size:
        s = size.upper()
        products = [p for p in products if any(i["size"] == s and i["quantity"] > 0 for i in p["inventory"])]
    if q and q.strip():
        # Each term must start a word ("art" shouldn't match "quarter"); plurals fold ("hoodies" -> "hoodie").
        patterns = [
            re.compile(r"\b(?:" + "|".join(re.escape(v) for v in {t, t[:-1] if len(t) > 3 and t.endswith("s") else t}) + ")")
            for t in q.lower().split()
        ]
        products = [p for p in products if all(pat.search(db.search_text(p)) for pat in patterns)]
    key, reverse = SORTS.get(sort, SORTS["name"])
    products.sort(key=key, reverse=reverse)
    return {"count": len(products), "products": products}


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    product = db.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/api/sizes")
def sizes(category: str | None = Query(default=None)):
    """How many products are in stock in each size (optionally within a category)."""
    products = [p for p in db.list_products() if not category or p["category"] == category]
    return [
        {"size": s, "in_stock": sum(1 for p in products if any(i["size"] == s and i["quantity"] > 0 for i in p["inventory"]))}
        for s in db.SIZE_ORDER
    ]


@app.get("/api/categories")
def categories():
    counts: dict[str, int] = {c: 0 for c in db.CATEGORIES}
    for p in db.list_products():
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    return [{"name": name, "count": n} for name, n in counts.items() if n]


# ---------- Auth ----------

def public_user(row: sqlite3.Row) -> User:
    first, last = row["first_name"], row["last_name"]
    if not first:
        first, _, last = row["name"].partition(" ")
    return User(id=row["id"], name=row["name"], first_name=first, last_name=last or "", email=row["email"])


def _user_from_header(authorization: str | None) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    user_id = auth.read_token(authorization.removeprefix("Bearer "))
    if user_id is None:
        return None
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(row) if row else None


def current_user(authorization: str | None = Header(default=None)) -> User:
    user = _user_from_header(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Not logged in or session expired")
    return user


def optional_user(authorization: str | None = Header(default=None)) -> User | None:
    return _user_from_header(authorization)


@app.post("/api/auth/signup", status_code=201)
def signup(body: SignupRequest):
    email = body.email.lower()
    first, last = body.first_name.strip(), body.last_name.strip()
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first} {last}", email, auth.hash_password(body.password), first, last),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {"token": auth.create_token(row["id"]), "user": public_user(row)}


@app.post("/api/auth/login")
def login(body: LoginRequest):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (body.email.lower(),)).fetchone()
    if row is None or not auth.verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"token": auth.create_token(row["id"]), "user": public_user(row)}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)) -> User:
    return user


# ---------- Chat ----------

def _load_history(user_id: int, limit: int) -> list[sqlite3.Row]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def _turn(row: sqlite3.Row) -> ChatTurn:
    ids = [p["product_id"] for p in json.loads(row["products_json"])] if row["products_json"] else []
    return ChatTurn(role=row["role"], content=row["content"], product_ids=ids)


def _customer_profile(user: User) -> CustomerProfile:
    """Name, email, and chat stats for the agent's dependencies (logged-in users only)."""
    with db.connect() as conn:
        created = conn.execute("SELECT created_at FROM users WHERE id = ?", (user.id,)).fetchone()["created_at"]
        stats = conn.execute(
            "SELECT COUNT(*) AS n, MAX(created_at) AS last FROM chat_messages WHERE user_id = ?", (user.id,)
        ).fetchone()
    return CustomerProfile(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        member_since=created,
        past_messages=stats["n"],
        last_chat_at=stats["last"],
    )


@app.get("/api/chat/history")
def chat_history(user: User = Depends(current_user)) -> list[ChatHistoryMessage]:
    return [
        ChatHistoryMessage(
            id=r["id"],
            role=r["role"],
            content=r["content"],
            products=json.loads(r["products_json"]) if r["products_json"] else [],
            created_at=r["created_at"],
        )
        for r in _load_history(user.id, 200)
    ]


@app.post("/api/chat")
async def chat(body: ChatRequest, user: User | None = Depends(optional_user)) -> ChatResponse:
    if not config.api_key_set():
        raise HTTPException(status_code=503, detail="The assistant isn't configured yet (PORTKEY_API_KEY missing).")

    # Logged-in users: memory comes from the DB (survives sessions/devices).
    # Guests: the client sends its in-memory conversation; nothing is stored.
    if user:
        history = [_turn(r) for r in _load_history(user.id, config.HISTORY_LIMIT)]
        customer = _customer_profile(user)
    else:
        history = body.history
        customer = None

    try:
        response = await run_chat(body.message, history, customer, body.page)
    except Exception:
        log.exception("Agent run failed")
        raise HTTPException(status_code=502, detail="Sorry, the assistant ran into a problem. Please try again.")

    if user:
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
                (user.id, body.message),
            )
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
                (user.id, response.reply, json.dumps(response.products)),
            )
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
