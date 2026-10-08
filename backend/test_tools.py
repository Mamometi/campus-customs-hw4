"""Checks the agent tools against raw SQL on the real database (read-only).

Run from backend/: .venv/bin/python test_tools.py
"""
from __future__ import annotations

import db
import tools
from models import ProductDetails, SearchResult, StockReport, ToolError


def sql_qty(product_id: str, size: str) -> int:
    with db.connect() as conn:
        return conn.execute(
            "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (product_id, size)
        ).fetchone()[0]


def sql_price(product_id: str) -> float:
    with db.connect() as conn:
        return conn.execute("SELECT price FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()[0]


def test_every_size_status_matches_sql():
    with db.connect() as conn:
        rows = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    for r in rows:
        report = tools.check_stock(r["product_id"], r["size"])
        assert isinstance(report, StockReport)
        assert report.requested_size_quantity == r["quantity"]
        expected = "sold_out" if r["quantity"] == 0 else "low_stock" if r["quantity"] <= 5 else "in_stock"
        assert report.requested_size_status == expected, (r["product_id"], r["size"])
        if expected == "sold_out":
            assert "SOLD OUT" in report.summary
    assert len(rows) == 612


def test_sold_out_size():
    r = tools.check_stock("baseball-left-chest-crewneck", "XL")
    assert r.requested_size_status == "sold_out" and sql_qty("baseball-left-chest-crewneck", "XL") == 0
    assert "XL" not in r.sizes_in_stock
    assert r.sizes_in_stock == ["S", "M", "L", "XXL"]


def test_size_aliases_and_bad_size():
    assert tools.check_stock("basic-hoodie-big-yale", "medium").requested_size == "M"
    assert tools.check_stock("basic-hoodie-big-yale", "2XL").requested_size == "XXL"
    assert isinstance(tools.check_stock("basic-hoodie-big-yale", "XXXL"), ToolError)


def test_details_match_sql():
    d = tools.get_product_details("basic-hoodie-big-yale")
    assert isinstance(d, ProductDetails)
    assert d.price == sql_price("basic-hoodie-big-yale")
    assert [s.size for s in d.inventory] == db.SIZE_ORDER
    assert all(s.quantity == sql_qty(d.product_id, s.size) for s in d.inventory)


def test_unknown_id_gives_suggestions():
    r = tools.get_product_details("big-yale-hoodie")
    assert isinstance(r, ToolError)
    assert any(s.product_id == "basic-hoodie-big-yale" for s in r.suggestions)


def test_search_size_filter_splits_sold_out():
    r = tools.search_products("hoodie", size="XL", limit=20)
    assert isinstance(r, SearchResult)
    assert all("XL" in p.sizes_in_stock for p in r.products)
    for ref in r.sold_out_in_requested_size:
        assert sql_qty(ref.product_id, "XL") == 0
    assert r.total_found + len(r.sold_out_in_requested_size) == 27  # all hoodies accounted for


def test_search_sort_cheapest():
    r = tools.search_products(category="Jackets & Fleece", sort="price_asc")
    prices = [p.price for p in r.products]
    assert prices == sorted(prices)


def test_plurals_and_no_match():
    assert tools.search_products("hoodies").total_found == 27
    assert tools.search_products("lacrosse stick xyz").match in {"partial", "none"}


def test_find_alternatives_in_stock_in_size():
    r = tools.find_alternatives("baseball-left-chest-crewneck", "XL")
    assert isinstance(r, SearchResult) and r.products
    for p in r.products:
        assert p.category == "Crewnecks" and p.product_id != "baseball-left-chest-crewneck"
        assert sql_qty(p.product_id, "XL") > 0


def test_categories_total():
    o = tools.list_categories()
    assert o.total_products == 102 and sum(c.count for c in o.categories) == 102


def test_not_carried_gets_alternatives():
    r = tools.search_products("shorts")
    assert r.match == "none" and "don't carry" in r.note and r.alternatives
    assert all(a.category == "T-Shirts" and a.total_stock > 0 for a in r.alternatives)
    assert tools.search_products("short sleeve").total_found > 0  # not confused with "shorts"


def test_color_family_fallback():
    r = tools.search_products(color="pink")
    assert r.products and all("dusty coral" in p.colors for p in r.products)
    assert "nothing in pink" in r.note


def test_relaxed_alternatives():
    r = tools.search_products("hoodie", max_price=30)
    assert r.match == "none" and r.alternatives
    prices = [a.price for a in r.alternatives]
    assert prices == sorted(prices)  # cheapest first when the budget is relaxed
    r = tools.search_products("saybrook", category="Hoodies")
    assert r.alternatives and all("Saybrook" in a.name for a in r.alternatives)


def test_sold_out_stock_has_alternatives():
    r = tools.check_stock("baseball-left-chest-crewneck", "XL")
    assert r.alternatives and all(sql_qty(a.product_id, "XL") > 0 for a in r.alternatives)


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"✓ {name}")
    print(f"{len(tests)} passed")
