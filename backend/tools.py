"""Product & inventory tools for the Campus Customs agent.

Plain functions that read the SQLite `catalogue` and `inventory` tables (via
db.py) and return the structured models in models.py. agent.py registers them
as PydanticAI tools; they can also be called and tested without the model.

Stock rules (single source of truth for the agent):
- quantity 0      -> "sold_out"
- quantity 1–5    -> "low_stock"
- quantity 6+     -> "in_stock"
"""
from __future__ import annotations

from typing import Literal

import db
from models import (
    CatalogOverview,
    CategoryInfo,
    ProductDetails,
    ProductRef,
    ProductSummary,
    SearchResult,
    SizeStock,
    StockReport,
    StockStatus,
    ToolError,
)

LOW_STOCK_MAX = 5          # per size
MAX_ALTERNATIVES = 4

# Things we don't sell -> the category that makes the best substitute.
NOT_CARRIED: dict[str, str | None] = {
    "shorts": "T-Shirts", "pant": "Hoodies", "pants": "Hoodies", "sweatpant": "Hoodies",
    "sweatpants": "Hoodies", "jogger": "Hoodies", "joggers": "Hoodies", "legging": "Long Sleeve", "leggings": "Long Sleeve",
    "hat": "Jackets & Fleece", "hats": "Jackets & Fleece", "cap": "Jackets & Fleece", "beanie": "Jackets & Fleece",
    "scarf": "Jackets & Fleece", "gloves": "Jackets & Fleece", "socks": None, "mug": None, "mugs": None,
    "sticker": None, "stickers": None, "bag": None, "backpack": None, "tote": None, "onesie": None, "bib": None,
    "blanket": None, "lanyard": None, "keychain": None, "dress": None, "skirt": None, "polo": "Long Sleeve",
}

# Colors customers ask for -> closest colors that exist in the catalogue.
COLOR_FAMILIES: dict[str, list[str]] = {
    "pink": ["dusty coral"], "rose": ["dusty coral"], "salmon": ["dusty coral"],
    "coral": ["dusty coral"], "peach": ["dusty coral"], "orange": ["dusty coral", "gold"],
    "purple": ["royal blue", "navy"], "violet": ["royal blue"], "lavender": ["light blue"],
    "maroon": ["red"], "burgundy": ["red"], "crimson": ["red"],
    "beige": ["cream", "ivory"], "tan": ["cream", "ivory"], "off-white": ["cream", "ivory", "white"],
    "grey": ["gray", "heather gray", "light gray"], "silver": ["light gray", "heather gray"],
    "black": ["black", "charcoal gray", "heather charcoal gray"], "dark": ["navy", "charcoal gray", "black"],
    "blue": ["navy", "royal blue", "light blue", "blue"], "teal": ["green", "light blue"],
    "yellow": ["yellow", "gold"], "olive": ["green"], "brown": ["cream", "gold"],
}
PRODUCT_LOW_STOCK_MAX = 10  # total units across sizes

SortKey = Literal["relevance", "price_asc", "price_desc"]


# ---------- helpers ----------

def size_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    if quantity <= LOW_STOCK_MAX:
        return "low_stock"
    return "in_stock"


def normalize_size(size: str | None) -> str | None:
    if not size:
        return None
    s = size.upper().replace(" ", "").replace("-", "")
    aliases = {
        "EXTRASMALL": "XS", "SMALL": "S", "MEDIUM": "M", "MED": "M", "LARGE": "L",
        "EXTRALARGE": "XL", "XXLARGE": "XXL", "2XL": "XXL", "XXXL": "XXXL",
    }
    return aliases.get(s, s)


def _variants(word: str) -> tuple[str, ...]:
    """Light plural folding: "hoodies" also tries "hoodie", "hobbies" "hobby"."""
    forms = [word]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        forms.append(word[:-1])
        if word.endswith("ies"):
            forms.append(word[:-3] + "y")
    return tuple(forms)


def _summary(p: dict) -> ProductSummary:
    inv = p["inventory"]
    total = p["total_stock"]
    overall: StockStatus = "sold_out" if total == 0 else "low_stock" if total <= PRODUCT_LOW_STOCK_MAX else "in_stock"
    return ProductSummary(
        product_id=p["product_id"],
        name=p["name"],
        category=p["category"],
        garment_type=p["garment_type"],
        price=p["price"],
        colors=p["colors"],
        description=p["description"],
        stock_status=overall,
        total_stock=total,
        sizes_in_stock=[i["size"] for i in inv if i["quantity"] > 0],
        low_stock_sizes=[i["size"] for i in inv if 0 < i["quantity"] <= LOW_STOCK_MAX],
        sold_out_sizes=[i["size"] for i in inv if i["quantity"] == 0],
        quantity_by_size={i["size"]: i["quantity"] for i in inv},
    )


