from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError

from app.config import Settings


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.secret = settings.auth_secret
        self.ttl_seconds = settings.auth_token_ttl_hours * 3600
        self.algorithm = "HS256"

    def hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return f"{salt.hex()}:{digest.hex()}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        salt_hex, digest_hex = stored_hash.split(":", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return actual == expected

    def create_token(self, user_id: int) -> str:
        expires_at = datetime.now(UTC) + timedelta(seconds=self.ttl_seconds)
        payload = {
            "sub": str(user_id),
            "exp": expires_at,
            "iat": datetime.now(UTC),
            "type": "access",
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def parse_token(self, token: str) -> int:
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            if payload.get("type") != "access":
                raise ValueError("Invalid token type")
            subject = payload.get("sub")
            if subject is None:
                raise ValueError("Missing token subject")
            return int(subject)
        except (InvalidTokenError, ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
            ) from exc
