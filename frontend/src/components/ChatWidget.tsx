import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, matchPath, useLocation, useNavigate } from "react-router-dom";
import Markdown from "react-markdown";
import {
  fetchChatHistory,
  fetchProduct,
  formatPrice,
  imageFrame,
  imageSrc,
  sendChatMessage,
  type ChatTurn,
  type PageContext,
  type PageResults,
  type Product,
} from "../api";
import { useAuth } from "../auth";
import { useChatResults } from "../chatResults";
import { ASSISTANT_NAME, MASCOT_FULL, MASCOT_HEAD, displayName } from "../brand";

const TEASER_KEY = "cc_dan_teaser_seen";

interface ChatMessage extends ChatTurn {
  products?: Product[];
  pageResults?: PageResults | null;
  quickReplies?: string[];
}

const SUGGESTIONS = [
  "Do you have navy hoodies in M?",
  "What's your cheapest quarter-zip?",
  "Show me Saybrook gear",
];

function ProductChip({ product }: { product: Product }) {
  return (
    <Link to={`/products/${product.product_id}`} className="chat-product">
      <img src={imageSrc(product)} alt="" loading="lazy" style={imageFrame(product)} />
      <span className="chat-product__name">{displayName(product.name)}</span>
      <span className="chat-product__price">{formatPrice(product.price)}</span>
    </Link>
  );
}

