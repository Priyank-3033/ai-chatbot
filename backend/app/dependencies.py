from contextlib import asynccontextmanager
import json
from pathlib import Path
from sqlite3 import IntegrityError

from fastapi import Header, HTTPException, status

from app.config import get_settings
from app.models import (
    AdminChatLogResponse,
    AdminStatsResponse,
    AuditLogResponse,
    CartItemResponse,
    CartResponse,
    ChatSessionSummary,
    DocumentResponse,
    OrderItemResponse,
    OrderResponse,
    OrderTrackingEvent,
    ProductResponse,
    SecurityAlertResponse,
    SecurityOverviewResponse,
    UserPublic,
    WishlistItemResponse,
    WishlistResponse,
)
from app.services.auth import AuthService
from app.services.chatbot import ChatbotService
from app.services.database import DatabaseService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_base import KnowledgeBaseService
from app.services.product_catalog import ProductCatalogService
from app.services.vector_store import VectorStoreService


settings = get_settings()
database = DatabaseService(settings)
auth_service = AuthService(settings)
knowledge_base = KnowledgeBaseService(settings.knowledge_base_path)
product_catalog = ProductCatalogService(settings.product_catalog_path)
document_service = DocumentService()
embedding_service = EmbeddingService(settings)
vector_store = VectorStoreService(settings)
chatbot = ChatbotService(settings, knowledge_base, product_catalog, embedding_service, vector_store)


@asynccontextmanager
async def lifespan(_: object):
    database.initialize()
    vector_store.ensure_storage()
    yield


def is_admin_email(email: str) -> bool:
    lowered = email.lower()
    return lowered in settings.admin_emails or lowered.startswith("admin@")


def is_security_analyst_email(email: str) -> bool:
    lowered = email.lower()
    return lowered in settings.security_analyst_emails or lowered.startswith("security@")


def derive_user_role(email: str) -> str:
    if is_admin_email(email):
        return "admin"
    if is_security_analyst_email(email):
        return "security_analyst"
    return "user"


def to_user_public(row) -> UserPublic:
    role = row["role"] if "role" in row.keys() and row["role"] else derive_user_role(row["email"])
    return UserPublic(id=row["id"], name=row["name"], email=row["email"], role=role, is_admin=role == "admin")


def to_session_summary(row) -> ChatSessionSummary:
    preview = (row["preview"] or "Start a conversation").strip()
    return ChatSessionSummary(id=row["id"], title=row["title"], mode=row["mode"], updated_at=row["updated_at"], preview=preview[:120])


def to_product_response(product) -> ProductResponse:
    valid_local_main = product.image_local if product.image_local and (settings.product_photos_path / Path(product.image_local)).exists() else None
    valid_local_gallery = [
        image
        for image in product.gallery_local
        if image and (settings.product_photos_path / Path(image)).exists()
    ]
    image_sources = []
    for value in [valid_local_main, product.image, "/fallback-product.svg"]:
        if value and value not in image_sources:
            image_sources.append(value)
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
        image_local=valid_local_main,
        gallery_local=valid_local_gallery,
        image_sources=image_sources,
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
        status=row["status"],
        created_at=row["created_at"],
    )


def to_admin_stats_response(row) -> AdminStatsResponse:
    return AdminStatsResponse(
        user_count=row["user_count"],
        order_count=row["order_count"],
        chat_session_count=row["chat_session_count"],
        uploaded_document_count=row["uploaded_document_count"],
        audit_log_count=row["audit_log_count"],
        open_security_alert_count=row["open_security_alert_count"],
        failed_login_count=row["failed_login_count"],
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


def _parse_metadata(metadata_json: str | None) -> dict[str, str]:
    if not metadata_json:
        return {}
    try:
        parsed = json.loads(metadata_json)
        return {str(key): str(value) for key, value in parsed.items()}
    except Exception:
        return {}


def to_audit_log_response(row) -> AuditLogResponse:
    return AuditLogResponse(
        id=row["id"],
        event_type=row["event_type"],
        severity=row["severity"],
        actor_email=row["actor_email"],
        ip_address=row["ip_address"] or None,
        description=row["description"],
        created_at=row["created_at"],
        metadata=_parse_metadata(row["metadata_json"]),
    )


def to_security_alert_response(row) -> SecurityAlertResponse:
    return SecurityAlertResponse(
        id=row["id"],
        alert_type=row["alert_type"],
        severity=row["severity"],
        status=row["status"],
        user_email=row["user_email"],
        ip_address=row["ip_address"] or None,
        message=row["message"],
        created_at=row["created_at"],
        metadata=_parse_metadata(row["metadata_json"]),
    )


def build_security_overview(limit_logs: int = 20, limit_alerts: int = 12) -> SecurityOverviewResponse:
    return SecurityOverviewResponse(
        recent_audit_logs=[to_audit_log_response(row) for row in database.recent_audit_logs(limit_logs)],
        recent_security_alerts=[to_security_alert_response(row) for row in database.recent_security_alerts(limit_alerts)],
    )


def require_user(authorization: str | None = Header(default=None)) -> UserPublic:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token.")
    token = authorization.split(" ", maxsplit=1)[1]
    claims = auth_service.parse_token_claims(token)
    user_id = int(claims["sub"])
    user_row = database.get_user_by_id(user_id)
    if not user_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if int(user_row["token_version"] or 0) != int(claims.get("ver", 0)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been revoked. Please sign in again.")
    return to_user_public(user_row)


def get_required_admin(current_user: UserPublic) -> UserPublic:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


def get_required_security_user(current_user: UserPublic) -> UserPublic:
    if current_user.role not in {"admin", "security_analyst"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Security access required.")
    return current_user


def register_user(name: str, email: str, password_hash: str, phone: str):
    try:
        return database.create_user(name, email, password_hash, phone=phone, role=derive_user_role(email))
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.") from exc
