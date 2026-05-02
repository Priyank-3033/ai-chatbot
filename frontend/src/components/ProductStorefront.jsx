import { useEffect, useMemo, useState } from "react";
import { getProductImageSources } from "../utils/productVisuals";

const CATEGORY_NAV = [
  { key: "all", label: "Top Offers", short: "TO" },
  { key: "phone", label: "Mobiles", short: "PH" },
  { key: "laptop", label: "Electronics", short: "EL" },
  { key: "tablet", label: "Study Tech", short: "ST" },
  { key: "watch", label: "Wearables", short: "WR" },
  { key: "accessory", label: "Accessories", short: "AC" },
];

const HOME_SECTIONS = [
  { key: "discounts", title: "Discounts for You", tagline: "Fresh picks across the store" },
  { key: "suggested", title: "Suggested for You", tagline: "Based on what shoppers love" },
  { key: "brands", title: "Top Brands, Best Price", tagline: "Popular deals you can open now" },
  { key: "miss", title: "Don't Miss These", tagline: "Handpicked tech and accessories" },
];

const TOP_MENU_GROUPS = [
  {
    key: "electronics",
    label: "Electronics",
    groups: [
      { title: "Mobiles", items: ["Budget phones", "5G smartphones", "Camera phones"], category: "phone" },
      { title: "Laptops", items: ["Student laptops", "Gaming laptops", "Creator laptops"], category: "laptop" },
      { title: "Accessories", items: ["Chargers", "Earbuds", "Smart watches"], category: "accessory" },
    ],
  },
  {
    key: "fashion",
    label: "Fashion",
    groups: [
      { title: "Topwear", items: ["Men's T-shirts", "Shirts", "Jackets"], category: "watch" },
      { title: "Bottomwear", items: ["Jeans", "Track pants", "Shorts"], category: "watch" },
      { title: "Footwear", items: ["Sneakers", "Slides", "Running shoes"], category: "watch" },
    ],
  },
  {
    key: "home",
    label: "Home & Furniture",
    groups: [
      { title: "Living", items: ["Decor", "Lighting", "Storage"], category: "accessory" },
      { title: "Study", items: ["Desks", "Chairs", "Organizers"], category: "tablet" },
      { title: "Essentials", items: ["Cleaners", "Tools", "Kitchen"], category: "accessory" },
    ],
  },
  {
    key: "grocery",
    label: "Daily Needs",
    groups: [
      { title: "Essentials", items: ["Home supplies", "Personal care", "Stationery"], category: "all" },
      { title: "Bundles", items: ["Value packs", "Deals of the day", "Subscriptions"], category: "all" },
      { title: "Delivery", items: ["Fast shipping", "Saver offers", "Best picks"], category: "all" },
    ],
  },
];

function salePercent(product) {
  const normalized = String(product.tag || "").toLowerCase();
  if (normalized.includes("budget") || normalized.includes("value")) return 22;
  if (normalized.includes("gaming")) return 18;
  if (normalized.includes("premium") || normalized.includes("creator")) return 12;
  if (product.category === "accessory" || product.category === "watch") return 20;
  return 15;
}

function originalPrice(price, percent) {
  return Math.round(price / (1 - percent / 100) / 100) * 100;
}

function CategoryTile({ category, active, onSelect }) {
  return (
    <button type="button" className={`flipkart-category-tile ${active ? "active" : ""}`} onClick={() => onSelect(category.key, category.label)}>
      <div className={`flipkart-category-image-wrap category-${category.key}`}>
        <span className="flipkart-category-icon" aria-hidden="true">{category.short}</span>
      </div>
      <span>{category.label}</span>
    </button>
  );
}

function FrontPageProduct({ product, saved, onViewDetails, onToggleWishlist, onAddToCart }) {
  const [imageIndex, setImageIndex] = useState(0);
  const sources = getProductImageSources(product);
  const discount = salePercent(product);
  const strike = originalPrice(product.price, discount);

  return (
    <article className="flipkart-product-card">
      <button type="button" className="flipkart-product-image" onClick={() => onViewDetails(product.id)}>
        <span className="flipkart-offer-badge">{discount}% off</span>
        <img
          src={sources[imageIndex] || ""}
          alt={product.name}
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setImageIndex((current) => Math.min(current + 1, sources.length - 1))}
        />
      </button>
      <div className="flipkart-product-copy">
        <strong>{product.name}</strong>
        <span>{product.brand}</span>
        <p>{product.delivery_note}</p>
      </div>
      <div className="flipkart-price-line">
        <strong>Rs {product.price.toLocaleString("en-IN")}</strong>
        <span>{discount}% off</span>
      </div>
      <div className="flipkart-price-subline">Rs {strike.toLocaleString("en-IN")}</div>
      <div className="flipkart-product-actions">
        <button type="button" onClick={() => onViewDetails(product.id)}>View</button>
        <button type="button" className="secondary-button" onClick={() => onAddToCart(product.id)}>Add</button>
        <button type="button" className={`ghost-button ${saved ? "saved" : ""}`} onClick={() => onToggleWishlist(product.id)}>
          {saved ? "Saved" : "Save"}
        </button>
      </div>
    </article>
  );
}

