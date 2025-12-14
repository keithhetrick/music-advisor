"""Verify wrapper."""
from __future__ import annotations

from ma_helper.commands.tooling import handle_verify


def run_verify(args, affected_fn, post_hint):
    return handle_verify(args, affected_fn, post_hint)
