"""
Auth provider interfaces and implementations.
"""
from __future__ import annotations

from typing import Dict, Optional

from advisor_host.auth.auth import AuthError, decode_google_token_no_sig, verify_google_id_token


class AuthContext:
    def __init__(self, user_id: Optional[str] = None, email: Optional[str] = None):
        self.user_id = user_id
        self.email = email


class AuthProvider:
    def verify(self, headers: Dict[str, str]) -> AuthContext:
        raise NotImplementedError


class NoAuthProvider(AuthProvider):
    def verify(self, headers: Dict[str, str]) -> AuthContext:
        return AuthContext(user_id=None)


class StaticBearerAuthProvider(AuthProvider):
    def __init__(self, token: str):
        self.token = token

    def verify(self, headers: Dict[str, str]) -> AuthContext:
        hdr = headers.get("Authorization", "")
        if hdr != f"Bearer {self.token}":
            raise AuthError("unauthorized")
        return AuthContext(user_id="static_token_user")


class GoogleAuthProvider(AuthProvider):
    def __init__(self, client_id: str, verify_sig: bool = False):
        self.client_id = client_id
        self.verify_sig = verify_sig

    def verify(self, headers: Dict[str, str]) -> AuthContext:
        hdr = headers.get("Authorization", "")
        if not hdr.startswith("Bearer "):
            raise AuthError("missing bearer token")
        id_token = hdr.removeprefix("Bearer ").strip()
        if self.verify_sig:
            payload = verify_google_id_token(id_token, self.client_id)
        else:
            payload = decode_google_token_no_sig(id_token)
        return AuthContext(user_id=payload.get("sub") or payload.get("email"), email=payload.get("email"))


__all__ = [
    "AuthContext",
    "AuthProvider",
    "NoAuthProvider",
    "StaticBearerAuthProvider",
    "GoogleAuthProvider",
]
