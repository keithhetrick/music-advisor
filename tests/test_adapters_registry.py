import os

from ma_audio_engine.adapters.backend_registry_adapter import (
    list_supported_backends,
    get_default_sidecar_cmd,
    is_backend_enabled,
    get_backend_settings,
)
from ma_audio_engine.adapters.qa_policy_adapter import load_qa_policy
from tools.sidecar_adapter import DEFAULT_SIDECAR_CMD


def test_backend_registry_defaults():
    backends = list_supported_backends()
    assert isinstance(backends, list)
    assert "librosa" in backends
    assert get_default_sidecar_cmd() == DEFAULT_SIDECAR_CMD
    # Enabled by default
    assert is_backend_enabled("essentia") is True
    assert get_backend_settings("nonexistent") == {}


def test_qa_policy_adapter_respects_env_override(monkeypatch):
    monkeypatch.setenv("QA_POLICY", "strict")
    policy = load_qa_policy("strict")
    assert policy.clip_peak_threshold <= 1.0
    # lenient/default should still load even if env is strict
    policy_default = load_qa_policy("default")
    assert policy_default.clip_peak_threshold == policy.clip_peak_threshold
