// In dev this is unset, so it falls back to the local backend. In prod set
// VITE_API_BASE to the backend's public URL.
export const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

/** Mirrors db.build_product in backend/db.py (see output/harness.md). */
export interface InventoryItem {
  size: string;
  quantity: number;
}

export interface Product {
  product_id: string;
  name: string;
  garment_type: string;
  category: string;
  description: string;
  colors: string[];
  search_tags: string[];
  image_file_path: string;
  image_url: string;
  /** Background-removed cutout (falls back to the original photo). */
  display_image_url?: string;
  /** Backdrop that contrasts with the garment: white for dark merch, charcoal for light merch. */
  image_bg?: string;
  price: number;
  inventory: InventoryItem[];
  total_stock: number;
}

export interface ProductsResponse {
  count: number;
  products: Product[];
}

export interface Category {
  name: string;
  count: number;
}

export interface User {
  id: number;
  name: string;
  first_name: string;
  last_name: string;
  email: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export type SortKey = "name" | "price_asc" | "price_desc";

export const imageSrc = (p: Product) => `${API_BASE}${p.display_image_url ?? p.image_url}`;

/** Inline style for any image frame so the backdrop matches the product's cutout. */
export const imageFrame = (p: Product) => ({ background: p.image_bg ?? "#ffffff" });

export const formatPrice = (price: number) =>
  `$${price.toFixed(Number.isInteger(price) ? 0 : 2)}`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const SIZES = ["XS", "S", "M", "L", "XL", "XXL"] as const;

export interface SizeCount {
  size: string;
  in_stock: number;
}

export function fetchProducts(params: { q?: string; category?: string; size?: string; sort?: SortKey } = {}) {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.category) search.set("category", params.category);
  if (params.size) search.set("size", params.size);
  if (params.sort) search.set("sort", params.sort);
  const qs = search.toString();
  return request<ProductsResponse>(`/api/products${qs ? `?${qs}` : ""}`);
}

export const fetchProduct = (id: string) =>
  request<Product>(`/api/products/${encodeURIComponent(id)}`);

export const fetchCategories = () => request<Category[]>("/api/categories");

export const fetchSizes = (category?: string) =>
  request<SizeCount[]>(`/api/sizes${category ? `?category=${encodeURIComponent(category)}` : ""}`);

const jsonPost = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const login = (email: string, password: string) =>
  request<AuthResponse>("/api/auth/login", jsonPost({ email, password }));

export const signup = (data: { first_name: string; last_name: string; email: string; password: string }) =>
  request<AuthResponse>("/api/auth/signup", jsonPost(data));

export const fetchMe = (token: string) =>
  request<User>("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } });

// ---------- Chat agent ----------

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  /** Products shown with an assistant message (lets the agent resolve "the first one"). */
  product_ids?: string[];
}

/** Where the customer is on the site; lets the agent resolve "this"/"it". */
export interface PageContext {
  path: string;
  product_id: string | null;
}

export interface SearchFilters {
  query: string;
  category: string | null;
  min_price: number | null;
  max_price: number | null;
  size: string | null;
  color: string | null;
  sort: string;
}

/** Full search results from a chat turn, rendered as cards on the Products page. */
export interface PageResults {
  title: string;
  query: string;
  total: number;
  filters: SearchFilters[];
  products: Product[];
}

export interface ChatResponse {
  reply: string;
  products: Product[];
  page_results: PageResults | null;
  /** Tappable answers when the assistant asks a clarifying question. */
  quick_replies: string[];
  tools_used: string[];
}

export interface ChatHistoryMessage extends ChatTurn {
  id: number;
  products: Product[];
  created_at: string;
}

const authHeader = (token: string | null): Record<string, string> =>
  token ? { Authorization: `Bearer ${token}` } : {};

/** Logged-in users: the backend loads context from the DB and saves the turn.
 *  Guests: send recent turns so the agent can follow the conversation. */
export const sendChatMessage = (
  message: string,
  token: string | null,
  history: ChatTurn[] = [],
  page: PageContext | null = null,
) =>
  request<ChatResponse>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify({ message, history: token ? [] : history.slice(-20), page }),
  });

export const fetchChatHistory = (token: string) =>
  request<ChatHistoryMessage[]>("/api/chat/history", { headers: authHeader(token) });
