import warnings
from ma_audiotools.always_present import coerce_payload_shape

warnings.warn(
    "music-advisor.always_present is deprecated; import ma_audio_engine.always_present instead.",
    DeprecationWarning,
    stacklevel=2,
)
__all__ = ["coerce_payload_shape"]
