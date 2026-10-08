import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchCategories, fetchProducts, imageFrame, imageSrc, type Category, type Product } from "../api";
import { MASCOT_FULL, RESIDENTIAL_COLLEGES, SCHOOLS, SPORTS, displayName, openChat } from "../brand";
import ProductCard from "../components/ProductCard";

// Hero collage: a dark, a light, and a classic piece so the backdrops alternate.
const HERO_IDS = ["basic-hoodie-big-yale", "champion-reverse-weave-crewneck", "district-vit-crewneck-vintage-standing-bulldog"];
const FEATURED_IDS = [
  "yale-law-school-1-4-zip",
  "district-vit-hoodie-vintage-bulldog",
  "saybrook-college-crewneck",
  "brooks-brothers-bomber-jacket-yale",
];
const GAME_ID = "2025-yale-vs-harvard-t-shirt";

const TRUST = [
  { icon: "🏛️", title: "Family-run since 1975", text: "On Broadway, steps from campus" },
  { icon: "🧵", title: "Printed & stitched in-house", text: "Screen printing and embroidery" },
  { icon: "🎓", title: "Every corner of Yale", text: "Colleges, schools & varsity teams" },
  { icon: "💬", title: "Ask Handsome Dan", text: "Sizes and stock, answered fast" },
];

const DAN_PROMPTS = ["What's good for game day?", "Show me Saybrook gear", "Gift for my dad"];