def _color_match(p: dict, color: str) -> bool:
    return any(color in col.lower() for col in p["colors"]) or color in p["description"].lower()


def _in_stock(p: dict, size: str | None) -> bool:
    return (_qty(p, size) or 0) > 0 if size else p["total_stock"] > 0


def _similarity(base: dict, p: dict) -> float:
    """Higher = better substitute: same category, shared theme words/colors, close price."""
    base_words = set(db.search_text(base).split())
    words = set(db.search_text(p).split())
    score = 3.0 if p["category"] == base["category"] else 0.0
    score += 0.4 * len(base_words & words)
    score += 0.5 * len({c.lower() for c in base["colors"]} & {c.lower() for c in p["colors"]})
    score -= abs(p["price"] - base["price"]) / 20
    return score


def _similar(base: dict, size: str | None, limit: int) -> list[dict]:
    pool = [p for p in db.list_products() if p["product_id"] != base["product_id"] and _in_stock(p, size)]
    return sorted(pool, key=lambda p: -_similarity(base, p))[:limit]


def _popular(products: list[dict], size: str | None, limit: int) -> list[dict]:
    """Best-stocked items, one per category first, as a last-resort suggestion."""
    ranked = sorted((p for p in products if _in_stock(p, size)), key=lambda p: -p["total_stock"])
    picked, seen = [], set()
    for p in ranked:
        if p["category"] not in seen:
            picked.append(p)
            seen.add(p["category"])
    picked += [p for p in ranked if p not in picked]
    return picked[:limit]


def _ref(p: dict) -> ProductRef:
    return ProductRef(
        product_id=p["product_id"], name=p["name"], price=p["price"],
        sizes_in_stock=[i["size"] for i in p["inventory"] if i["quantity"] > 0],
    )


def _qty(p: dict, size: str) -> int | None:
    for i in p["inventory"]:
        if i["size"] == size:
            return i["quantity"]
    return None


def _not_found(product_id: str) -> ToolError:
    """Unknown id: suggest products whose name/id shares words with what was asked."""
    words = [w for w in product_id.lower().replace("-", " ").split() if len(w) > 2]
    scored = []
    for p in db.list_products():
        hay = f"{p['product_id']} {p['name']}".lower()
        hits = sum(1 for w in words if w in hay)
        if hits:
            scored.append((hits, p))
    scored.sort(key=lambda x: -x[0])
    return ToolError(
        error=f"No product with id '{product_id}'. Use an exact product_id from search_products.",
        suggestions=[_ref(p) for _, p in scored[:5]],
    )


# ---------- tools ----------

