"""
Optional LLM paraphrase hook for chat replies.
Safe usage: paraphrase already-assembled text without adding new facts.
"""
from __future__ import annotations

import os
from typing import Callable


def make_paraphrase_fn(llm_client: Callable[[str], str], max_chars: int = 400) -> Callable[[str], str]:
    """
    Wrap an LLM client (callable prompt->str) into a paraphrase_fn suitable for ChatSession.extras.
    The LLM should be prompted upstream to not alter facts/numbers.
    """
    def _paraphrase(text: str) -> str:
        if not text:
            return text
        prompt = (
            "Rephrase the following reply concisely. Do NOT add or change any facts, numbers, or percentages. "
            f"Keep it under {max_chars} characters. Reply with the rewritten text only.\n\n{text}"
        )
        return llm_client(prompt)
    return _paraphrase


def env_paraphrase_enabled() -> bool:
    return os.getenv("CHAT_PARAPHRASE_ENABLED", "").lower() in ("1", "true", "yes")


__all__ = ["make_paraphrase_fn", "env_paraphrase_enabled"]
