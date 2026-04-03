import { useEffect, useMemo, useState } from "react";
import { getLocalProductGallery, getProductImageSources, getProductPlaceholder } from "../utils/productVisuals";

export default function ProductDetailModal({ product, inWishlist, onClose, onAddToCart, onToggleWishlist, onAsk }) {
  if (!product) return null;

  const localGallery = useMemo(() => getLocalProductGallery(product), [product]);
  const [selectedImage, setSelectedImage] = useState(() => getProductImageSources(product)[0] || getProductPlaceholder(product));
  const [zoomed, setZoomed] = useState(false);

  useEffect(() => {
    setSelectedImage(getProductImageSources(product)[0] || getProductPlaceholder(product));
    setZoomed(false);
  }, [product]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="product-modal" onClick={(event) => event.stopPropagation()}>
        <button className="modal-close" onClick={onClose} type="button">x</button>
        <div className="product-modal-grid">
          <div className="product-modal-media">
            <div className={`product-modal-hero-wrap ${zoomed ? "zoomed" : ""}`}>
              <img
                src={selectedImage}
                alt={product.name}
                className="product-modal-hero"
                onClick={() => setZoomed((current) => !current)}
                onError={() => setSelectedImage(getProductPlaceholder(product))}
              />
              <span className="zoom-hint">{zoomed ? "Click image to zoom out" : "Click image to zoom"}</span>
            </div>
            <div className="product-modal-gallery">
              {localGallery.map((img, i) => (
                <img
                  key={`${product.id}-${i}`}
                  src={img}
                  alt={`${product.name} preview ${i + 1}`}
                  onClick={() => {
                    setSelectedImage(img);
                    setZoomed(false);
                  }}
                  onError={(event) => {
                    event.currentTarget.src = getProductPlaceholder(product);
                  }}
                />
              ))}
            </div>
          </div>

          <div className="product-modal-copy">
            <p className="eyebrow">{product.brand} • {product.category}</p>
            <h2>{product.name}</h2>
            <div className="product-modal-meta">
              <span className="product-tag">{product.tag}</span>
              <span className="product-rating">{product.rating.toFixed(1)} / 5</span>
              <span className="stock-pill">{product.stock > 0 ? `${product.stock} in stock` : "Out of stock"}</span>
            </div>
            <p className="detail-price">Rs {product.price.toLocaleString("en-IN")}</p>
            <p className="detail-description">{product.long_description}</p>
            <p className="delivery-note">{product.delivery_note}</p>

            <div className="feature-list detail-features">
              {product.features.map((feature) => (
                <span key={feature}>{feature}</span>
              ))}
            </div>

            <div className="detail-actions">
              <button onClick={() => onAddToCart(product.id)} type="button">Add to cart</button>
              <button className="secondary-button" onClick={() => onToggleWishlist(product.id)} type="button">
                {inWishlist ? "Remove wishlist" : "Save to wishlist"}
              </button>
              <button className="secondary-button" onClick={() => onAsk(`Compare and explain whether ${product.name} is worth buying`)} type="button">
                Ask AI
              </button>
            </div>

            <div className="spec-grid">
              {Object.entries(product.specs).map(([key, value]) => (
                <div key={key} className="spec-card">
                  <span>{key}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
