"""
Minimal OAuth ID token verification helper (Google first).
This is deliberately light; in production you would cache JWKs and verify signatures.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from typing import Any, Dict, Optional


class AuthError(ValueError):
    pass


GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_JWKS_CACHE: Dict[str, Any] = {}
_JWKS_FETCH_TS: Optional[float] = None
_JWKS_TTL = 3600  # 1 hour


def _decode_unverified(jwt: str) -> Dict[str, Any]:
    try:
        parts = jwt.split(".")
        if len(parts) != 3:
            raise AuthError("Invalid JWT format")
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload
    except Exception as exc:  # noqa: BLE001
        raise AuthError(f"Failed to decode token: {exc}") from exc


def _fetch_jwks(url: str = GOOGLE_JWKS_URL) -> Dict[str, Any]:
    global _JWKS_CACHE, _JWKS_FETCH_TS
    now = time.time()
    if _JWKS_CACHE and _JWKS_FETCH_TS and now - _JWKS_FETCH_TS < _JWKS_TTL:
        return _JWKS_CACHE
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        data = json.loads(resp.read())
        _JWKS_CACHE = data
        _JWKS_FETCH_TS = now
        return data


def verify_google_id_token(
    id_token: str,
    client_id: str,
    leeway: int = 60,
    force_verify_sig: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Lightweight verification of a Google ID token.
    - Decodes JWT
    - Checks issuer, audience, expiry
    Signature verification:
      - If PyJWT is available and not explicitly disabled, verify signature against JWKs.
      - Otherwise, perform a best-effort JWK presence check.
    """
    payload = _decode_unverified(id_token)
    iss = payload.get("iss")
    aud = payload.get("aud")
    exp = payload.get("exp")
    if iss not in ("accounts.google.com", "https://accounts.google.com"):
        raise AuthError("Invalid issuer")
    if aud != client_id:
        raise AuthError("Invalid audience")
    if exp is None or time.time() > (exp + leeway):
        raise AuthError("Token expired")
    # Best-effort JWK presence (not full signature verification)
    try:
        header_b64 = id_token.split(".")[0] + "=" * (-len(id_token.split(".")[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))
        kid = header.get("kid")
        jwks = _fetch_jwks()
        keys = {k.get("kid"): k for k in jwks.get("keys", [])}
        if kid and kid not in keys:
            raise AuthError("Unknown key id")
    except AuthError:
        raise
    except Exception:
        # Non-fatal; rely on expiry/audience/issuer checks
        pass

    # Optional full signature verification
    env_verify = os.getenv("HOST_VERIFY_GOOGLE_SIG", "").lower()
    auto_verify = env_verify not in ("0", "false", "no")
    do_verify = force_verify_sig if force_verify_sig is not None else auto_verify
    if do_verify:
        try:
            import jwt  # type: ignore
            jwks = _fetch_jwks()
            jwt.decode(
                id_token,
                key=jwks,
                algorithms=["RS256"],
                audience=client_id,
                issuer=iss,
                options={"verify_at_hash": False},
            )
        except ImportError:
            # PyJWT not installed; skip signature verify
            pass
        except Exception as exc:  # noqa: BLE001
            raise AuthError(f"Signature verification failed: {exc}") from exc
    return payload


def decode_google_token_no_sig(id_token: str) -> Dict[str, Any]:
    """
    Minimal decode path without signature verification (for local/dev use).
    """
    payload = _decode_unverified(id_token)
    return payload


__all__ = ["verify_google_id_token", "decode_google_token_no_sig", "AuthError"]
