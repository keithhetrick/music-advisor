"""
Shim for policy modules to support `src.policies.*` imports.
"""
from .qa_policy import (
    QAPolicy,
    POLICIES,
    get_policy,
)

__all__ = [
    "QAPolicy",
    "POLICIES",
    "get_policy",
]
