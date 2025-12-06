#!/usr/bin/env python3
"""
Wrapper to load the real helper CLI from tools/ma_helper/cli.py.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_inner():
    root = Path(__file__).resolve().parents[1]
    target = root / "tools" / "ma_helper" / "cli.py"
    spec = importlib.util.spec_from_file_location("ma_helper_inner", target)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load tools/ma_helper/cli.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ma_helper_inner"] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    inner = _load_inner()
    return inner.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
