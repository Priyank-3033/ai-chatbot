from contextlib import asynccontextmanager
from sqlite3 import IntegrityError

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import (
    AuthResponse,
    CartAddRequest,
    CartItemResponse,
    CartResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionCreateRequest,
    ChatSessionDetail,
    ChatSessionSummary,
    CheckoutRequest,
    HealthResponse,
    LoginRequest,
    OrderItemResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
    OrderTrackingEvent,
    ProductResponse,
    ProductUpsertRequest,
    RegisterRequest,
    UserPublic,
    WishlistItemResponse,
    WishlistResponse,
)
from app.services.auth import AuthService
from app.services.chatbot import ChatbotService
from app.services.database import DatabaseService
from app.services.knowledge_base import KnowledgeBaseService
from app.services.product_catalog import ProductCatalogService


settings = get_settings()
database = DatabaseService(settings)
auth_service = AuthService(settings)
knowledge_base = KnowledgeBaseService(settings.knowledge_base_path)
product_catalog = ProductCatalogService(settings.product_catalog_path)
chatbot = ChatbotService(settings, knowledge_base, product_catalog)


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize()
    yield


app = FastAPI(title="Smart Chat API", version="5.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def require_user(authorization: str | None = Header(default=None)) -> UserPublic:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token.")
    token = authorization.split(" ", maxsplit=1)[1]
    user_id = auth_service.parse_token(token)
    user_row = database.get_user_by_id(user_id)
    if not user_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return to_user_public(user_row)


def require_admin(current_user: UserPublic = Depends(require_user)) -> UserPublic:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


@app.get("/api/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", knowledge_base_loaded=len(knowledge_base.entries) > 0)


