from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class Source(BaseModel):
    title: str
    snippet: str


class ProductResponse(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    sku: str
    price: int
    rating: float
    storage: str
    tag: str
    image: str
    gallery: list[str]
    image_local: str | None = None
    gallery_local: list[str] = Field(default_factory=list)
    image_sources: list[str] = Field(default_factory=list)
    description: str
    long_description: str
    features: list[str]
    specs: dict[str, str]
    stock: int
    delivery_note: str


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


class ProductRecommendationResponse(BaseModel):
    product: ProductResponse
    reason: str


class CartItemResponse(BaseModel):
    product_id: str
    quantity: int
    product: ProductResponse


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total_amount: int


class CartAddRequest(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=10)


class CheckoutRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=8, max_length=20)
    address_line: str = Field(..., min_length=5, max_length=200)
    city: str = Field(..., min_length=2, max_length=80)
    state: str = Field(..., min_length=2, max_length=80)
    postal_code: str = Field(..., min_length=4, max_length=12)
    payment_method: str = Field(default="Cash on Delivery", max_length=40)
    payment_provider: str = Field(default="SmartPay Demo", max_length=60)
    payment_reference: str | None = Field(default=None, max_length=80)


class WishlistItemResponse(BaseModel):
    product_id: str
    added_at: str
    product: ProductResponse


class WishlistResponse(BaseModel):
    items: list[WishlistItemResponse]


class OrderItemResponse(BaseModel):
    product_id: str
    name: str
    quantity: int
    unit_price: int


class OrderResponse(BaseModel):
    id: str
    status: str
    total_amount: int
    created_at: str
    payment_method: str
    payment_provider: str
    payment_status: str
    transaction_reference: str
    tracking_code: str
    shipping_name: str
    shipping_address: str
    items: list[OrderItemResponse]
    tracking_events: list["OrderTrackingEvent"]


class OrderTrackingEvent(BaseModel):
    label: str
    description: str
    timestamp: str
    complete: bool


class UserPublic(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_admin: bool = False


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class ChatMessage(BaseModel):
    role: Literal["assistant", "user"]
    content: str
    created_at: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list)
    mode: Literal["general", "support"] = "general"
    session_id: str | None = None
    model: str | None = Field(default=None, max_length=80)
    custom_prompt: str | None = Field(default=None, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    mode: str
    session_id: str | None = None


class ChatSessionCreateRequest(BaseModel):
    mode: Literal["general", "support"] = "general"
    title: str | None = Field(default=None, max_length=120)


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    mode: Literal["general", "support"]
    updated_at: str
    preview: str


class ChatSessionDetail(BaseModel):
    id: str
    title: str
    mode: Literal["general", "support"]
    created_at: str
    updated_at: str
    messages: list[ChatMessage]


class ProductUpsertRequest(BaseModel):
    id: str = Field(..., min_length=2, max_length=40)
    name: str = Field(..., min_length=2, max_length=120)
    brand: str = Field(..., min_length=2, max_length=80)
    category: str = Field(..., min_length=2, max_length=40)
    sku: str = Field(..., min_length=3, max_length=40)
    price: int = Field(..., ge=1, le=500000)
    rating: float = Field(default=4.0, ge=0, le=5)
    storage: str = Field(default="-", max_length=40)
    tag: str = Field(default="Featured", max_length=60)
    image: str = Field(..., min_length=5, max_length=500)
    gallery: list[str] = Field(default_factory=list)
    image_local: str | None = Field(default=None, max_length=500)
    gallery_local: list[str] = Field(default_factory=list)
    description: str = Field(..., min_length=10, max_length=220)
    long_description: str = Field(..., min_length=20, max_length=1500)
    features: list[str] = Field(default_factory=list)
    specs: dict[str, str] = Field(default_factory=dict)
    stock: int = Field(default=10, ge=0, le=100000)
    delivery_note: str = Field(default="Fast delivery available", max_length=120)


class OrderStatusUpdateRequest(BaseModel):
    status: str = Field(..., min_length=3, max_length=40)


class HealthResponse(BaseModel):
    status: str
    knowledge_base_loaded: bool


class DocumentResponse(BaseModel):
    id: str
    name: str
    content_type: str
    size: int
    status: str
    created_at: str


class AdminStatsResponse(BaseModel):
    user_count: int
    order_count: int
    chat_session_count: int
    uploaded_document_count: int


class AdminChatLogResponse(BaseModel):
    session_id: str
    user_name: str
    user_email: EmailStr
    title: str
    mode: str
    updated_at: str
    preview: str
