from contextlib import asynccontextmanager
from sqlite3 import IntegrityError

from fastapi import Header, HTTPException, status

from app.config import get_settings
from app.models import (
    AdminChatLogResponse,
    AdminStatsResponse,
    CartItemResponse,
    CartResponse,
    ChatSessionSummary,
    DocumentResponse,
    OrderItemResponse,
    OrderResponse,
    OrderTrackingEvent,
    ProductResponse,
    UserPublic,
    WishlistItemResponse,
    WishlistResponse,
)
from app.services.auth import AuthService
from app.services.chatbot import ChatbotService
from app.services.database import DatabaseService
from app.services.document_service import DocumentService
from app.services.knowledge_base import KnowledgeBaseService
from app.services.product_catalog import ProductCatalogService


settings = get_settings()
database = DatabaseService(settings)
auth_service = AuthService(settings)
knowledge_base = KnowledgeBaseService(settings.knowledge_base_path)
product_catalog = ProductCatalogService(settings.product_catalog_path)
chatbot = ChatbotService(settings, knowledge_base, product_catalog)
document_service = DocumentService()


@asynccontextmanager
async def lifespan(_: object):
    database.initialize()
    yield


def is_admin_email(email: str) -> bool:
    lowered = email.lower()
    return lowered in settings.admin_emails or lowered.startswith("admin@")


def to_user_public(row) -> UserPublic:
    return UserPublic(id=row["id"], name=row["name"], email=row["email"], is_admin=is_admin_email(row["email"]))


def to_session_summary(row) -> ChatSessionSummary:
    preview = (row["preview"] or "Start a conversation").strip()
    return ChatSessionSummary(id=row["id"], title=row["title"], mode=row["mode"], updated_at=row["updated_at"], preview=preview[:120])


def to_product_response(product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        brand=product.brand,
        category=product.category,
        sku=product.sku,
        price=product.price,
        rating=product.rating,
        storage=product.storage,
        tag=product.tag,
        image=product.image,
        gallery=product.gallery,
        image_local=product.image_local,
        gallery_local=product.gallery_local,
        description=product.description,
        long_description=product.long_description,
        features=product.features,
        specs=product.specs,
        stock=product.stock,
        delivery_note=product.delivery_note,
    )


def build_cart_response(user_id: int) -> CartResponse:
    rows = database.get_cart_items(user_id)
    items: list[CartItemResponse] = []
    total_amount = 0
    for row in rows:
        product = product_catalog.get_product(row["product_id"])
        if not product:
            continue
        total_amount += product.price * row["quantity"]
        items.append(
            CartItemResponse(
                product_id=product.id,
                quantity=row["quantity"],
                product=to_product_response(product),
            )
        )
    return CartResponse(items=items, total_amount=total_amount)


def build_wishlist_response(user_id: int) -> WishlistResponse:
    rows = database.list_wishlist_items(user_id)
    items: list[WishlistItemResponse] = []
    for row in rows:
        product = product_catalog.get_product(row["product_id"])
        if not product:
            continue
        items.append(
            WishlistItemResponse(
                product_id=product.id,
                added_at=row["added_at"],
                product=to_product_response(product),
            )
        )
    return WishlistResponse(items=items)


def build_order_response(order_row) -> OrderResponse:
    items = database.get_order_items(order_row["id"])
    tracking_events = database.build_tracking_events(order_row)
    return OrderResponse(
        id=order_row["id"],
        status=order_row["status"],
        total_amount=order_row["total_amount"],
        created_at=order_row["created_at"],
        payment_method=order_row["payment_method"],
        payment_provider=order_row["payment_provider"],
        payment_status=order_row["payment_status"],
        transaction_reference=order_row["transaction_reference"],
        tracking_code=order_row["tracking_code"],
        shipping_name=order_row["shipping_name"],
        shipping_address=order_row["shipping_address"],
        items=[
            OrderItemResponse(
                product_id=item["product_id"],
                name=item["name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
            )
            for item in items
        ],
        tracking_events=[OrderTrackingEvent(**event) for event in tracking_events],
    )


def to_document_response(row) -> DocumentResponse:
    return DocumentResponse(
        id=row["id"],
        name=row["name"],
        content_type=row["content_type"],
        size=row["size"],
        created_at=row["created_at"],
    )


def to_admin_stats_response(row) -> AdminStatsResponse:
    return AdminStatsResponse(
        user_count=row["user_count"],
        order_count=row["order_count"],
        chat_session_count=row["chat_session_count"],
        uploaded_document_count=row["uploaded_document_count"],
    )


def to_admin_chat_log(row) -> AdminChatLogResponse:
    return AdminChatLogResponse(
        session_id=row["session_id"],
        user_name=row["user_name"],
        user_email=row["user_email"],
        title=row["title"],
        mode=row["mode"],
        updated_at=row["updated_at"],
        preview=(row["preview"] or "").strip()[:160],
    )


def require_user(authorization: str | None = Header(default=None)) -> UserPublic:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token.")
    token = authorization.split(" ", maxsplit=1)[1]
    user_id = auth_service.parse_token(token)
    user_row = database.get_user_by_id(user_id)
    if not user_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return to_user_public(user_row)


def get_required_admin(current_user: UserPublic) -> UserPublic:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


def register_user(name: str, email: str, password_hash: str):
    try:
        return database.create_user(name, email, password_hash)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.") from exc