@app.post("/api/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest) -> AuthResponse:
    password_hash = auth_service.hash_password(request.password)
    try:
        user_row = database.create_user(request.name.strip(), request.email, password_hash)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.") from exc
    token = auth_service.create_token(user_row["id"])
    return AuthResponse(token=token, user=to_user_public(user_row))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    user_row = database.get_user_by_email(request.email)
    if not user_row or not auth_service.verify_password(request.password, user_row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    token = auth_service.create_token(user_row["id"])
    return AuthResponse(token=token, user=to_user_public(user_row))


@app.get("/api/auth/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(require_user)) -> UserPublic:
    return current_user


@app.get("/api/products", response_model=list[ProductResponse])
def list_products(category: str | None = Query(default=None), search: str | None = Query(default=None), current_user: UserPublic = Depends(require_user)) -> list[ProductResponse]:
    _ = current_user
    products = product_catalog.list_products(category=category, search=search)
    return [to_product_response(product) for product in products]


@app.get("/api/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, current_user: UserPublic = Depends(require_user)) -> ProductResponse:
    _ = current_user
    product = product_catalog.get_product(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return to_product_response(product)


@app.get("/api/wishlist", response_model=WishlistResponse)
def get_wishlist(current_user: UserPublic = Depends(require_user)) -> WishlistResponse:
    return build_wishlist_response(current_user.id)


@app.post("/api/wishlist/{product_id}", response_model=WishlistResponse)
def add_wishlist_item(product_id: str, current_user: UserPublic = Depends(require_user)) -> WishlistResponse:
    product = product_catalog.get_product(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    database.add_to_wishlist(current_user.id, product_id)
    return build_wishlist_response(current_user.id)


@app.delete("/api/wishlist/{product_id}", response_model=WishlistResponse)
def remove_wishlist_item(product_id: str, current_user: UserPublic = Depends(require_user)) -> WishlistResponse:
    database.remove_from_wishlist(current_user.id, product_id)
    return build_wishlist_response(current_user.id)


@app.get("/api/cart", response_model=CartResponse)
def get_cart(current_user: UserPublic = Depends(require_user)) -> CartResponse:
    return build_cart_response(current_user.id)


@app.post("/api/cart/items", response_model=CartResponse)
def add_cart_item(request: CartAddRequest, current_user: UserPublic = Depends(require_user)) -> CartResponse:
    product = product_catalog.get_product(request.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    database.add_to_cart(current_user.id, request.product_id, request.quantity)
    return build_cart_response(current_user.id)


@app.put("/api/cart/items/{product_id}", response_model=CartResponse)
def update_cart_item(product_id: str, request: CartAddRequest, current_user: UserPublic = Depends(require_user)) -> CartResponse:
    database.update_cart_quantity(current_user.id, product_id, request.quantity)
    return build_cart_response(current_user.id)


@app.get("/api/orders", response_model=list[OrderResponse])
def list_orders(current_user: UserPublic = Depends(require_user)) -> list[OrderResponse]:
    rows = database.list_orders(current_user.id)
    return [build_order_response(row) for row in rows]


@app.get("/api/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, current_user: UserPublic = Depends(require_user)) -> OrderResponse:
    row = database.get_order(order_id, current_user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return build_order_response(row)


@app.post("/api/orders/checkout", response_model=OrderResponse)
def checkout(request: CheckoutRequest, current_user: UserPublic = Depends(require_user)) -> OrderResponse:
    cart = build_cart_response(current_user.id)
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty.")
    payment_status = "Pay on Delivery" if request.payment_method == "Cash on Delivery" else "Paid"
    transaction_reference = request.payment_reference or f"TXN-{current_user.id}-{len(cart.items)}-{request.payment_method.replace(' ', '').upper()}"
    order_id = database.create_order(
        user_id=current_user.id,
        total_amount=cart.total_amount,
        payment_method=request.payment_method,
        payment_provider=request.payment_provider,
        payment_status=payment_status,
        transaction_reference=transaction_reference,
        shipping_name=request.full_name,
        shipping_phone=request.phone,
        shipping_address=f"{request.address_line}, {request.city}, {request.state} - {request.postal_code}",
        items=[
            {
                "product_id": item.product.id,
                "name": item.product.name,
                "quantity": item.quantity,
                "unit_price": item.product.price,
            }
            for item in cart.items
        ],
    )
    order_row = database.get_order(order_id, current_user.id)
    return build_order_response(order_row)


@app.put("/api/admin/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: str, request: OrderStatusUpdateRequest, current_user: UserPublic = Depends(require_admin)) -> OrderResponse:
    _ = current_user
    order_row = database.update_order_status(order_id, request.status)
    if not order_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return build_order_response(order_row)


@app.post("/api/admin/products", response_model=ProductResponse)
def create_product(request: ProductUpsertRequest, current_user: UserPublic = Depends(require_admin)) -> ProductResponse:
    _ = current_user
    if product_catalog.get_product(request.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product ID already exists.")
    product = product_catalog.upsert_product(request.model_dump())
    return to_product_response(product)


@app.put("/api/admin/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, request: ProductUpsertRequest, current_user: UserPublic = Depends(require_admin)) -> ProductResponse:
    _ = current_user
    if product_id != request.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product ID mismatch.")
    product = product_catalog.upsert_product(request.model_dump())
    return to_product_response(product)


@app.delete("/api/admin/products/{product_id}")
def delete_product(product_id: str, current_user: UserPublic = Depends(require_admin)) -> dict[str, str]:
    _ = current_user
    deleted = product_catalog.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return {"status": "deleted"}


@app.get("/api/chat-sessions", response_model=list[ChatSessionSummary])
def list_chat_sessions(current_user: UserPublic = Depends(require_user)) -> list[ChatSessionSummary]:
    rows = database.list_chat_sessions(current_user.id)
    return [to_session_summary(row) for row in rows]


@app.post("/api/chat-sessions", response_model=ChatSessionDetail)
def create_chat_session(request: ChatSessionCreateRequest, current_user: UserPublic = Depends(require_user)) -> ChatSessionDetail:
    title = request.title.strip() if request.title else chatbot.default_session_title(request.mode)
    row = database.create_chat_session(user_id=current_user.id, mode=request.mode, title=title, welcome_message=chatbot.welcome_message(request.mode))
    messages = database.get_chat_messages(row["id"])
    return ChatSessionDetail(
        id=row["id"],
        title=row["title"],
        mode=row["mode"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        messages=[{"role": item["role"], "content": item["content"], "created_at": item["created_at"]} for item in messages],
    )


@app.get("/api/chat-sessions/{session_id}", response_model=ChatSessionDetail)
def get_chat_session(session_id: str, current_user: UserPublic = Depends(require_user)) -> ChatSessionDetail:
    row = database.get_chat_session(session_id, current_user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    messages = database.get_chat_messages(session_id)
    return ChatSessionDetail(
        id=row["id"],
        title=row["title"],
        mode=row["mode"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        messages=[{"role": item["role"], "content": item["content"], "created_at": item["created_at"]} for item in messages],
    )


@app.delete("/api/chat-sessions/{session_id}")
def delete_chat_session(session_id: str, current_user: UserPublic = Depends(require_user)) -> dict[str, str]:
    deleted = database.delete_chat_session(session_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    return {"status": "deleted"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: UserPublic = Depends(require_user)) -> ChatResponse:
    session_id = request.session_id
    if session_id:
        session_row = database.get_chat_session(session_id, current_user.id)
        if not session_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    else:
        session_row = database.create_chat_session(user_id=current_user.id, mode=request.mode, title=chatbot.default_session_title(request.mode), welcome_message=chatbot.welcome_message(request.mode))
        session_id = session_row["id"]

    existing_messages = database.get_chat_messages(session_id)
    history = [{"role": item["role"], "content": item["content"]} for item in existing_messages]
    database.append_chat_message(session_id, "user", request.question)

    if session_row["title"] == chatbot.default_session_title(request.mode):
        database.rename_chat_session(session_id, chatbot.suggested_session_title(request.question, request.mode))

    response = chatbot.answer(request.question, history, request.mode)
    database.append_chat_message(session_id, "assistant", response.answer)
    response.session_id = session_id
    return response


@app.post("/api/rebuild-index")
def rebuild_index() -> dict[str, str]:
    knowledge_base.rebuild_index()
    return {"status": "rebuilt"}
