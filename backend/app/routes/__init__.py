from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.commerce import router as commerce_router
from app.routes.documents import router as documents_router
from app.routes.products import router as products_router
from app.routes.realtime import router as realtime_router
from app.routes.system import router as system_router

__all__ = [
    "admin_router",
    "auth_router",
    "chat_router",
    "commerce_router",
    "documents_router",
    "products_router",
    "realtime_router",
    "system_router",
]
