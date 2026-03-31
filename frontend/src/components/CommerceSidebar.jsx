const TRACKING_ORDER = ["Placed", "Packed", "Shipped", "Out for Delivery", "Delivered"];

export default function CommerceSidebar({
  cart,
  wishlist,
  orders,
  checkoutForm,
  setCheckoutForm,
  onCheckout,
  onUpdateQty,
  onToggleWishlist,
  onViewDetails,
  onAdvanceOrder,
  loading,
  isAdmin,
}) {
  return (
    <section className="commerce-panel">
      <div className="commerce-overview-card">
        <div>
          <p className="eyebrow">Order center</p>
          <h3>Everything in one checkout rail</h3>
        </div>
        <div className="overview-grid">
          <article>
            <strong>{wishlist.items.length}</strong>
            <span>Wishlist</span>
          </article>
          <article>
            <strong>{cart.items.length}</strong>
            <span>Cart items</span>
          </article>
          <article>
            <strong>{orders.length}</strong>
            <span>Orders</span>
          </article>
        </div>
      </div>

      <div className="commerce-block">
        <div className="commerce-head">
          <h3>Wishlist</h3>
          <span>{wishlist.items.length} saved</span>
        </div>
        <div className="cart-list">
          {wishlist.items.length === 0 ? <p className="empty-mini">No wishlist items yet.</p> : null}
          {wishlist.items.map((item) => (
            <article key={item.product_id} className="cart-item compact-card">
              <div>
                <strong>{item.product.name}</strong>
                <p>Rs {item.product.price.toLocaleString("en-IN")}</p>
              </div>
              <div className="mini-actions">
                <button type="button" onClick={() => onViewDetails(item.product_id)}>View</button>
                <button className="secondary-button" type="button" onClick={() => onToggleWishlist(item.product_id)}>Remove</button>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="commerce-block commerce-block-strong">
        <div className="commerce-head">
          <h3>Cart</h3>
          <span>{cart.items.length} items</span>
        </div>
        <div className="cart-list">
          {cart.items.length === 0 ? <p className="empty-mini">Your cart is empty.</p> : null}
          {cart.items.map((item) => (
            <article key={item.product_id} className="cart-item cart-item-rich">
              <div>
                <strong>{item.product.name}</strong>
                <p>{item.product.tag}</p>
              </div>
              <div className="cart-item-meta">
                <span>Rs {item.product.price.toLocaleString("en-IN")}</span>
                <div className="qty-box">
                  <button onClick={() => onUpdateQty(item.product_id, item.quantity - 1)} type="button">-</button>
                  <span>{item.quantity}</span>
                  <button onClick={() => onUpdateQty(item.product_id, item.quantity + 1)} type="button">+</button>
                </div>
              </div>
            </article>
          ))}
        </div>
        <div className="cart-total">
          <strong>Total</strong>
          <strong>Rs {cart.total_amount.toLocaleString("en-IN")}</strong>
        </div>
      </div>

      <div className="commerce-block checkout-block">
        <div className="commerce-head">
          <h3>Checkout</h3>
          <span>Demo payment gateway</span>
        </div>
        <p className="checkout-helper">Fill shipping details, choose a payment method, and place the order from this rail.</p>
        <div className="checkout-form">
          <input placeholder="Full name" value={checkoutForm.full_name} onChange={(event) => setCheckoutForm((current) => ({ ...current, full_name: event.target.value }))} />
          <input placeholder="Phone" value={checkoutForm.phone} onChange={(event) => setCheckoutForm((current) => ({ ...current, phone: event.target.value }))} />
          <input placeholder="Address line" value={checkoutForm.address_line} onChange={(event) => setCheckoutForm((current) => ({ ...current, address_line: event.target.value }))} />
          <div className="admin-inline-grid">
            <input placeholder="City" value={checkoutForm.city} onChange={(event) => setCheckoutForm((current) => ({ ...current, city: event.target.value }))} />
            <input placeholder="State" value={checkoutForm.state} onChange={(event) => setCheckoutForm((current) => ({ ...current, state: event.target.value }))} />
          </div>
          <input placeholder="Postal code" value={checkoutForm.postal_code} onChange={(event) => setCheckoutForm((current) => ({ ...current, postal_code: event.target.value }))} />
          <div className="admin-inline-grid">
            <select value={checkoutForm.payment_method} onChange={(event) => setCheckoutForm((current) => ({ ...current, payment_method: event.target.value }))}>
              <option>Cash on Delivery</option>
              <option>UPI</option>
              <option>Card</option>
            </select>
            <select value={checkoutForm.payment_provider} onChange={(event) => setCheckoutForm((current) => ({ ...current, payment_provider: event.target.value }))}>
              <option>SmartPay Demo</option>
              <option>Razorpay Demo</option>
              <option>Stripe Demo</option>
            </select>
          </div>
          {checkoutForm.payment_method !== "Cash on Delivery" ? (
            <input
              placeholder="Payment reference or transaction ID"
              value={checkoutForm.payment_reference}
              onChange={(event) => setCheckoutForm((current) => ({ ...current, payment_reference: event.target.value }))}
            />
          ) : null}
          <button className="checkout-button" disabled={loading || cart.items.length === 0} onClick={onCheckout} type="button">
            Pay and place order
          </button>
        </div>
      </div>

      <div className="commerce-block">
        <div className="commerce-head">
          <h3>Orders</h3>
          <span>{orders.length} tracked</span>
        </div>
        <div className="order-list">
          {orders.length === 0 ? <p className="empty-mini">No orders yet.</p> : null}
          {orders.map((order) => (
            <article key={order.id} className="order-item order-card-detailed">
              <div className="order-headline">
                <div>
                  <strong>{order.status}</strong>
                  <p>Rs {order.total_amount.toLocaleString("en-IN")}</p>
                </div>
                <span>{order.payment_method}</span>
              </div>
              <p>Tracking: {order.tracking_code}</p>
              <span>{order.payment_status} • {order.transaction_reference}</span>
              <div className="tracking-strip">
                {TRACKING_ORDER.map((status) => (
                  <span key={status} className={status === order.status ? "active" : order.tracking_events.some((event) => event.label === status && event.complete) ? "done" : ""}>
                    {status}
                  </span>
                ))}
              </div>
              {isAdmin ? (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => onAdvanceOrder(order.id, order.status)}
                  disabled={loading || ["Delivered", "Cancelled"].includes(order.status)}
                >
                  Advance tracking
                </button>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
