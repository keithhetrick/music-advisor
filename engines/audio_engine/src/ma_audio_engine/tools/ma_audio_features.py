"""
Legacy shim for console_scripts entrypoints that import ma_audio_engine.tools.ma_audio_features.
Delegates to the canonical tools/ma_audio_features.py.
"""

from tools.ma_audio_features import main


if __name__ == "__main__":
    raise SystemExit(main())
