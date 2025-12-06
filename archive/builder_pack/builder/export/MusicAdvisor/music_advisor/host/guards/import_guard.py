from __future__ import annotations
from pathlib import Path
FORBIDDEN = ("music_advisor.advisory","advisory","trend","trends","reco","recommend","gpt","client")
ENGINE_DIR_HINTS = ("ma_hf_audiotools","music_advisor/host","engines","features","segmentation")
def scan_for_forbidden_imports(repo_root: str = ".") -> list[str]:
    root = Path(repo_root); offenders = []
    for p in root.rglob("*.py"):
        if not any(h in str(p).replace("\\","/") for h in ENGINE_DIR_HINTS): continue
        try: text = p.read_text(encoding="utf-8")
        except Exception: continue
        L = text.lower()
        if any(f"import {k}" in L or f"from {k} " in L for k in FORBIDDEN): offenders.append(str(p))
    return offenders