def search_products(
    query: str = "",
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    size: str | None = None,
    color: str | None = None,
    sort: SortKey = "relevance",
    limit: int = 8,
) -> SearchResult:
    """Keyword + filter search over catalogue/inventory.

    Every keyword must match name, garment type, description, colors, or tags.
    If nothing matches all keywords, the closest partial matches are returned
    (match="partial"). With `size`, items sold out in that size are moved to
    `sold_out_in_requested_size` instead of being silently dropped.
    """
    limit = max(1, min(limit, 200))
    products = db.list_products()
    notes: list[str] = []

    if category:
        valid = {c.lower(): c for c in db.CATEGORIES}
        if category.lower() not in valid:
            notes.append(f"Unknown category '{category}'. Valid: {', '.join(db.CATEGORIES)}.")
        products = [p for p in products if p["category"].lower() == category.lower()]
    if min_price is not None:
        products = [p for p in products if p["price"] >= min_price]
    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]
    before_color = products
    if color:
        c = color.lower().strip()
        products = [p for p in before_color if _color_match(p, c)]
        if not products and c in COLOR_FAMILIES:
            family = COLOR_FAMILIES[c]
            products = [p for p in before_color if any(_color_match(p, f) for f in family)]
            notes.append(
                f"We have nothing in {color}. Showing the closest colors we carry ({', '.join(family)}); say so explicitly."
            )

    # Product types we don't sell: say so (instead of "shorts" matching "short-sleeve").
    raw_terms = query.lower().split()
    not_carried = [t for t in raw_terms if t in NOT_CARRIED]
    if not_carried:
        item = not_carried[0]
        sub_cat = NOT_CARRIED[item]
        pool = db.list_products()
        if sub_cat:
            pool = [p for p in pool if p["category"] == sub_cat]
        theme = [t for t in raw_terms if t not in NOT_CARRIED]
        if theme:  # keep e.g. "hockey" from "hockey shorts"
            themed = [p for p in pool if any(any(f in db.search_text(p) for f in _variants(t)) for t in theme)]
            pool = themed or pool
        want = normalize_size(size)
        alts = _popular(pool, want if want in db.SIZE_ORDER else None, MAX_ALTERNATIVES)
        return SearchResult(
            match="none", total_found=0, products=[],
            note=f"We don't carry {item}. Campus Customs sells tops and outerwear only.",
            alternatives=[_summary(p) for p in alts],
            alternatives_reason=f"Closest things we do carry{f' ({sub_cat})' if sub_cat else ''}.",
        )

    terms = [_variants(t) for t in raw_terms if t]
    match: Literal["all", "partial", "none"] = "all"
    if terms:
        scored = []
        for p in products:
            text = db.search_text(p)
            hits = sum(1 for forms in terms if any(f in text for f in forms))
            if hits:
                scored.append((hits, p))
        full = [p for hits, p in scored if hits == len(terms)]
        if full:
            products = full
        else:
            match = "partial"
            scored.sort(key=lambda x: -x[0])
            products = [p for _, p in scored]

    sold_out_in_size: list[ProductRef] = []
    want = normalize_size(size)
    if want:
        if want not in db.SIZE_ORDER:
            notes.append(f"We don't carry size '{size}'. Sizes: {', '.join(db.SIZE_ORDER)}.")
            products = []
        else:
            sold_out_in_size = [_ref(p) for p in products if (_qty(p, want) or 0) == 0]
            products = [p for p in products if (_qty(p, want) or 0) > 0]

    if sort == "price_asc":
        products = sorted(products, key=lambda p: p["price"])
    elif sort == "price_desc":
        products = sorted(products, key=lambda p: -p["price"])

    alternatives: list[dict] = []
    reason: str | None = None
    if not products:
        match = "none"
        alternatives, reason = _fallback_alternatives(
            query, category, min_price, max_price, want if want in db.SIZE_ORDER else None, color, sold_out_in_size
        )

    return SearchResult(
        match=match,
        total_found=len(products),
        products=[_summary(p) for p in products[:limit]],
        sold_out_in_requested_size=sold_out_in_size[:limit],
        note=" ".join(notes) or None,
        alternatives=[_summary(p) for p in alternatives],
        alternatives_reason=reason,
    )


def _fallback_alternatives(
    query: str,
    category: str | None,
    min_price: float | None,
    max_price: float | None,
    size: str | None,
    color: str | None,
    sold_out_in_size: list[ProductRef],
) -> tuple[list[dict], str]:
    """Nothing matched: progressively relax the request so the customer always gets real, in-stock options."""
    # 1. The items exist but are sold out in their size -> closest items that ARE in that size.
    if sold_out_in_size:
        base = db.get_product(sold_out_in_size[0].product_id)
        return _similar(base, size, MAX_ALTERNATIVES), (
            f"Matching items are sold out in {size}; these similar items are in stock in {size}."
        )
    # 2. Drop filters one at a time (color, then price, then size), keeping keywords + category.
    relaxations = [
        ("color", dict(color=None)),
        ("price range", dict(color=None, min_price=None, max_price=None, sort="price_asc")),
        ("size", dict(color=None, min_price=None, max_price=None, size=None)),
        ("category", dict(color=None, min_price=None, max_price=None, size=None, category=None)),
    ]
    base_args = dict(query=query, category=category, min_price=min_price, max_price=max_price, size=size, color=color)
    for label, change in relaxations:
        if all(base_args.get(k) is None for k in change if k != "sort"):
            continue  # that filter wasn't used
        args = {**base_args, **change}
        r = search_products(**args, limit=MAX_ALTERNATIVES)  # type: ignore[arg-type]
        if r.products:
            ids = [x.product_id for x in r.products]
            return [db.get_product(i) for i in ids], f"Nothing matched exactly; relaxed the {label} to find these."
    # 3. We don't carry it at all -> popular in-stock picks (in their size/category if given).
    pool = db.list_products()
    if category:
        pool = [p for p in pool if p["category"].lower() == category.lower()] or pool
    return _popular(pool, size, MAX_ALTERNATIVES), "We don't carry anything like that; these are popular in-stock picks."