const search = (q: string) => `/products?q=${encodeURIComponent(q)}`;

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchProducts(), fetchCategories()])
      .then(([p, c]) => {
        setProducts(p.products);
        setCategories(c);
      })
      .catch((err) => setError(`${err.message}. Is the backend running on port 8000?`));
  }, []);

  const byId = (id: string) => products.find((p) => p.product_id === id);
  const hero = HERO_IDS.map(byId).filter((p): p is Product => Boolean(p));
  const featured = FEATURED_IDS.map(byId).filter((p): p is Product => Boolean(p));
  const game = byId(GAME_ID);
  const coverFor = (category: string) => products.find((p) => p.category === category);

  return (
    <>
      {/* ---------- Hero ---------- */}
      <section className="hero bleed">
        <div className="hero__inner bleed__inner">
          <div>
            <span className="kicker">Campus Customs · New Haven</span>
            <h1>
              Wear Yale. <em>Every&nbsp;day.</em>
            </h1>
            <p className="hero__lede">
              Hoodies, crewnecks, quarter-zips and tees for every residential college, professional school and varsity
              team, printed and stitched just off Old Campus.
            </p>
            <div className="hero__actions">
              <Link to="/products" className="btn btn--light">
                Shop the collection
              </Link>
              <button className="btn btn--ghost-light" onClick={() => openChat()}>
                Ask Handsome Dan
              </button>
            </div>
            <div className="hero__stats">
              <div>
                <strong>1975</strong>
                <span>On Broadway since</span>
              </div>
              <div>
                <strong>{products.length || "100+"}</strong>
                <span>Yale styles</span>
              </div>
              <div>
                <strong>XS–XXL</strong>
                <span>Every size</span>
              </div>
            </div>
          </div>

          <div className="hero__visual" aria-hidden={hero.length === 0}>
            {hero.map((p, i) => (
              <Link
                key={p.product_id}
                to={`/products/${p.product_id}`}
                className={`hero__card hero__card--${i + 1}`}
                style={imageFrame(p)}
                aria-label={displayName(p.name)}
              >
                <img src={imageSrc(p)} alt="" />
                {i === 0 && <span className="hero__tag">{displayName(p.name)}</span>}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- Trust strip ---------- */}
      <section className="trust bleed">
        <div className="trust__inner bleed__inner">
          {TRUST.map((t) => (
            <div key={t.title} className="trust__item">
              <span className="trust__icon" aria-hidden>
                {t.icon}
              </span>
              <div>
                <strong>{t.title}</strong>
                <span>{t.text}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {error && <div className="notice notice--error">⚠️ {error}</div>}

      {/* ---------- Categories ---------- */}
      <section className="section">
        <div className="section__head">
          <div>
            <span className="kicker">Shop by category</span>
            <h2>Find your fit</h2>
          </div>
          <Link to="/products">View all products</Link>
        </div>
        <div className="category-grid">
          {categories.map((c) => {
            const cover = coverFor(c.name);
            return (
              <Link
                key={c.name}
                to={`/products?category=${encodeURIComponent(c.name)}`}
                className="category-tile"
                style={cover ? imageFrame(cover) : undefined}
              >
                {cover && <img src={imageSrc(cover)} alt="" loading="lazy" />}
                <span className="category-tile__label">
                  <b>{c.name}</b>
                  <small>{c.count} styles</small>
                </span>
              </Link>
            );
          })}
        </div>
      </section>

      {/* ---------- Explore: colleges, schools, sports ---------- */}
      <section className="section">
        <div className="section__head">
          <div>
            <span className="kicker">Represent</span>
            <h2>Your college. Your school. Your team.</h2>
          </div>
        </div>
        <div className="explore">
          <div className="explore__col">
            <h3>Residential Colleges</h3>
            <p>Crests and crewnecks for the house you call home.</p>
            <div className="pill-cloud">
              {RESIDENTIAL_COLLEGES.map((c) => (
                <Link key={c} to={search(c)} className="pill">
                  {c}
                </Link>
              ))}
            </div>
          </div>
          <div className="explore__col">
            <h3>Graduate &amp; Professional Schools</h3>
            <p>Quarter-zips and fleece for the next chapter.</p>
            <div className="pill-cloud">
              {SCHOOLS.map((s) => (
                <Link key={s.label} to={search(s.q)} className="pill">
                  {s.label}
                </Link>
              ))}
            </div>
          </div>
          <div className="explore__col">
            <h3>Bulldog Athletics</h3>
            <p>Cheer on the Bulldogs, from the Bowl to Ingalls Rink.</p>
            <div className="pill-cloud">
              {SPORTS.map((s) => (
                <Link key={s} to={search(s)} className="pill">
                  {s}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ---------- The Game feature ---------- */}
      {game && (
        <section className="section">
          <div className="feature">
            <div className="feature__copy">
              <span className="kicker">Harvard–Yale · The Game</span>
              <h2>Gear up for The Game.</h2>
              <p>
                The rivalry that started in 1875. Show up in Bulldog blue, from the tailgate to the final whistle.
              </p>
              <div className="feature__actions">
                <Link to={`/products/${game.product_id}`} className="btn btn--light">
                  Shop The Game tee
                </Link>
                <Link to={search("football")} className="btn btn--ghost-light">
                  Game day gear
                </Link>
              </div>
            </div>
            <Link to={`/products/${game.product_id}`} className="feature__image" style={imageFrame(game)}>
              <img src={imageSrc(game)} alt={displayName(game.name)} />
            </Link>
          </div>
        </section>
      )}

      {/* ---------- Featured products ---------- */}
      {featured.length > 0 && (
        <section className="section">
          <div className="section__head">
            <div>
              <span className="kicker">Campus favorites</span>
              <h2>Classics worth wearing out</h2>
            </div>
            <Link to="/products">Shop all</Link>
          </div>
          <div className="product-grid">
            {featured.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      )}

      {/* ---------- Meet Handsome Dan ---------- */}
      <section className="section">
        <div className="dan-promo">
          <div className="dan-promo__art">
            <img src={MASCOT_FULL} alt="Handsome Dan, the Yale bulldog, in a Y sweater" />
          </div>
          <div>
            <span className="kicker">Your shopping assistant</span>
            <h2>Ask Handsome Dan.</h2>
            <p>
              Not sure about a size, a color, or which crewneck says “Saybrook” best? Dan knows every rack in the shop
              and checks live stock before he answers.
            </p>
            <div className="dan-promo__prompts">
              {DAN_PROMPTS.map((q) => (
                <button key={q} onClick={() => openChat(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
          <button className="btn btn--primary" onClick={() => openChat()}>
            Start a chat
          </button>
        </div>
      </section>

      {/* ---------- Heritage ---------- */}
      <section className="heritage bleed">
        <div className="heritage__inner bleed__inner">
          <div className="heritage__year">
            1975
            <small>On Broadway since</small>
          </div>
          <div>
            <span className="kicker">Our story</span>
            <h2>A New Haven family business, one shirt at a time.</h2>
            <p>
              Campus Customs began as a small Yale memorabilia shop across from campus. Five decades later, a second
              generation still runs it from Broadway, printing, stitching, and outfitting Elis, families and fans.
            </p>
            <Link to="/about" className="btn btn--outline">
              Read our story
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
