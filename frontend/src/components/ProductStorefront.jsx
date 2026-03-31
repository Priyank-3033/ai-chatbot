function getTagTone(tag) {
  const normalized = tag.toLowerCase();
  if (normalized.includes("camera")) return "camera";
  if (normalized.includes("gaming")) return "gaming";
  if (normalized.includes("battery")) return "battery";
  if (normalized.includes("audio") || normalized.includes("bass") || normalized.includes("call")) return "audio";
  if (normalized.includes("fitness") || normalized.includes("health") || normalized.includes("workout")) return "health";
  if (normalized.includes("budget") || normalized.includes("value") || normalized.includes("student") || normalized.includes("office")) return "value";
  if (normalized.includes("creator") || normalized.includes("premium")) return "premium";
  return "default";
}

function getRatingTone(rating) {
  if (rating >= 4.7) return "excellent";
  if (rating >= 4.4) return "strong";
  if (rating >= 4.2) return "good";
  return "value";
}

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

function ProductTile({ product, saved, onViewDetails, onToggleWishlist, onAddToCart, onAsk, compact = false }) {
  const tagTone = getTagTone(product.tag);
  const ratingTone = getRatingTone(product.rating);
  const salePercent = getSalePercent(product);
  const originalPrice = getOriginalPrice(product.price, salePercent);

  return (
    <article className={`product-card ${compact ? "collection-card" : ""}`}>
      <div className="product-media">
        <img src={product.image} alt={product.name} />
        <div className="product-media-overlay">
          <span className="product-media-chip">{product.stock > 0 ? `${product.stock} ready to ship` : "Out of stock"}</span>
          <button className={`wishlist-floating ${saved ? "saved" : ""}`} onClick={() => onToggleWishlist(product.id)} type="button">
            {saved ? "Saved" : "Save"}
          </button>
        </div>
        <div className="product-media-footer">
          <span className="sale-badge">{salePercent}% off</span>
        </div>
      </div>
      <div className="product-body">
        <div className="product-topline">
          <span className={`product-tag product-tag--${tagTone}`}>{product.tag}</span>
          <span className={`product-rating product-rating--${ratingTone}`}>{product.rating.toFixed(1)} / 5</span>
        </div>
        <h3>{product.name}</h3>
        <p className="product-brand">{product.brand} • {product.storage}</p>
        <p className="product-description">{product.description}</p>
        <div className="feature-list">
          {product.features.slice(0, compact ? 2 : 3).map((feature) => (
            <span key={feature}>{feature}</span>
          ))}
        </div>
        <div className="product-footer">
          <div className="price-stack">
            <strong>Rs {product.price.toLocaleString("en-IN")}</strong>
            <span className="old-price">Rs {originalPrice.toLocaleString("en-IN")}</span>
          </div>
          <div className="product-actions">
            <button onClick={() => onViewDetails(product.id)} type="button">
              View details
            </button>
            <button className="secondary-button" onClick={() => onAddToCart(product.id)} type="button">
              Add to cart
            </button>
            <button className="secondary-button" onClick={() => onAsk(`Show me details about ${product.name}`)} type="button">
              Ask AI
            </button>
          </div>
        </div>
        <div className="product-note-row">
          <span>{product.delivery_note}</span>
          <span>SKU {product.sku}</span>
        </div>
      </div>
    </article>
  );
}

