from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    build_cart_response,
    build_order_response,
    build_wishlist_response,
    database,
    product_catalog,
    require_user,
)
from app.models import (
    CartAddRequest,
    CartResponse,
    CheckoutRequest,
    OrderResponse,
    UserPublic,
    WishlistResponse,
)


router = APIRouter()


@router.get("/api/wishlist", response_model=WishlistResponse)
def get_wishlist(current_user: UserPublic = Depends(require_user)) -> WishlistResponse:
    return build_wishlist_response(current_user.id)


@router.post("/api/wishlist/{product_id}", response_model=WishlistResponse)
def add_wishlist_item(product_id: str, current_user: UserPublic = Depends(require_user)) -> WishlistResponse:
    product = product_catalog.get_product(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    database.add_to_wishlist(current_user.id, product_id)
    return build_wishlist_response(current_user.id)


@router.delete("/api/wishlist/{product_id}", response_model=WishlistResponse)
def remove_wishlist_item(product_id: str, current_user: UserPublic = Depends(require_user)) -> WishlistResponse:
    database.remove_from_wishlist(current_user.id, product_id)
    return build_wishlist_response(current_user.id)


@router.get("/api/cart", response_model=CartResponse)
def get_cart(current_user: UserPublic = Depends(require_user)) -> CartResponse:
    return build_cart_response(current_user.id)


@router.post("/api/cart/items", response_model=CartResponse)
def add_cart_item(request: CartAddRequest, current_user: UserPublic = Depends(require_user)) -> CartResponse:
    product = product_catalog.get_product(request.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    database.add_to_cart(current_user.id, request.product_id, request.quantity)
    return build_cart_response(current_user.id)


@router.put("/api/cart/items/{product_id}", response_model=CartResponse)
def update_cart_item(product_id: str, request: CartAddRequest, current_user: UserPublic = Depends(require_user)) -> CartResponse:
    database.update_cart_quantity(current_user.id, product_id, request.quantity)
    return build_cart_response(current_user.id)


@router.get("/api/orders", response_model=list[OrderResponse])
def list_orders(current_user: UserPublic = Depends(require_user)) -> list[OrderResponse]:
    rows = database.list_orders(current_user.id)
    return [build_order_response(row) for row in rows]


@router.get("/api/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, current_user: UserPublic = Depends(require_user)) -> OrderResponse:
    row = database.get_order(order_id, current_user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return build_order_response(row)


@router.post("/api/orders/checkout", response_model=OrderResponse)
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
