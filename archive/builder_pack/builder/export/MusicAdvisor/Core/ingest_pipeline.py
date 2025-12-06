# MusicAdvisor/Core/ingest_pipeline.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
from MusicAdvisor.Core.ingest_normalizer import adapt_pack

def ingest(pack_path: str, helper_txt: str) -> Dict[str, Any]:
    """
    Entry point used by advisor_cli.py.
    Builds a staged dict with MVP/Buckets/Audit ready for scoring.
    Accepts client/GPT helper text; content shape is identical.
    """
    pack_path = str(Path(pack_path).resolve())
    staged = adapt_pack(pack_path, helper_txt)
    return staged
