from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import (
    build_security_overview,
    build_order_response,
    database,
    get_required_admin,
    get_required_security_user,
    product_catalog,
    require_user,
    to_audit_log_response,
    to_admin_chat_log,
    to_admin_stats_response,
    to_product_response,
    to_security_alert_response,
)
from app.models import AdminChatLogResponse, AdminStatsResponse, AuditLogResponse, OrderResponse, OrderStatusUpdateRequest, ProductResponse, ProductUpsertRequest, SecurityAlertResponse, SecurityOverviewResponse, UserPublic


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


@router.get("/api/admin/security-overview", response_model=SecurityOverviewResponse)
def get_security_overview(current_user: UserPublic = Depends(require_user)) -> SecurityOverviewResponse:
    _ = get_required_security_user(current_user)
    return build_security_overview()


@router.get("/api/admin/audit-logs", response_model=list[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(default=30, ge=1, le=200),
    current_user: UserPublic = Depends(require_user),
) -> list[AuditLogResponse]:
    _ = get_required_security_user(current_user)
    return [to_audit_log_response(row) for row in database.recent_audit_logs(limit)]


@router.get("/api/admin/security-alerts", response_model=list[SecurityAlertResponse])
def get_security_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserPublic = Depends(require_user),
) -> list[SecurityAlertResponse]:
    _ = get_required_security_user(current_user)
    return [to_security_alert_response(row) for row in database.recent_security_alerts(limit)]


@router.put("/api/admin/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: str, request: OrderStatusUpdateRequest, current_user: UserPublic = Depends(require_admin_user)) -> OrderResponse:
    database.record_audit_log(
        event_type="admin.order_status_update",
        severity="medium",
        user_id=current_user.id,
        description=f"Order {order_id} status changed to {request.status}",
        metadata={"order_id": order_id, "status": request.status},
    )
    order_row = database.update_order_status(order_id, request.status)
    if not order_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return build_order_response(order_row)


@router.post("/api/admin/products", response_model=ProductResponse)
def create_product(request: ProductUpsertRequest, current_user: UserPublic = Depends(require_admin_user)) -> ProductResponse:
    if product_catalog.get_product(request.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product ID already exists.")
    product = product_catalog.upsert_product(request.model_dump())
    database.record_audit_log(
        event_type="admin.product_create",
        severity="medium",
        user_id=current_user.id,
        description=f"Product {request.id} created",
        metadata={"product_id": request.id, "name": request.name},
    )
    return to_product_response(product)


@router.put("/api/admin/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, request: ProductUpsertRequest, current_user: UserPublic = Depends(require_admin_user)) -> ProductResponse:
    if product_id != request.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product ID mismatch.")
    product = product_catalog.upsert_product(request.model_dump())
    database.record_audit_log(
        event_type="admin.product_update",
        severity="medium",
        user_id=current_user.id,
        description=f"Product {product_id} updated",
        metadata={"product_id": product_id, "name": request.name},
    )
    return to_product_response(product)


@router.delete("/api/admin/products/{product_id}")
def delete_product(product_id: str, current_user: UserPublic = Depends(require_admin_user)) -> dict[str, str]:
    deleted = product_catalog.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    database.record_audit_log(
        event_type="admin.product_delete",
        severity="high",
        user_id=current_user.id,
        description=f"Product {product_id} deleted",
        metadata={"product_id": product_id},
    )
    return {"status": "deleted"}
