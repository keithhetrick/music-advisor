"""
Legacy shim for console_scripts that import ma_audio_engine.tools.equilibrium_merge.
Delegates to the canonical tools/equilibrium_merge.py.
"""

from tools.equilibrium_merge import main


if __name__ == "__main__":
    raise SystemExit(main())
