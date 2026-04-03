from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import (
    build_order_response,
    database,
    get_required_admin,
    product_catalog,
    require_user,
    to_admin_chat_log,
    to_admin_stats_response,
    to_product_response,
)
from app.models import AdminChatLogResponse, AdminStatsResponse, OrderResponse, OrderStatusUpdateRequest, ProductResponse, ProductUpsertRequest, UserPublic


router = APIRouter()


def require_admin_user(current_user: UserPublic = Depends(require_user)) -> UserPublic:
    return get_required_admin(current_user)


@router.get("/api/admin/stats", response_model=AdminStatsResponse)
def get_admin_stats(current_user: UserPublic = Depends(require_admin_user)) -> AdminStatsResponse:
    _ = current_user
    return to_admin_stats_response(database.admin_stats())


@router.get("/api/admin/chat-logs", response_model=list[AdminChatLogResponse])
def get_admin_chat_logs(
    limit: int = Query(default=30, ge=1, le=200),
    current_user: UserPublic = Depends(require_admin_user),
) -> list[AdminChatLogResponse]:
    _ = current_user
    return [to_admin_chat_log(row) for row in database.admin_chat_logs(limit)]


@router.put("/api/admin/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: str, request: OrderStatusUpdateRequest, current_user: UserPublic = Depends(require_admin_user)) -> OrderResponse:
    _ = current_user
    order_row = database.update_order_status(order_id, request.status)
    if not order_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return build_order_response(order_row)


@router.post("/api/admin/products", response_model=ProductResponse)
def create_product(request: ProductUpsertRequest, current_user: UserPublic = Depends(require_admin_user)) -> ProductResponse:
    _ = current_user
    if product_catalog.get_product(request.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product ID already exists.")
    product = product_catalog.upsert_product(request.model_dump())
    return to_product_response(product)


@router.put("/api/admin/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, request: ProductUpsertRequest, current_user: UserPublic = Depends(require_admin_user)) -> ProductResponse:
    _ = current_user
    if product_id != request.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product ID mismatch.")
    product = product_catalog.upsert_product(request.model_dump())
    return to_product_response(product)


@router.delete("/api/admin/products/{product_id}")
def delete_product(product_id: str, current_user: UserPublic = Depends(require_admin_user)) -> dict[str, str]:
    _ = current_user
    deleted = product_catalog.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return {"status": "deleted"}
