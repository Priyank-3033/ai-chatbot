from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import auth_service, require_user, register_user, to_user_public
from app.models import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from app.dependencies import database


router = APIRouter()


@router.post("/api/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest) -> AuthResponse:
    password_hash = auth_service.hash_password(request.password)
    user_row = register_user(request.name.strip(), request.email, password_hash)
    token = auth_service.create_token(user_row["id"])
    return AuthResponse(token=token, user=to_user_public(user_row))


@router.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    user_row = database.get_user_by_email(request.email)
    if not user_row or not auth_service.verify_password(request.password, user_row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    token = auth_service.create_token(user_row["id"])
    return AuthResponse(token=token, user=to_user_public(user_row))


@router.get("/api/auth/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(require_user)) -> UserPublic:
    return current_user