def get_product_details(product_id: str) -> ProductDetails | ToolError:
    """Everything we know about one product, including per-size stock."""
    p = db.get_product(product_id)
    if p is None:
        return _not_found(product_id)
    return ProductDetails(
        **_summary(p).model_dump(),
        search_tags=p["search_tags"],
        inventory=[SizeStock(size=i["size"], quantity=i["quantity"], status=size_status(i["quantity"])) for i in p["inventory"]],
    )


def check_stock(product_id: str, size: str | None = None) -> StockReport | ToolError:
    """Live stock for one product (optionally one size), with a plain-English summary."""
    p = db.get_product(product_id)
    if p is None:
        return _not_found(product_id)

    sizes = [SizeStock(size=i["size"], quantity=i["quantity"], status=size_status(i["quantity"])) for i in p["inventory"]]
    in_stock = [s.size for s in sizes if s.quantity > 0]
    want = normalize_size(size)

    if want is None:
        sold = [s.size for s in sizes if s.status == "sold_out"]
        low = [s.size for s in sizes if s.status == "low_stock"]
        summary = f"{p['name']} is available in {', '.join(in_stock) or 'no sizes'}."
        if sold:
            summary += f" Sold out in {', '.join(sold)}."
        if low:
            summary += f" Only a few left in {', '.join(low)}."
        return StockReport(product_id=p["product_id"], name=p["name"], price=p["price"], sizes=sizes, sizes_in_stock=in_stock, summary=summary)

    if want not in db.SIZE_ORDER:
        return ToolError(error=f"We don't carry size '{size}'. Sizes: {', '.join(db.SIZE_ORDER)}.")

    q = _qty(p, want) or 0
    status = size_status(q)
    alternatives: list[ProductSummary] = []
    if status == "sold_out":
        summary = f"{p['name']} is SOLD OUT in {want}." + (
            f" Still available in {', '.join(in_stock)}." if in_stock else " It is sold out in every size."
        )
        alternatives = [_summary(a) for a in _similar(p, want, 3)]
        if alternatives:
            summary += f" Similar items in stock in {want}: " + ", ".join(f"{a.name} (${a.price:g})" for a in alternatives) + "."
    elif status == "low_stock":
        summary = f"{p['name']} is in stock in {want}, but only {q} left."
    else:
        summary = f"{p['name']} is in stock in {want} ({q} available)."
    return StockReport(
        product_id=p["product_id"], name=p["name"], price=p["price"],
        requested_size=want, requested_size_status=status, requested_size_quantity=q,
        sizes=sizes, sizes_in_stock=in_stock, summary=summary, alternatives=alternatives,
    )


def find_alternatives(product_id: str, size: str | None = None, limit: int = 4) -> SearchResult | ToolError:
    """In-stock substitutes for a product: same category and theme first, then close in price.

    Ranks every in-stock item (in `size`, if given) by similarity: same category,
    shared keywords (college, sport, graphic), shared colors, and price distance.
    """
    base = db.get_product(product_id)
    if base is None:
        return _not_found(product_id)
    want = normalize_size(size)
    if want and want not in db.SIZE_ORDER:
        return ToolError(error=f"We don't carry size '{size}'. Sizes: {', '.join(db.SIZE_ORDER)}.")

    limit = max(1, min(limit, 10))
    similar = _similar(base, want, limit)
    return SearchResult(
        match="all" if similar else "none",
        total_found=len(similar),
        products=[_summary(p) for p in similar],
        note=f"Similar to {base['name']}" + (f", in stock in {want}" if want else "") + ", best match first",
    )


def list_categories() -> CatalogOverview:
    """Categories with counts and price ranges."""
    products = db.list_products()
    out: dict[str, CategoryInfo] = {}
    for p in products:
        c = out.get(p["category"])
        if c is None:
            out[p["category"]] = CategoryInfo(category=p["category"], count=1, min_price=p["price"], max_price=p["price"])
        else:
            c.count += 1
            c.min_price = min(c.min_price, p["price"])
            c.max_price = max(c.max_price, p["price"])
    order = {name: i for i, name in enumerate(db.CATEGORIES)}
    return CatalogOverview(
        categories=sorted(out.values(), key=lambda c: order.get(c.category, 99)),
        sizes=db.SIZE_ORDER,
        total_products=len(products),
        note="We carry tops and outerwear only (no shorts, pants, hats, or accessories).",
    )
