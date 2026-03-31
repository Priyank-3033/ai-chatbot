from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

from fastapi import HTTPException, status

from app.config import Settings


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.secret = settings.auth_secret.encode("utf-8")
        self.ttl_seconds = settings.auth_token_ttl_hours * 3600

    def hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return f"{salt.hex()}:{digest.hex()}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        salt_hex, digest_hex = stored_hash.split(":", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return hmac.compare_digest(actual, expected)

    def create_token(self, user_id: int) -> str:
        expires_at = int(time.time()) + self.ttl_seconds
        payload = f"{user_id}:{expires_at}"
        signature = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        raw_token = f"{payload}:{signature}".encode("utf-8")
        return base64.urlsafe_b64encode(raw_token).decode("utf-8")

    def parse_token(self, token: str) -> int:
        try:
            decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            user_id_str, expires_at_str, signature = decoded.split(":", maxsplit=2)
            payload = f"{user_id_str}:{expires_at_str}"
            expected = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Invalid token signature")
            if int(expires_at_str) < int(time.time()):
                raise ValueError("Token expired")
            return int(user_id_str)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
            ) from exc
