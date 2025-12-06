# Back-compat shim so existing code/tests can still do:
#   from music-advisor.always_present import coerce_payload_shape
# Keep real code in ma_audiotools. Prefer `from ma_audio_engine.always_present import coerce_payload_shape`.
import warnings

warnings.warn(
    "music-advisor is deprecated; import ma_audio_engine.always_present instead.",
    DeprecationWarning,
    stacklevel=2,
)
__all__ = []
