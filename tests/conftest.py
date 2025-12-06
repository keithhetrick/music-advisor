"""
Test bootstrap helper to ensure repository imports work under pytest.

Pytest does not automatically add the repo root to sys.path, so adapter
imports can fail when tests are executed from arbitrary working directories.
This hook normalizes the path upfront via the shared bootstrap helper.
"""
import os
import sys


# Make sure the repo root is on sys.path before importing adapters.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
_SRC = os.path.join(_ROOT, "src")
# Ensure repo root is ahead of src to prefer in-repo adapters package
sys.path = [p for p in sys.path if os.path.abspath(p) != os.path.abspath(_SRC)]
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ["PATH"] = f"{_ROOT}{os.pathsep}{os.environ.get('PATH', '')}"

from ma_audio_engine.adapters.bootstrap import ensure_repo_root  # noqa: E402


ensure_repo_root()
