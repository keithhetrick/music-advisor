"""
Lightweight inbound request validation for chat/HTTP entrypoints.
"""
from __future__ import annotations

from typing import Any, Dict


class RequestValidationError(ValueError):
    pass


def validate_chat_request(data: Dict[str, Any]) -> None:
    """
    Ensure inbound request has the expected fields and types.
    """
    if not isinstance(data, dict):
        raise RequestValidationError("Request body must be an object")
    if "message" not in data or not isinstance(data.get("message"), str) or not data["message"].strip():
        raise RequestValidationError("Missing or invalid message")
    if data.get("payload") is not None and not isinstance(data["payload"], dict):
        raise RequestValidationError("payload must be an object when provided")
    if data.get("norms") is not None and not isinstance(data["norms"], dict):
        raise RequestValidationError("norms must be an object when provided")
    if data.get("profile") is not None and not isinstance(data["profile"], str):
        raise RequestValidationError("profile must be a string")
    if data.get("session") is not None and not isinstance(data["session"], dict):
        raise RequestValidationError("session must be an object when provided")
    if data.get("client_rich_path") is not None and not isinstance(data["client_rich_path"], str):
        raise RequestValidationError("client_rich_path must be a string when provided")


def enforce_size_caps(data: Dict[str, Any], max_payload_bytes: int, max_norms_bytes: int) -> None:
    """
    Reject requests whose payload/norms exceed configured byte caps.
    """
    if data.get("payload") is not None:
        size = len(str(data["payload"]).encode("utf-8"))
        if size > max_payload_bytes:
            raise RequestValidationError("payload too large")
    if data.get("norms") is not None:
        size = len(str(data["norms"]).encode("utf-8"))
        if size > max_norms_bytes:
            raise RequestValidationError("norms too large")
