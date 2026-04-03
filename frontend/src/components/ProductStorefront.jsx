import { useMemo, useState } from "react";
import { getProductImageSources } from "../utils/productVisuals";

const CATEGORY_ICONS = {
  all: "All",
  phone: "Mob",
  laptop: "Ele",
  tablet: "Std",
  watch: "Wr",
  accessory: "Acc",
};

function getSalePercent(product) {
  const normalized = product.tag.toLowerCase();
  if (normalized.includes("budget") || normalized.includes("value")) return 22;
  if (normalized.includes("premium") || normalized.includes("creator")) return 12;
  if (normalized.includes("gaming")) return 18;
  if (product.category === "accessory" || product.category === "watch") return 20;
  if (product.category === "laptop") return 16;
  return 15;
}

function getOriginalPrice(price, salePercent) {
  return Math.round(price / (1 - salePercent / 100) / 100) * 100;
}

function ProductTile({ product, saved, onViewDetails, onToggleWishlist, onAddToCart }) {
  const salePercent = getSalePercent(product);
  const originalPrice = getOriginalPrice(product.price, salePercent);
  const imageSources = getProductImageSources(product);
  const [imageIndex, setImageIndex] = useState(0);

  return (
    <article className="product-card simple-store-card minimal-product-card">
      <div className="product-media minimal-product-media">
        <img
          src={imageSources[imageIndex] || ""}
          alt={product.name}
          loading="lazy"
          onError={() => setImageIndex((current) => Math.min(current + 1, imageSources.length - 1))}
        />
        <div className="product-media-overlay">
          <span className="product-media-chip">{product.stock > 0 ? `${product.stock} in stock` : "Out of stock"}</span>
          <button className={`wishlist-floating ${saved ? "saved" : ""}`} onClick={() => onToggleWishlist(product.id)} type="button">
            {saved ? "Saved" : "Save"}
          </button>
        </div>
        <div className="product-media-footer">
          <span className="sale-badge">{salePercent}% off</span>
        </div>
      </div>
      <div className="product-body minimal-product-body">
        <h3>{product.name}</h3>
        <p className="product-brand">{product.brand}</p>
        <div className="minimal-product-meta-line">
          <span className="minimal-meta-pill">{product.rating.toFixed(1)} / 5</span>
          <span className="minimal-meta-pill">{product.delivery_note}</span>
        </div>
        <div className="product-footer minimal-product-footer">
          <div className="price-stack">
            <strong>Rs {product.price.toLocaleString("en-IN")}</strong>
            <span className="old-price">Rs {originalPrice.toLocaleString("en-IN")}</span>
          </div>
          <div className="product-actions minimal-product-actions">
            <button onClick={() => onViewDetails(product.id)} type="button">View</button>
            <button className="secondary-button" onClick={() => onAddToCart(product.id)} type="button">Add to cart</button>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function ProductStorefront({
  products,
  productTotal,
  productPage,
  onPageChange,
  pageSize = 12,
  productSearch,
  setProductSearch,
  productSuggestions = [],
  category,
  setCategory,
  onAddToCart,
  onViewDetails,
  onToggleWishlist,
  wishlistIds,
}) {
  const categoryOptions = [
    { key: "all", label: "Everything" },
    { key: "phone", label: "Mobiles" },
    { key: "laptop", label: "Electronics" },
    { key: "tablet", label: "Study Tech" },
    { key: "watch", label: "Wearables" },
    { key: "accessory", label: "Accessories" },
  ];

  const visibleProducts = useMemo(() => {
    return products;
  }, [products]);

  const totalPages = Math.max(1, Math.ceil(productTotal / pageSize));

  return (
    <section className="storefront-card simple-storefront-card compact-top-storefront">
      <div className="storefront-head simple-storefront-head compact-topbar-head">
        <div>
          <p className="eyebrow">Store and orders</p>
          <h2>Browse products</h2>
        </div>
      </div>

      <div className="simple-category-strip icon-category-strip">
        {categoryOptions.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`simple-category-chip ${category === item.key ? "active" : ""}`}
            onClick={() => setCategory(item.key)}
          >
            <span className="simple-category-icon">{CATEGORY_ICONS[item.key]}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </div>

      <div className="storefront-filters simple-storefront-filters compact-storefront-filters">
        <input
          type="text"
          value={productSearch}
          onChange={(event) => setProductSearch(event.target.value)}
          placeholder="Search products..."
        />
        {productSuggestions.length ? (
          <div className="search-suggestion-list">
            {productSuggestions.map((suggestion) => (
              <button key={suggestion} type="button" className="search-suggestion-chip" onClick={() => setProductSearch(suggestion)}>
                {suggestion}
              </button>
            ))}
          </div>
        ) : null}
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          {categoryOptions.map((item) => (
            <option key={item.key} value={item.key}>{item.label}</option>
          ))}
        </select>
      </div>

      <div className="product-grid simple-product-grid compact-product-grid">
        {visibleProducts.map((product) => (
          <ProductTile
            key={product.id}
            product={product}
            saved={wishlistIds.includes(product.id)}
            onViewDetails={onViewDetails}
            onToggleWishlist={onToggleWishlist}
            onAddToCart={onAddToCart}
          />
        ))}
      </div>

      {productTotal > pageSize ? (
        <div className="product-pagination">
          <button type="button" onClick={() => onPageChange(Math.max(1, productPage - 1))} disabled={productPage <= 1}>
            Prev
          </button>
          <span>Page {productPage} of {totalPages}</span>
          <button type="button" onClick={() => onPageChange(Math.min(totalPages, productPage + 1))} disabled={productPage >= totalPages}>
            Next
          </button>
        </div>
      ) : null}

      {visibleProducts.length === 0 ? (
        <div className="simple-store-empty">
          <h3>No products found</h3>
          <p>Try a different search or switch to another category.</p>
        </div>
      ) : null}
    </section>
  );
}
