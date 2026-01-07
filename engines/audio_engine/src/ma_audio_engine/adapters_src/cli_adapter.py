"""
CLI adapter helpers to keep option schemas consistent across tools.

Purpose:
- Standardize common flags (log json/sandbox, preflight, QA policy) across CLIs.
- Apply env fallbacks so tools behave consistently whether invoked via Automator or direct CLI.

Usage:
- In argparse setup: call `add_log_format_arg(parser)`, `add_log_sandbox_arg(parser)`, `add_preflight_arg(parser)`, `add_qa_policy_arg(parser)`.
- After parsing: `apply_log_format_env(args)`, `apply_log_sandbox_env(args)`, `run_preflight_if_requested(args)`.
"""
from __future__ import annotations

import os
import argparse
import sys
from pathlib import Path
from shared.security import subprocess as sec_subprocess
from shared.security.config import CONFIG as SEC_CONFIG

__all__ = [
    "add_log_sandbox_arg",
    "add_log_format_arg",
    "apply_log_format_env",
    "add_preflight_arg",
    "run_preflight_if_requested",
    "add_qa_policy_arg",
    "apply_log_sandbox_env",
]


def add_log_sandbox_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--log-sandbox",
        action="store_true",
        help="Enable sandbox log scrubbing (also controllable via LOG_SANDBOX=1).",
    )


def add_log_format_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--log-json",
        action="store_true",
        help="Emit structured JSON logs (also honors env LOG_JSON=1).",
    )


def apply_log_format_env(args) -> None:
    if getattr(args, "log_json", False):
        os.environ["LOG_JSON"] = "1"


def add_preflight_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run preflight check (deps/files) before executing the CLI.",
    )


def run_preflight_if_requested(args) -> None:
    if not getattr(args, "preflight", False):
        return
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "preflight_check.py"
    cmd = [sys.executable, str(script)]
    sec_subprocess.run_safe(
        cmd,
        allow_roots=SEC_CONFIG.allowed_binary_roots,
        timeout=SEC_CONFIG.subprocess_timeout,
        check=True,
    )


def add_qa_policy_arg(parser: argparse.ArgumentParser, env_var: str = "QA_POLICY") -> None:
    default = os.getenv(env_var, None)
    parser.add_argument(
        "--qa-policy",
        type=str,
        default=default,
        help="Select QA policy preset (default honors {} env or built-in defaults).".format(env_var),
    )


def apply_log_sandbox_env(args) -> None:
    if getattr(args, "log_sandbox", False):
        os.environ["LOG_SANDBOX"] = "1"
