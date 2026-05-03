from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import auth_service, require_user, register_user, to_user_public
from app.models import AuthResponse, LoginRequest, PasswordResetRequest, RegisterRequest, UserPublic
from app.dependencies import database


router = APIRouter()


def _client_ip(http_request: Request) -> str:
    return http_request.client.host if http_request.client else ""


@router.post("/api/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest, http_request: Request) -> AuthResponse:
    password_hash = auth_service.hash_password(request.password)
    user_row = register_user(request.name.strip(), request.email, password_hash, request.phone.strip())
    token = auth_service.create_token(user_row["id"], user_row["token_version"])
    database.record_audit_log(
        event_type="user.register",
        severity="low",
        user_id=user_row["id"],
        ip_address=_client_ip(http_request),
        description=f"New account created for {request.email.lower()}",
        metadata={"role": user_row["role"]},
    )
    return AuthResponse(token=token, user=to_user_public(user_row))


@router.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest, http_request: Request) -> AuthResponse:
    client_ip = _client_ip(http_request)
    attempt_state = database.get_login_attempt_state(request.email)
    if attempt_state and attempt_state["locked_until"]:
        locked_until = datetime.fromisoformat(attempt_state["locked_until"])
        if locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Too many failed login attempts. Please try again later.",
            )
    user_row = database.get_user_by_email(request.email)
    if not user_row or not auth_service.verify_password(request.password, user_row["password_hash"]):
        attempts, locked_until = database.register_failed_login_attempt(
            request.email,
            max_attempts=auth_service.settings.login_max_attempts,
            lock_minutes=auth_service.settings.login_lock_minutes,
        )
        database.record_audit_log(
            event_type="auth.login_failed",
            severity="medium",
            ip_address=client_ip,
            description=f"Failed login for {request.email.lower()}",
            metadata={"attempt_count": str(attempts)},
        )
        if locked_until:
            database.create_security_alert(
                alert_type="failed_login_burst",
                severity="high",
                ip_address=client_ip,
                message=f"Account temporarily locked after repeated failed login attempts for {request.email.lower()}",
                metadata={"email": request.email.lower(), "locked_until": locked_until},
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    database.clear_login_attempts(request.email)
    token = auth_service.create_token(user_row["id"], user_row["token_version"])
    database.record_audit_log(
        event_type="auth.login_success",
        severity="low",
        user_id=user_row["id"],
        ip_address=client_ip,
        description=f"Successful login for {request.email.lower()}",
        metadata={"role": user_row["role"]},
    )
    return AuthResponse(token=token, user=to_user_public(user_row))


@router.post("/api/auth/password-reset", response_model=AuthResponse)
def password_reset(request: PasswordResetRequest, http_request: Request) -> AuthResponse:
    password_hash = auth_service.hash_password(request.new_password)
    user_row = database.reset_password_with_phone(request.email, request.phone, password_hash)
    if not user_row:
        database.record_audit_log(
            event_type="auth.password_reset_failed",
            severity="medium",
            ip_address=_client_ip(http_request),
            description=f"Failed password reset attempt for {request.email.lower()}",
            metadata={"reason": "email_phone_mismatch"},
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found for the provided email and phone number.")
    database.record_audit_log(
        event_type="auth.password_reset_success",
        severity="medium",
        user_id=user_row["id"],
        ip_address=_client_ip(http_request),
        description=f"Password reset completed for {request.email.lower()}",
        metadata={"role": user_row["role"]},
    )
    token = auth_service.create_token(user_row["id"], user_row["token_version"])
    return AuthResponse(token=token, user=to_user_public(user_row))


@router.post("/api/auth/revoke-sessions", response_model=AuthResponse)
def revoke_sessions(current_user: UserPublic = Depends(require_user)) -> AuthResponse:
    user_row = database.rotate_token_version(current_user.id)
    if not user_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    database.record_audit_log(
        event_type="auth.sessions_revoked",
        severity="medium",
        user_id=current_user.id,
        description=f"Revoked other sessions for {current_user.email.lower()}",
        metadata={"role": user_row["role"]},
    )
    token = auth_service.create_token(user_row["id"], user_row["token_version"])
    return AuthResponse(token=token, user=to_user_public(user_row))


@router.get("/api/auth/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(require_user)) -> UserPublic:
    return current_user
