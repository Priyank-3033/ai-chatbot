from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import product_catalog, require_user, to_product_response
from app.models import ProductListResponse, ProductResponse, UserPublic


router = APIRouter()


@router.get("/api/products", response_model=ProductListResponse)
def list_products(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=48),
    current_user: UserPublic = Depends(require_user),
) -> ProductListResponse:
    _ = current_user
    products = product_catalog.list_products(category=category, search=search)
    total = len(products)
    start = (page - 1) * page_size
    end = start + page_size
    return ProductListResponse(
        items=[to_product_response(product) for product in products[start:end]],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/api/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, current_user: UserPublic = Depends(require_user)) -> ProductResponse:
    _ = current_user
    product = product_catalog.get_product(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return to_product_response(product)


@router.get("/api/products/autocomplete", response_model=list[str])
def product_autocomplete(
    q: str = Query(..., min_length=1),
    current_user: UserPublic = Depends(require_user),
) -> list[str]:
    _ = current_user
    return product_catalog.autocomplete(q)


@router.get("/api/products/recommend", response_model=list[ProductResponse])
def recommend_products(
    q: str = Query(..., min_length=2),
    current_user: UserPublic = Depends(require_user),
) -> list[ProductResponse]:
    _ = current_user
    return [to_product_response(product) for product in product_catalog.recommend_products(q, limit=6)]
