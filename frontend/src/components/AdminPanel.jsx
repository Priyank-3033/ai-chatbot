import { useState } from "react";

const CATEGORY_OPTIONS = [
  ["phone", "Phone"],
  ["laptop", "Laptop"],
  ["tablet", "Tablet"],
  ["watch", "Watch"],
  ["accessory", "Accessory"],
];

const EMPTY_PRODUCT = {
  id: "",
  name: "",
  brand: "",
  category: "phone",
  sku: "",
  price: 9999,
  rating: 4.2,
  storage: "128GB",
  tag: "Featured",
  image: "",
  gallery: "",
  description: "",
  long_description: "",
  features: "",
  specs: "Display: AMOLED\nBattery: 5000mAh",
  stock: 10,
  delivery_note: "Fast delivery available",
};

function productToForm(product) {
  if (!product) return EMPTY_PRODUCT;
  return {
    ...product,
    gallery: (product.gallery || []).join("\n"),
    features: (product.features || []).join("\n"),
    specs: Object.entries(product.specs || {}).map(([key, value]) => `${key}: ${value}`).join("\n"),
  };
}

export default function AdminPanel({ products, onSave, onDelete, busy }) {
  const [form, setForm] = useState(EMPTY_PRODUCT);
  const [editingId, setEditingId] = useState("");
  const [message, setMessage] = useState("");

  function startEdit(product) {
    setEditingId(product.id);
    setForm(productToForm(product));
    setMessage("");
  }

  function resetForm() {
    setEditingId("");
    setForm(EMPTY_PRODUCT);
    setMessage("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const payload = {
      ...form,
      price: Number(form.price),
      rating: Number(form.rating),
      stock: Number(form.stock),
      gallery: form.gallery.split("\n").map((item) => item.trim()).filter(Boolean),
      features: form.features.split("\n").map((item) => item.trim()).filter(Boolean),
      specs: Object.fromEntries(
        form.specs
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean)
          .map((line) => {
            const [key, ...rest] = line.split(":");
            return [key.trim(), rest.join(":").trim()];
          })
          .filter(([key, value]) => key && value)
      ),
    };
    try {
      await onSave(payload, Boolean(editingId));
      setMessage(editingId ? "Product updated." : "Product created.");
      resetForm();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save product.");
    }
  }

  return (
    <section className="admin-panel">
      <div className="commerce-head">
        <div>
          <p className="eyebrow">Admin product management</p>
          <h2>Manage catalog</h2>
        </div>
        <button className="secondary-button" type="button" onClick={resetForm}>New product</button>
      </div>

      <div className="admin-layout">
        <div className="admin-product-list">
          {products.map((product) => (
            <article key={product.id} className="admin-product-card">
              <div>
                <strong>{product.name}</strong>
                <p>{product.brand} • Rs {product.price.toLocaleString("en-IN")}</p>
                <span>{product.stock} stock • {product.sku}</span>
              </div>
              <div className="admin-actions">
                <button type="button" onClick={() => startEdit(product)}>Edit</button>
                <button className="secondary-button" type="button" onClick={() => onDelete(product.id)} disabled={busy}>Delete</button>
              </div>
            </article>
          ))}
        </div>

        <form className="admin-form" onSubmit={handleSubmit}>
          <input placeholder="Product ID" value={form.id} onChange={(event) => setForm((current) => ({ ...current, id: event.target.value }))} disabled={Boolean(editingId)} />
          <input placeholder="Name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
          <input placeholder="Brand" value={form.brand} onChange={(event) => setForm((current) => ({ ...current, brand: event.target.value }))} />
          <div className="admin-inline-grid">
            <select value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}>
              {CATEGORY_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <input placeholder="SKU" value={form.sku} onChange={(event) => setForm((current) => ({ ...current, sku: event.target.value }))} />
          </div>
          <div className="admin-inline-grid">
            <input placeholder="Price" type="number" value={form.price} onChange={(event) => setForm((current) => ({ ...current, price: event.target.value }))} />
            <input placeholder="Rating" type="number" step="0.1" value={form.rating} onChange={(event) => setForm((current) => ({ ...current, rating: event.target.value }))} />
          </div>
          <div className="admin-inline-grid">
            <input placeholder="Storage" value={form.storage} onChange={(event) => setForm((current) => ({ ...current, storage: event.target.value }))} />
            <input placeholder="Tag" value={form.tag} onChange={(event) => setForm((current) => ({ ...current, tag: event.target.value }))} />
          </div>
          <input placeholder="Optional image URL override" value={form.image} onChange={(event) => setForm((current) => ({ ...current, image: event.target.value }))} />
          <textarea placeholder="Optional gallery URLs, one per line" value={form.gallery} onChange={(event) => setForm((current) => ({ ...current, gallery: event.target.value }))} rows={4} />
          <textarea placeholder="Short description" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} rows={3} />
          <textarea placeholder="Long description" value={form.long_description} onChange={(event) => setForm((current) => ({ ...current, long_description: event.target.value }))} rows={4} />
          <textarea placeholder="Features, one per line" value={form.features} onChange={(event) => setForm((current) => ({ ...current, features: event.target.value }))} rows={4} />
          <textarea placeholder="Specs as Key: Value" value={form.specs} onChange={(event) => setForm((current) => ({ ...current, specs: event.target.value }))} rows={5} />
          <div className="admin-inline-grid">
            <input placeholder="Stock" type="number" value={form.stock} onChange={(event) => setForm((current) => ({ ...current, stock: event.target.value }))} />
            <input placeholder="Delivery note" value={form.delivery_note} onChange={(event) => setForm((current) => ({ ...current, delivery_note: event.target.value }))} />
          </div>
          {message ? <p className="admin-message">{message}</p> : null}
          <button className="checkout-button" type="submit" disabled={busy}>{editingId ? "Update product" : "Create product"}</button>
        </form>
      </div>
    </section>
  );
}