export default function ChatWidget() {
  const { user, token } = useAuth();
  const { show: showOnPage } = useChatResults();
  const navigate = useNavigate();
  const location = useLocation();
  const viewingId = matchPath("/products/:productId", location.pathname)?.params.productId ?? null;
  const [viewing, setViewing] = useState<Product | null>(null);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // Logged in: restore saved conversation from the DB. Logged out: start fresh.
  useEffect(() => {
    setMessages([]);
    setError(null);
    if (!token) return;
    let cancelled = false;
    fetchChatHistory(token)
      .then((rows) => {
        if (!cancelled) setMessages(rows.map(({ role, content, products }) => ({ role, content, products })));
      })
      .catch(() => {
        /* history is a nice-to-have; chat still works without it */
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  // Name of the product page the customer is on, shown as context in the chat.
  useEffect(() => {
    if (!viewingId) {
      setViewing(null);
      return;
    }
    let cancelled = false;
    fetchProduct(viewingId)
      .then((p) => !cancelled && setViewing(p))
      .catch(() => !cancelled && setViewing(null));
    return () => {
      cancelled = true;
    };
  }, [viewingId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open, loading]);

  // Other parts of the site can open the chat (and ask a first question) via openChat().
  const [pending, setPending] = useState<string | null>(null);
  useEffect(() => {
    function onOpen(e: Event) {
      const message = (e as CustomEvent<{ message?: string }>).detail?.message;
      setOpen(true);
      if (message) setPending(message);
    }
    window.addEventListener("cc:open-chat", onOpen);
    return () => window.removeEventListener("cc:open-chat", onOpen);
  }, []);
  useEffect(() => {
    if (pending && !loading) {
      setPending(null);
      void send(pending);
    }
    // send is recreated each render; pending is the trigger.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending, loading]);

  // A one-time "Ask Handsome Dan" teaser next to the launcher, per browser session.
  const [teaser, setTeaser] = useState(() => !sessionStorage.getItem(TEASER_KEY));
  useEffect(() => {
    if (open && teaser) {
      sessionStorage.setItem(TEASER_KEY, "1");
      setTeaser(false);
    }
  }, [open, teaser]);

  const greeting = user
    ? `Hi ${user.first_name}! I'm ${ASSISTANT_NAME}, the Campus Customs bulldog. Ask me about products, sizes, or prices.`
    : `Hi there! I'm ${ASSISTANT_NAME}, the Campus Customs bulldog. Ask me about products, sizes, or prices.`;

  async function send(text: string) {
    const message = text.trim();
    if (!message || loading) return;
    const history: ChatTurn[] = messages.map(({ role, content, products }) => ({
      role,
      content,
      product_ids: products?.map((p) => p.product_id) ?? [],
    }));
    const page: PageContext = { path: location.pathname + location.search, product_id: viewingId };

    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const res = await sendChatMessage(message, token, history, page);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply,
          products: res.products,
          pageResults: res.page_results,
          quickReplies: res.quick_replies,
        },
      ]);
      if (res.page_results) openOnPage(res.page_results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  // Search results from the agent update the Products page (chat stays open).
  function openOnPage(results: PageResults) {
    showOnPage(results);
    navigate("/products?view=chat");
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  return (
    <div className="chat-widget">
      {open && (
        <section className="chat-window" aria-label={`${ASSISTANT_NAME}, Campus Customs shopping assistant`}>
          <header className="chat-window__header">
            <img className="chat-avatar" src={MASCOT_HEAD} alt="" />
            <div className="chat-window__title">
              <h2>{ASSISTANT_NAME}</h2>
              <span>{user ? "Campus Customs assistant · chats saved" : "Campus Customs assistant · log in to save chats"}</span>
            </div>
            <button aria-label="Close chat" onClick={() => setOpen(false)}>
              ✕
            </button>
          </header>

          <div className="chat-window__messages">
            <div className="chat-welcome">
              <div className="chat-welcome__art">
                <img src={MASCOT_FULL} alt="" />
              </div>
              <strong>{ASSISTANT_NAME}</strong>
              <p>{greeting}</p>
            </div>
            {messages.length === 0 && (
              <div className="chat-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => void send(s)} disabled={loading}>
                    {s}
                  </button>
                ))}
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`chat-message chat-message--${m.role}`}>
                {m.role === "assistant" && <img className="chat-message__avatar" src={MASCOT_HEAD} alt="" />}
                <div className={`chat-bubble chat-bubble--${m.role}`}>
                  {m.role === "assistant" ? <Markdown>{m.content}</Markdown> : m.content}
                </div>
                {m.quickReplies && m.quickReplies.length > 0 && i === messages.length - 1 && !loading && (
                  <div className="chat-quick-replies" aria-label="Suggested answers">
                    {m.quickReplies.map((q) => (
                      <button key={q} onClick={() => void send(q)}>
                        {q}
                      </button>
                    ))}
                  </div>
                )}
                {m.pageResults && (
                  <button className="chat-page-link" onClick={() => openOnPage(m.pageResults!)}>
                    📋 {m.pageResults.total} result{m.pageResults.total === 1 ? "" : "s"} shown on the page: view
                  </button>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat-products">
                    {m.products.map((p) => (
                      <ProductChip key={p.product_id} product={p} />
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="chat-message chat-message--assistant">
                <img className="chat-message__avatar" src={MASCOT_HEAD} alt="" />
                <div className="chat-bubble chat-bubble--assistant chat-bubble--typing" aria-label={`${ASSISTANT_NAME} is typing`}>
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
            {error && <div className="chat-bubble chat-bubble--error">⚠️ {error}</div>}
            <div ref={endRef} />
          </div>

          {viewing && (
            <div className="chat-context" title={`${ASSISTANT_NAME} knows which product you're viewing`}>
              👀 Viewing: <strong>{displayName(viewing.name)}</strong>
              <span>Ask “Is this in M?”</span>
            </div>
          )}
          <form className="chat-window__form" onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask ${ASSISTANT_NAME} about products, sizes…`}
              aria-label="Message"
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()}>
              {loading ? "…" : "Send"}
            </button>
          </form>
        </section>
      )}

      <div className="chat-launcher-row">
        {!open && teaser && (
          <button className="chat-teaser" onClick={() => setOpen(true)}>
            Ask {ASSISTANT_NAME} 🐾
            <span>Sizes, stock &amp; gift ideas</span>
          </button>
        )}
        <button
          className="chat-launcher"
          aria-label={open ? `Close chat with ${ASSISTANT_NAME}` : `Chat with ${ASSISTANT_NAME}`}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? (
            <span className="chat-launcher__close">✕</span>
          ) : (
            <>
              <img src={MASCOT_HEAD} alt="" />
              <span className="chat-launcher__dot" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
