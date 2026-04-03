from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings


TRACKING_DESCRIPTIONS = {
    "Placed": "Order confirmed and payment step recorded.",
    "Packed": "Items are packed and ready to leave the warehouse.",
    "Shipped": "Order is on the way with the logistics partner.",
    "Out for Delivery": "Courier is carrying your order for final delivery.",
    "Delivered": "Order delivered successfully.",
    "Cancelled": "Order has been cancelled.",
}

TRACKING_SEQUENCE = ["Placed", "Packed", "Shipped", "Out for Delivery", "Delivered"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DatabaseService:
    def __init__(self, settings: Settings) -> None:
        self.db_path = settings.database_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
                );

                CREATE TABLE IF NOT EXISTS cart_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, product_id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS wishlist_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    UNIQUE(user_id, product_id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    total_amount INTEGER NOT NULL,
                    payment_method TEXT NOT NULL,
                    shipping_name TEXT NOT NULL,
                    shipping_phone TEXT NOT NULL,
                    shipping_address TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price INTEGER NOT NULL,
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                );

                CREATE TABLE IF NOT EXISTS uploaded_documents (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ready',
                    extracted_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
                """
            )
            self._ensure_column(connection, "orders", "payment_provider", "TEXT NOT NULL DEFAULT 'SmartPay Demo'")
            self._ensure_column(connection, "orders", "payment_status", "TEXT NOT NULL DEFAULT 'Pending'")
            self._ensure_column(connection, "orders", "transaction_reference", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "orders", "tracking_code", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "orders", "tracking_updated_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "uploaded_documents", "status", "TEXT NOT NULL DEFAULT 'ready'")
            self._ensure_tracking_rows(connection)

    @staticmethod
    def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        existing = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def _ensure_tracking_rows(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            "SELECT id, status, created_at, tracking_code, tracking_updated_at, payment_status, transaction_reference FROM orders"
        ).fetchall()
        for row in rows:
            updates = {}
            if not row["tracking_code"]:
                updates["tracking_code"] = f"TRK-{row['id'][:8].upper()}"
            if not row["tracking_updated_at"]:
                updates["tracking_updated_at"] = row["created_at"]
            if not row["payment_status"]:
                updates["payment_status"] = "Paid" if row["payment_method"] != "Cash on Delivery" else "Pay on Delivery"
            if not row["transaction_reference"]:
                updates["transaction_reference"] = f"TXN-{row['id'][:10].upper()}"
            if updates:
                sets = ", ".join(f"{key} = ?" for key in updates)
                connection.execute(f"UPDATE orders SET {sets} WHERE id = ?", (*updates.values(), row["id"]))

    def create_user(self, name: str, email: str, password_hash: str) -> sqlite3.Row:
        created_at = utc_now_iso()
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name, email.lower(), password_hash, created_at),
            )
            user_id = cursor.lastrowid
            return connection.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()

    def get_user_by_email(self, email: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()

    def get_user_by_id(self, user_id: int) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()

    def create_chat_session(self, user_id: int, mode: str, title: str, welcome_message: str) -> sqlite3.Row:
        session_id = uuid4().hex
        now = utc_now_iso()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO chat_sessions (id, user_id, mode, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, user_id, mode, title, now, now),
            )
            connection.execute(
                "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, "assistant", welcome_message, now),
            )
            return connection.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()

    def list_chat_sessions(self, user_id: int) -> list[sqlite3.Row]:
        query = """
            SELECT
                s.id,
                s.title,
                s.mode,
                s.created_at,
                s.updated_at,
                COALESCE((SELECT content FROM chat_messages m WHERE m.session_id = s.id ORDER BY m.id DESC LIMIT 1), '') AS preview
            FROM chat_sessions s
            WHERE s.user_id = ?
            ORDER BY s.updated_at DESC
        """
        with self.connect() as connection:
            return connection.execute(query, (user_id,)).fetchall()

    def get_chat_session(self, session_id: str, user_id: int) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute("SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id)).fetchone()

    def get_chat_messages(self, session_id: str) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute("SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id ASC", (session_id,)).fetchall()

    def append_chat_message(self, session_id: str, role: str, content: str) -> None:
        now = utc_now_iso()
        with self.connect() as connection:
            connection.execute("INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)", (session_id, role, content, now))
            connection.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))

    def rename_chat_session(self, session_id: str, title: str) -> None:
        with self.connect() as connection:
            connection.execute("UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?", (title, utc_now_iso(), session_id))

    def delete_chat_session(self, session_id: str, user_id: int) -> bool:
        with self.connect() as connection:
            owned = connection.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if not owned:
                return False
            connection.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
            return True

    def get_cart_items(self, user_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute("SELECT product_id, quantity FROM cart_items WHERE user_id = ? ORDER BY id ASC", (user_id,)).fetchall()

    def add_to_cart(self, user_id: int, product_id: str, quantity: int) -> None:
        now = utc_now_iso()
        with self.connect() as connection:
            existing = connection.execute("SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?", (user_id, product_id)).fetchone()
            if existing:
                connection.execute(
                    "UPDATE cart_items SET quantity = ?, updated_at = ? WHERE user_id = ? AND product_id = ?",
                    (existing["quantity"] + quantity, now, user_id, product_id),
                )
            else:
                connection.execute(
                    "INSERT INTO cart_items (user_id, product_id, quantity, updated_at) VALUES (?, ?, ?, ?)",
                    (user_id, product_id, quantity, now),
                )

    def update_cart_quantity(self, user_id: int, product_id: str, quantity: int) -> None:
        with self.connect() as connection:
            if quantity <= 0:
                connection.execute("DELETE FROM cart_items WHERE user_id = ? AND product_id = ?", (user_id, product_id))
            else:
                connection.execute(
                    "UPDATE cart_items SET quantity = ?, updated_at = ? WHERE user_id = ? AND product_id = ?",
                    (quantity, utc_now_iso(), user_id, product_id),
                )

    def clear_cart(self, user_id: int) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))

    def list_wishlist_items(self, user_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT product_id, added_at FROM wishlist_items WHERE user_id = ? ORDER BY added_at DESC",
                (user_id,),
            ).fetchall()

    def add_to_wishlist(self, user_id: int, product_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO wishlist_items (user_id, product_id, added_at) VALUES (?, ?, ?)",
                (user_id, product_id, utc_now_iso()),
            )

    def remove_from_wishlist(self, user_id: int, product_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM wishlist_items WHERE user_id = ? AND product_id = ?", (user_id, product_id))

    def create_order(
        self,
        user_id: int,
        total_amount: int,
        payment_method: str,
        payment_provider: str,
        payment_status: str,
        transaction_reference: str,
        shipping_name: str,
        shipping_phone: str,
        shipping_address: str,
        items: list[dict],
    ) -> str:
        order_id = uuid4().hex
        now = utc_now_iso()
        tracking_code = f"TRK-{order_id[:8].upper()}"
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO orders (id, user_id, status, total_amount, payment_method, payment_provider, payment_status, transaction_reference, tracking_code, tracking_updated_at, shipping_name, shipping_phone, shipping_address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    order_id,
                    user_id,
                    "Placed",
                    total_amount,
                    payment_method,
                    payment_provider,
                    payment_status,
                    transaction_reference,
                    tracking_code,
                    now,
                    shipping_name,
                    shipping_phone,
                    shipping_address,
                    now,
                ),
            )
            for item in items:
                connection.execute(
                    "INSERT INTO order_items (order_id, product_id, name, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                    (order_id, item["product_id"], item["name"], item["quantity"], item["unit_price"]),
                )
            connection.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        return order_id

    def list_orders(self, user_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()

    def get_order(self, order_id: str, user_id: int | None = None) -> sqlite3.Row | None:
        with self.connect() as connection:
            if user_id is None:
                return connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            return connection.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id)).fetchone()

    def get_order_items(self, order_id: str) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT product_id, name, quantity, unit_price FROM order_items WHERE order_id = ? ORDER BY id ASC",
                (order_id,),
            ).fetchall()

    def update_order_status(self, order_id: str, status: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE orders SET status = ?, tracking_updated_at = ? WHERE id = ?",
                (status, utc_now_iso(), order_id),
            )
            return connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()

    def build_tracking_events(self, order_row: sqlite3.Row) -> list[dict[str, str | bool]]:
        current_status = order_row["status"]
        current_index = TRACKING_SEQUENCE.index(current_status) if current_status in TRACKING_SEQUENCE else -1
        created_at = order_row["created_at"]
        updated_at = order_row["tracking_updated_at"] or created_at
        events = []
        if current_status == "Cancelled":
            events.append(
                {
                    "label": "Placed",
                    "description": TRACKING_DESCRIPTIONS["Placed"],
                    "timestamp": created_at,
                    "complete": True,
                }
            )
            events.append(
                {
                    "label": "Cancelled",
                    "description": TRACKING_DESCRIPTIONS["Cancelled"],
                    "timestamp": updated_at,
                    "complete": True,
                }
            )
            return events
        for index, label in enumerate(TRACKING_SEQUENCE):
            events.append(
                {
                    "label": label,
                    "description": TRACKING_DESCRIPTIONS[label],
                    "timestamp": updated_at if index == current_index else created_at,
                    "complete": index <= current_index,
                }
            )
        return events

    def save_uploaded_document(self, user_id: int, name: str, content_type: str, size: int, extracted_text: str) -> sqlite3.Row:
        document_id = uuid4().hex
        created_at = utc_now_iso()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO uploaded_documents (id, user_id, name, content_type, size, extracted_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, user_id, name, content_type, size, extracted_text, created_at),
            )
            return connection.execute("SELECT * FROM uploaded_documents WHERE id = ?", (document_id,)).fetchone()

    def create_uploaded_document_placeholder(self, user_id: int, name: str, content_type: str, size: int) -> sqlite3.Row:
        document_id = uuid4().hex
        created_at = utc_now_iso()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO uploaded_documents (id, user_id, name, content_type, size, status, extracted_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, user_id, name, content_type, size, "processing", "", created_at),
            )
            return connection.execute("SELECT * FROM uploaded_documents WHERE id = ?", (document_id,)).fetchone()

    def update_uploaded_document_text(self, document_id: str, extracted_text: str, status: str = "ready") -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE uploaded_documents SET extracted_text = ?, status = ? WHERE id = ?",
                (extracted_text, status, document_id),
            )

    def mark_uploaded_document_failed(self, document_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE uploaded_documents SET status = ? WHERE id = ?",
                ("failed", document_id),
            )

    def list_uploaded_documents(self, user_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT id, name, content_type, size, status, created_at FROM uploaded_documents WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()

    def get_uploaded_documents_for_retrieval(self, user_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT id, name, content_type, size, status, extracted_text, created_at FROM uploaded_documents WHERE user_id = ? AND status = 'ready' ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()

    def admin_stats(self) -> sqlite3.Row:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM users) AS user_count,
                    (SELECT COUNT(*) FROM orders) AS order_count,
                    (SELECT COUNT(*) FROM chat_sessions) AS chat_session_count,
                    (SELECT COUNT(*) FROM uploaded_documents) AS uploaded_document_count
                """
            ).fetchone()

    def admin_chat_logs(self, limit: int = 50) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT
                    s.id AS session_id,
                    s.title,
                    s.mode,
                    s.updated_at,
                    u.name AS user_name,
                    u.email AS user_email,
                    COALESCE(
                        (SELECT content FROM chat_messages m WHERE m.session_id = s.id ORDER BY m.id DESC LIMIT 1),
                        ''
                    ) AS preview
                FROM chat_sessions s
                JOIN users u ON u.id = s.user_id
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
