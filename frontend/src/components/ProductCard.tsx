import { Link } from "react-router-dom";
import { formatPrice, imageFrame, imageSrc, type Product } from "../api";
import { displayName, swatch } from "../brand";

export default function ProductCard({ product }: { product: Product }) {
  const name = displayName(product.name);
  const lowSizes = product.inventory.filter((i) => i.quantity > 0 && i.quantity <= 5).length;
  const badge = product.total_stock === 0 ? "Sold out" : lowSizes >= 2 ? "Selling fast" : null;

  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card__image" style={imageFrame(product)}>
        <img src={imageSrc(product)} alt={name} loading="lazy" />
        {badge && <span className="product-card__badge">{badge}</span>}
        <span className="product-card__cta">View details</span>
      </div>
      <div className="product-card__body">
        <span className="product-card__category">{product.category}</span>
        <h3 className="product-card__name">{name}</h3>
        <p className="product-card__desc">{product.description}</p>
        <div className="product-card__sizes" aria-label="Sizes">
          {product.inventory.map((i) => (
            <span key={i.size} className={i.quantity === 0 ? "is-out" : undefined} title={i.quantity === 0 ? "Sold out" : "In stock"}>
              {i.size}
            </span>
          ))}
        </div>
        <div className="product-card__meta">
          <span className="product-card__price">{formatPrice(product.price)}</span>
          {product.colors.length > 0 && (
            <span className="swatches" aria-label={`Colors: ${product.colors.join(", ")}`}>
              {product.colors.slice(0, 4).map((c) => (
                <span key={c} className="swatch" style={{ background: swatch(c) }} title={c} />
              ))}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
