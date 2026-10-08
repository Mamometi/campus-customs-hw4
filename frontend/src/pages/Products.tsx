import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  fetchCategories,
  fetchProducts,
  fetchSizes,
  formatPrice,
  type Category,
  type SizeCount,
  type PageResults,
  type Product,
  type SortKey,
} from "../api";
import ProductCard from "../components/ProductCard";
import { useChatResults } from "../chatResults";
import { ASSISTANT_NAME, MASCOT_HEAD } from "../brand";

const SORT_LABELS: Record<SortKey, string> = {
  name: "Name (A–Z)",
  price_asc: "Price: low to high",
  price_desc: "Price: high to low",
};

/** Human-readable chips for the filters the agent used, e.g. "Size XS", "Under $40". */
function filterLabels(results: PageResults): string[] {
  const labels = new Set<string>();
  for (const f of results.filters) {
    if (f.query) labels.add(`“${f.query}”`);
    if (f.category) labels.add(f.category);
    if (f.size) labels.add(`Size ${f.size.toUpperCase()}`);
    if (f.color) labels.add(f.color);
    if (f.min_price != null && f.max_price != null) labels.add(`${formatPrice(f.min_price)}–${formatPrice(f.max_price)}`);
    else if (f.max_price != null) labels.add(`Under ${formatPrice(f.max_price)}`);
    else if (f.min_price != null) labels.add(`Over ${formatPrice(f.min_price)}`);
    if (f.sort === "price_asc") labels.add("Lowest price first");
    if (f.sort === "price_desc") labels.add("Highest price first");
  }
  return [...labels];
}

function ChatResultsView({ results, onClear }: { results: PageResults; onClear: () => void }) {
  const labels = filterLabels(results);
  return (
    <div className="page">
      <section className="chat-results">
        <img className="chat-results__dan" src={MASCOT_HEAD} alt={ASSISTANT_NAME} />
        <div className="chat-results__text">
          <span className="kicker">{ASSISTANT_NAME} found these for you</span>
          <h1>{results.title}</h1>
          <p>
            {results.total} item{results.total === 1 ? "" : "s"} matching “{results.query}”
          </p>
          {labels.length > 0 && (
            <div className="tags">
              {labels.map((l) => (
                <span key={l} className="tag">
                  {l}
                </span>
              ))}
            </div>
          )}
          <button className="btn btn--light chat-results__clear" onClick={onClear}>
            ✕ Show all products
          </button>
        </div>
      </section>

      <div className="product-grid">
        {results.products.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
      {results.products.length < results.total && (
        <p className="empty">Showing the first {results.products.length} of {results.total}.</p>
      )}
    </div>
  );
}

export default function Products() {
  const { results: chatResults, clear: clearChatResults } = useChatResults();
  const [params, setParams] = useSearchParams();
  const category = params.get("category") ?? "";
  const size = params.get("size") ?? "";
  const sort = (params.get("sort") as SortKey) || "name";
  const [query, setQuery] = useState(params.get("q") ?? "");

  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [sizeCounts, setSizeCounts] = useState<SizeCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => {});
  }, []);

  // Size counts follow the selected category so shoppers see what's actually available.
  useEffect(() => {
    fetchSizes(category || undefined).then(setSizeCounts).catch(() => {});
  }, [category]);

  const updateParam = useCallback(
    (key: string, value: string) =>
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value) next.set(key, value);
          else next.delete(key);
          return next;
        },
        { replace: true }
      ),
    [setParams]
  );

  // Debounce typing into the URL.
  useEffect(() => {
    const handle = setTimeout(() => updateParam("q", query.trim()), 250);
    return () => clearTimeout(handle);
  }, [query, updateParam]);

  const q = params.get("q") ?? "";
  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchProducts({ q: q || undefined, category: category || undefined, size: size || undefined, sort })
      .then((res) => setProducts(res.products))
      .catch((err) => setError(`${err.message}. Is the backend running on port 8000?`))
      .finally(() => setLoading(false));
  }, [q, category, size, sort]);

  const hasFilters = Boolean(category || size || q);
  function clearFilters() {
    setQuery("");
    setParams(sort !== "name" ? { sort } : {}, { replace: true });
  }

  // /products?view=chat shows the latest chat search; any other /products link shows the catalogue.
  if (params.get("view") === "chat" && chatResults) {
    return (
      <ChatResultsView
        results={chatResults}
        onClear={() => {
          clearChatResults();
          setParams({}, { replace: true });
        }}
      />
    );
  }

  return (
    <div className="page">
      <div className="page__head">
        <h1>
          {category || "All Products"}
          {size && <span className="page__subtitle"> in size {size}</span>}
        </h1>
        <p>{loading ? "Loading…" : `${products.length} item${products.length === 1 ? "" : "s"}`}</p>
      </div>

      <div className="filters">
        <input
          className="filters__search"
          type="search"
          placeholder="Search: try “navy hoodie”, “Saybrook”, “hockey”…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="filters__sort"
          value={sort}
          onChange={(e) => updateParam("sort", e.target.value === "name" ? "" : e.target.value)}
          aria-label="Sort products"
        >
          {Object.entries(SORT_LABELS).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-row">
        <span className="filter-row__label">Category</span>
        <div className="chips">
          <button
            className={`chip ${!category ? "chip--active" : ""}`}
            onClick={() => updateParam("category", "")}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c.name}
              className={`chip ${category === c.name ? "chip--active" : ""}`}
              onClick={() => updateParam("category", c.name)}
            >
              {c.name} <span>{c.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="filter-row">
        <span className="filter-row__label">Size</span>
        <div className="chips">
          <button className={`chip size-chip ${!size ? "chip--active" : ""}`} onClick={() => updateParam("size", "")}>
            Any
          </button>
          {sizeCounts.map((sc) => (
            <button
              key={sc.size}
              className={`chip size-chip ${size === sc.size ? "chip--active" : ""}`}
              onClick={() => updateParam("size", size === sc.size ? "" : sc.size)}
              disabled={sc.in_stock === 0 && size !== sc.size}
              title={`${sc.in_stock} item${sc.in_stock === 1 ? "" : "s"} in stock in ${sc.size}`}
            >
              {sc.size} <span>{sc.in_stock}</span>
            </button>
          ))}
        </div>
      </div>

      {hasFilters && (
        <div className="active-filters">
          Showing {products.length} {products.length === 1 ? "item" : "items"}
          {category && ` in ${category}`}
          {size && `, in stock in ${size}`}
          {q && ` matching “${q}”`}
          <button onClick={clearFilters}>Clear all filters</button>
        </div>
      )}

      {error && <div className="notice notice--error">⚠️ {error}</div>}

      <div className="product-grid">
        {products.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
      {!loading && !error && products.length === 0 && (
        <p className="empty">No products match that search. Try a different word or category.</p>
      )}
    </div>
  );
}
