import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchProduct, fetchProducts, formatPrice, imageFrame, imageSrc, type Product } from "../api";
import ProductCard from "../components/ProductCard";
import { displayName, openChat, swatch } from "../brand";

export default function ProductDetail() {
  const { productId = "" } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [related, setRelated] = useState<Product[]>([]);
  const [size, setSize] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProduct(null);
    setSize(null);
    setError(null);
    fetchProduct(productId)
      .then((p) => {
        setProduct(p);
        return fetchProducts({ category: p.category });
      })
      .then((res) => setRelated(res.products.filter((r) => r.product_id !== productId).slice(0, 4)))
      .catch((err) => setError(err.message));
  }, [productId]);

  if (error) {
    return (
      <div className="page">
        <div className="notice notice--error">⚠️ {error}</div>
        <Link to="/products">← Back to products</Link>
      </div>
    );
  }
  if (!product) return <div className="page">Loading…</div>;

  const selected = product.inventory.find((i) => i.size === size);
  const name = displayName(product.name);

  return (
    <div className="page">
      <nav className="breadcrumb">
        <Link to="/products">Products</Link> /{" "}
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link> /{" "}
        <span>{name}</span>
      </nav>

      <div className="detail">
        <div className="detail__image" style={imageFrame(product)}>
          <img src={imageSrc(product)} alt={name} />
        </div>

        <div className="detail__info">
          <span className="product-card__category">{product.garment_type}</span>
          <h1>{name}</h1>
          <p className="detail__price">{formatPrice(product.price)}</p>
          <p className="detail__desc">{product.description}</p>

          {product.colors.length > 0 && (
            <div className="detail__block">
              <h4>Colors on this item</h4>
              <div className="tags">
                {product.colors.map((c) => (
                  <span key={c} className="tag">
                    <span className="swatch" style={{ background: swatch(c) }} />
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="detail__block">
            <h4>Size</h4>
            <div className="sizes">
              {product.inventory.map((i) => (
                <button
                  key={i.size}
                  className={`size ${size === i.size ? "size--active" : ""}`}
                  disabled={i.quantity === 0}
                  title={i.quantity === 0 ? "Sold out" : `${i.quantity} in stock`}
                  onClick={() => setSize(i.size)}
                >
                  {i.size}
                </button>
              ))}
            </div>
            <p className={`detail__stock ${selected && selected.quantity <= 5 ? "detail__stock--low" : ""}`}>
              {selected
                ? selected.quantity <= 5
                  ? `Only ${selected.quantity} left in ${selected.size}!`
                  : `In stock in ${selected.size} (${selected.quantity} available)`
                : `${product.total_stock} in stock across all sizes. Crossed-out sizes are sold out.`}
            </p>
          </div>

          <div className="detail__actions">
            <button className="btn btn--primary" onClick={() => openChat(`Is this available in ${size ?? "my size"}?`)}>
              Ask Handsome Dan about this
            </button>
            <Link to={`/products?category=${encodeURIComponent(product.category)}`} className="btn btn--outline">
              More {product.category}
            </Link>
          </div>

          <ul className="detail__assurance">
            <li>Sold by Campus Customs, a family-run Yale outfitter on Broadway since 1975</li>
            <li>Live stock shown per size, so what you see is what’s on the shelf</li>
            <li>Try it on in person, steps from Yale’s campus</li>
          </ul>

          <div className="detail__block">
            <h4>Tags</h4>
            <div className="tags">
              {product.search_tags.map((t) => (
                <span key={t} className="tag tag--muted">
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {related.length > 0 && (
        <section className="section">
          <div className="section__head">
            <h2>More {product.category}</h2>
          </div>
          <div className="product-grid">
            {related.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