function FrontPageSection({ title, tagline, products, wishlistIds, onViewDetails, onToggleWishlist, onAddToCart, onViewAll }) {
  return (
    <section className="flipkart-section-row">
      <div className="flipkart-section-head">
        <div>
          <h3>{title}</h3>
          <p>{tagline}</p>
        </div>
        <button type="button" className="flipkart-view-all" onClick={onViewAll}>VIEW ALL</button>
      </div>
      <div className="flipkart-row-scroll">
        {products.map((product) => (
          <FrontPageProduct
            key={product.id}
            product={product}
            saved={wishlistIds.includes(product.id)}
            onViewDetails={onViewDetails}
            onToggleWishlist={onToggleWishlist}
            onAddToCart={onAddToCart}
          />
        ))}
      </div>
    </section>
  );
}

export default function ProductStorefront({
  products,
  productSearch,
  setProductSearch,
  category,
  setCategory,
  onAddToCart,
  onViewDetails,
  onToggleWishlist,
  wishlistIds,
  onAsk,
  onOpenCart,
  onOpenWishlist,
  onOpenOrders,
  user,
}) {
  const [browseMode, setBrowseMode] = useState("home");
  const [activeMenu, setActiveMenu] = useState("");
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const [activeSubcategory, setActiveSubcategory] = useState("");
  const [openFilters, setOpenFilters] = useState({
    categories: true,
    offers: true,
    budget: true,
  });

  const heroProduct = products[0];
  const browseProducts = useMemo(() => products.slice(0, 20), [products]);
  const sectionProducts = useMemo(() => {
    return HOME_SECTIONS.map((section, index) => ({
      ...section,
      products: products.slice(index * 6, index * 6 + 10),
    })).filter((section) => section.products.length > 0);
  }, [products]);

  const listingTitle = useMemo(() => {
    if (activeSubcategory) return activeSubcategory;
    if (category === "phone") return "Mobile Collection";
    if (category === "laptop") return "Electronics";
    if (category === "tablet") return "Study Tech";
    if (category === "watch") return "Wearables";
    if (category === "accessory") return "Accessories";
    return "All Products";
  }, [activeSubcategory, category]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const view = params.get("view");
    const urlCategory = params.get("category");
    const urlSearch = params.get("search");
    const urlSubcategory = params.get("subcategory");

    setBrowseMode(view === "listing" ? "listing" : "home");
    if (urlCategory && CATEGORY_NAV.some((item) => item.key === urlCategory)) {
      setCategory(urlCategory);
    }
    if (urlSearch) {
      setProductSearch(urlSearch);
    }
    setActiveSubcategory(urlSubcategory || "");

    function syncFromUrl() {
      const nextParams = new URLSearchParams(window.location.search);
      const nextView = nextParams.get("view");
      const nextCategory = nextParams.get("category");
      const nextSearch = nextParams.get("search");
      const nextSubcategory = nextParams.get("subcategory");

      setBrowseMode(nextView === "listing" ? "listing" : "home");
      if (nextCategory && CATEGORY_NAV.some((item) => item.key === nextCategory)) {
        setCategory(nextCategory);
      } else if (!nextCategory) {
        setCategory("all");
      }
      setProductSearch(nextSearch || "");
      setActiveSubcategory(nextSubcategory || "");
    }

    window.addEventListener("popstate", syncFromUrl);
    return () => window.removeEventListener("popstate", syncFromUrl);
  }, [setCategory, setProductSearch]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (browseMode === "listing") {
      params.set("view", "listing");
      params.set("category", category || "all");
      if (activeSubcategory) {
        params.set("subcategory", activeSubcategory);
      } else {
        params.delete("subcategory");
      }
      if (productSearch.trim()) {
        params.set("search", productSearch.trim());
      } else {
        params.delete("search");
      }
    } else {
      params.delete("view");
      params.delete("category");
      params.delete("subcategory");
      params.delete("search");
    }

    const nextUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
    window.history.replaceState({}, "", nextUrl);
  }, [browseMode, category, activeSubcategory, productSearch]);

  function toggleFilter(key) {
    setOpenFilters((current) => ({ ...current, [key]: !current[key] }));
  }

  function goHome() {
    setBrowseMode("home");
    setCategory("all");
    setActiveSubcategory("");
    setActiveMenu("");
    setAccountMenuOpen(false);
    setMoreMenuOpen(false);
  }

  function openCategory(nextCategory, nextSubcategory = "") {
    setCategory(nextCategory);
    setBrowseMode("listing");
    setActiveSubcategory(nextSubcategory);
    setActiveMenu("");
    setAccountMenuOpen(false);
    setMoreMenuOpen(false);
  }

  function openAllProducts() {
    setBrowseMode("listing");
    setCategory("all");
    setActiveSubcategory("");
    setActiveMenu("");
  }

  function handleSearchSubmit(event) {
    event.preventDefault();
    setBrowseMode("listing");
    setActiveSubcategory("");
    setActiveMenu("");
    setAccountMenuOpen(false);
    setMoreMenuOpen(false);
  }

  return (
    <section className="storefront-card flipkart-storefront">
      <div className="flipkart-topbar">
        <div className="flipkart-brand-panel">
          <div className="flipkart-brand">Vmart<span>Plus</span></div>
          <small>Explore best deals</small>
        </div>

        <form className="flipkart-search-panel" onSubmit={handleSearchSubmit}>
          <input
            type="text"
            value={productSearch}
            onChange={(event) => setProductSearch(event.target.value)}
            placeholder="Search for products, brands and more"
          />
          <button type="submit" aria-label="Search">?</button>
        </form>

        <div className="flipkart-account-bar">
          <div className="flipkart-account-menu-wrap">
            <button type="button" onClick={() => setAccountMenuOpen((current) => !current)}>{user ? "Account" : "Login"}</button>
            {accountMenuOpen ? (
              <div className="flipkart-account-menu rich-login-popup">
                <div className="flipkart-account-menu-top">
                  <div>
                    <strong>{user?.name || "Guest user"}</strong>
                    <span>{user?.email || "Use sign in to continue"}</span>
                  </div>
                  <button type="button" className="flipkart-signup-link" onClick={() => setAccountMenuOpen(false)}>Manage</button>
                </div>
                <button type="button" onClick={() => { setAccountMenuOpen(false); onOpenOrders(); }}>My Orders</button>
                <button type="button" onClick={() => { setAccountMenuOpen(false); onOpenWishlist(); }}>My Wishlist</button>
                <button type="button" onClick={() => { setAccountMenuOpen(false); onOpenCart(); }}>My Cart</button>
              </div>
            ) : null}
          </div>
          <div className="flipkart-account-menu-wrap">
            <button type="button" className="flipkart-inline-button" onClick={() => setMoreMenuOpen((current) => !current)}>More</button>
            {moreMenuOpen ? (
              <div className="flipkart-account-menu more-menu">
                <button type="button" onClick={() => { setMoreMenuOpen(false); goHome(); }}>Home</button>
                <button type="button" onClick={() => { setMoreMenuOpen(false); onAsk("Help me find the best products for my needs."); }}>Ask AI</button>
                <button type="button" onClick={() => { setMoreMenuOpen(false); onOpenOrders(); }}>Track Orders</button>
              </div>
            ) : null}
          </div>
          <button type="button" className="flipkart-inline-button" onClick={onOpenCart}>Cart ({wishlistIds.length})</button>
        </div>
      </div>

      <div className="flipkart-category-strip">
        {CATEGORY_NAV.map((item) => (
          <CategoryTile key={item.key} category={item} active={category === item.key} onSelect={openCategory} />
        ))}
      </div>

      <div className="flipkart-dept-bar">
        {TOP_MENU_GROUPS.map((menu) => (
          <button
            key={menu.key}
            type="button"
            className={`flipkart-dept-trigger ${activeMenu === menu.key ? "active" : ""}`}
            onMouseEnter={() => setActiveMenu(menu.key)}
            onFocus={() => setActiveMenu(menu.key)}
            onClick={() => openCategory(menu.groups[0].category, menu.groups[0].items[0])}
          >
            {menu.label}
          </button>
        ))}
      </div>

      {activeMenu ? (
        <div className="flipkart-mega-menu" onMouseLeave={() => setActiveMenu("")}>
          {(TOP_MENU_GROUPS.find((menu) => menu.key === activeMenu)?.groups || []).map((group) => (
            <div key={group.title} className="flipkart-mega-column">
              <strong>{group.title}</strong>
              {group.items.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="flipkart-mega-link"
                  onClick={() => openCategory(group.category, item)}
                >
                  {item}
                </button>
              ))}
            </div>
          ))}
        </div>
      ) : null}

      {browseMode === "home" && heroProduct ? (
        <section className="flipkart-hero">
          <button type="button" className="flipkart-hero-arrow left" aria-label="Previous banner">‹</button>
          <div className="flipkart-hero-image-wrap">
            <img src={getProductImageSources(heroProduct)[0] || ""} alt={heroProduct.name} loading="lazy" decoding="async" />
          </div>
          <div className="flipkart-hero-copy">
            <p>Big savings live now</p>
            <h2>{heroProduct.name}</h2>
            <h3>Starting Rs {heroProduct.price.toLocaleString("en-IN")}</h3>
            <span>{heroProduct.tag}</span>
            <div className="flipkart-hero-actions">
              <button type="button" onClick={() => onViewDetails(heroProduct.id)}>View details</button>
              <button type="button" className="secondary-button" onClick={() => onAddToCart(heroProduct.id)}>Add to cart</button>
              <button type="button" className="ghost-button" onClick={() => onAsk(`Help me compare ${heroProduct.name} with similar options`)}>
                Ask AI
              </button>
            </div>
          </div>
          <button type="button" className="flipkart-hero-arrow right" aria-label="Next banner">›</button>
        </section>
      ) : null}

      {browseMode === "home" ? (
        <div className="flipkart-section-stack">
          {sectionProducts.map((section) => (
            <FrontPageSection
              key={section.key}
              title={section.title}
              tagline={section.tagline}
              products={section.products}
              wishlistIds={wishlistIds}
              onViewDetails={onViewDetails}
              onToggleWishlist={onToggleWishlist}
              onAddToCart={onAddToCart}
              onViewAll={openAllProducts}
            />
          ))}
        </div>
      ) : (
        <section className="flipkart-listing-shell">
          <div className="flipkart-listing-breadcrumbs">
            <button type="button" onClick={goHome}>Home</button>
            <span>›</span>
            <span>{listingTitle}</span>
          </div>

          <div className="flipkart-listing-layout">
            <aside className="flipkart-filter-panel">
              <div className="flipkart-filter-card">
                <h3>Filters</h3>
                <div className="flipkart-filter-group">
                  <button type="button" className="flipkart-filter-toggle" onClick={() => toggleFilter("categories")}>
                    <strong>Categories</strong>
                    <span>{openFilters.categories ? "-" : "+"}</span>
                  </button>
                  {openFilters.categories ? CATEGORY_NAV.filter((item) => item.key !== "all").map((item) => (
                    <button key={item.key} type="button" className={`flipkart-filter-link ${category === item.key ? "active" : ""}`} onClick={() => openCategory(item.key, "")}>
                      {item.label}
                    </button>
                  )) : null}
                </div>
                <div className="flipkart-filter-group">
                  <button type="button" className="flipkart-filter-toggle" onClick={() => toggleFilter("offers")}>
                    <strong>Offers</strong>
                    <span>{openFilters.offers ? "-" : "+"}</span>
                  </button>
                  {openFilters.offers ? (
                    <>
                      <span>Min 20% off</span>
                      <span>Fast delivery</span>
                      <span>Top rated</span>
                    </>
                  ) : null}
                </div>
                <div className="flipkart-filter-group">
                  <button type="button" className="flipkart-filter-toggle" onClick={() => toggleFilter("budget")}>
                    <strong>Budget</strong>
                    <span>{openFilters.budget ? "-" : "+"}</span>
                  </button>
                  {openFilters.budget ? (
                    <>
                      <span>Under Rs 10,000</span>
                      <span>Rs 10,000 - Rs 25,000</span>
                      <span>Premium picks</span>
                    </>
                  ) : null}
                </div>
              </div>
            </aside>

            <div className="flipkart-listing-main">
              <div className="flipkart-listing-head">
                <div>
                  <h2>{listingTitle}</h2>
                  <p>Showing {browseProducts.length} products</p>
                </div>
                <div className="flipkart-sort-row">
                  <span>Sort By</span>
                  <button type="button" className="active">Popularity</button>
                  <button type="button">Price -- Low to High</button>
                  <button type="button">Newest First</button>
                </div>
              </div>

              <div className="flipkart-listing-grid">
                {browseProducts.map((product) => (
                  <FrontPageProduct
                    key={product.id}
                    product={product}
                    saved={wishlistIds.includes(product.id)}
                    onViewDetails={onViewDetails}
                    onToggleWishlist={onToggleWishlist}
                    onAddToCart={onAddToCart}
                  />
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {products.length === 0 ? (
        <div className="simple-store-empty">
          <h3>No products found</h3>
          <p>Try a different search or switch to another category.</p>
        </div>
      ) : null}
    </section>
  );
}