export default function ProductStorefront({
  products,
  productSearch,
  setProductSearch,
  category,
  setCategory,
  onAsk,
  onAddToCart,
  onViewDetails,
  onToggleWishlist,
  wishlistIds,
}) {
  const categoryOptions = [
    ["all", "All products"],
    ["phone", "Phones"],
    ["laptop", "Laptops"],
    ["tablet", "Tablets"],
    ["watch", "Watches"],
    ["accessory", "Accessories"],
  ];

  const brandList = [...new Set(products.map((product) => product.brand))].slice(0, 8);
  const featuredProducts = products.slice(0, 6);
  const dealProducts = products
    .filter((product) => product.price <= 20000 || product.rating >= 4.6 || /budget|value|deal|pick|choice/i.test(product.tag))
    .slice(0, 4);
  const phoneCount = products.filter((product) => product.category === "phone").length;
  const laptopCount = products.filter((product) => product.category === "laptop").length;
  const tabletCount = products.filter((product) => product.category === "tablet").length;
  const watchCount = products.filter((product) => product.category === "watch").length;

  const collections = [
    { key: "laptop", title: "Laptop collection", subtitle: "Work, study, and gaming machines with more room to compare.", items: products.filter((product) => product.category === "laptop").slice(0, 4) },
    { key: "tablet", title: "Tablet collection", subtitle: "Portable screens for notes, creativity, reading, and entertainment.", items: products.filter((product) => product.category === "tablet").slice(0, 4) },
    { key: "watch", title: "Smartwatch collection", subtitle: "Fitness, notifications, and style-focused wearables in one strip.", items: products.filter((product) => product.category === "watch").slice(0, 4) },
  ];

  return (
    <section className="storefront-card">
      <div className="storefront-hero">
        <div className="storefront-hero-copy">
          <p className="eyebrow">Curated storefront</p>
          <h2>Designed for faster discovery</h2>
          <p>
            Explore a sharper store layout with category banners, featured deals,
            brand navigation, and separate collections that feel closer to a real ecommerce homepage.
          </p>
          <div className="storefront-pills">
            <span>AI assisted search</span>
            <span>Featured deals</span>
            <span>Shop by brand</span>
          </div>
        </div>
        <div className="storefront-stats storefront-stats-wide">
          <article>
            <strong>{products.length}</strong>
            <span>Products live</span>
          </article>
          <article>
            <strong>{phoneCount}</strong>
            <span>Phones</span>
          </article>
          <article>
            <strong>{laptopCount}</strong>
            <span>Laptops</span>
          </article>
          <article>
            <strong>{tabletCount}</strong>
            <span>Tablets</span>
          </article>
          <article>
            <strong>{watchCount}</strong>
            <span>Watches</span>
          </article>
          <article>
            <strong>{brandList.length}</strong>
            <span>Brands</span>
          </article>
        </div>
      </div>

      <div className="category-banner-grid">
        {categoryOptions.map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={`category-banner ${category === value ? "active" : ""}`}
            onClick={() => setCategory(value)}
          >
            <span className="category-banner-title">{label}</span>
            <span className="category-banner-meta">{value === "all" ? `${products.length} visible now` : `Browse ${label.toLowerCase()}`}</span>
          </button>
        ))}
      </div>

      <section className="deal-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Featured deals</p>
            <h3>Strong value picks this week</h3>
          </div>
          <button type="button" className="secondary-button section-action" onClick={() => setCategory("all")}>See all</button>
        </div>
        <div className="deal-grid">
          {dealProducts.map((product) => (
            <div key={product.id} className="deal-card">
              <div>
                <span className={`product-tag product-tag--${getTagTone(product.tag)}`}>{product.tag}</span>
                <h4>{product.name}</h4>
                <p>{product.description}</p>
              </div>
              <div className="deal-card-footer">
                <strong>Rs {product.price.toLocaleString("en-IN")}</strong>
                <button type="button" onClick={() => onViewDetails(product.id)}>Open</button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="brand-strip-card">
        <div className="section-heading-row brand-strip-head">
          <div>
            <p className="eyebrow">Brand strip</p>
            <h3>Jump into a brand faster</h3>
          </div>
        </div>
        <div className="brand-strip">
          {brandList.map((brand) => (
            <button key={brand} type="button" className="brand-chip" onClick={() => setProductSearch(brand)}>
              {brand}
            </button>
          ))}
        </div>
      </section>

      <div className="storefront-head">
        <div>
          <p className="eyebrow">Featured products</p>
          <h2>Main spotlight grid</h2>
          <p className="storefront-subcopy">Pick a product, open details, save it, or let the AI explain what fits best.</p>
        </div>
        <div className="storefront-filters">
          <input
            type="text"
            value={productSearch}
            onChange={(event) => setProductSearch(event.target.value)}
            placeholder="Search products..."
          />
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            {categoryOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="product-grid">
        {featuredProducts.map((product) => (
          <ProductTile
            key={product.id}
            product={product}
            saved={wishlistIds.includes(product.id)}
            onViewDetails={onViewDetails}
            onToggleWishlist={onToggleWishlist}
            onAddToCart={onAddToCart}
            onAsk={onAsk}
          />
        ))}
      </div>

      <div className="collection-stack">
        {collections.map((collection) => (
          collection.items.length > 0 ? (
            <section key={collection.key} className="collection-section">
              <div className="section-heading-row">
                <div>
                  <p className="eyebrow">{collection.key} collection</p>
                  <h3>{collection.title}</h3>
                  <p className="storefront-subcopy">{collection.subtitle}</p>
                </div>
                <button type="button" className="secondary-button section-action" onClick={() => setCategory(collection.key)}>
                  Open {collection.key}
                </button>
              </div>
              <div className="collection-grid">
                {collection.items.map((product) => (
                  <ProductTile
                    key={product.id}
                    product={product}
                    saved={wishlistIds.includes(product.id)}
                    onViewDetails={onViewDetails}
                    onToggleWishlist={onToggleWishlist}
                    onAddToCart={onAddToCart}
                    onAsk={onAsk}
                    compact
                  />
                ))}
              </div>
            </section>
          ) : null
        ))}
      </div>
    </section>
  );
}
