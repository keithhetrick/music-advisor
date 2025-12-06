import textwrap
from ma_audio_engine import schemas


def test_lint_sidecar_payload_detects_issues():
    warnings = schemas.lint_sidecar_payload({"backend": "essentia", "tempo": 300, "mode": "phrygian"})
    assert "tempo_out_of_range" in warnings
    assert "mode_invalid" in warnings


def test_lint_sidecar_payload_beats_mismatch():
    warnings = schemas.lint_sidecar_payload({"backend": "essentia", "tempo": 120, "beats_sec": [0.1, 0.2], "beats_count": 3})
    assert "beats_count_mismatch" in warnings


def test_lint_client_rich_text_missing_keys():
    content = textwrap.dedent(
        """
        # header
        /audio import {"foo": "bar"}
        """
    )
    warnings = schemas.lint_client_rich_text(content)
    assert "missing:historical_echo_v1" in warnings
    assert "missing:historical_echo_meta" in warnings
    assert "missing:feature_pipeline_meta" in warnings


def test_lint_client_rich_text_ok():
    content = textwrap.dedent(
        """
        # header
        /audio import {
          "historical_echo_v1": {},
          "historical_echo_meta": {},
          "feature_pipeline_meta": {},
          "features": {"runtime_sec": 123},
          "features_full": {"runtime_sec": 123}
        }
        """
    )
    warnings = schemas.lint_client_rich_text(content)
    assert warnings == []


def test_lint_client_rich_text_ok_aliases_client():
    content = textwrap.dedent(
        """
        # header
        /audio import {
          "historical_echo_v1": {},
          "historical_echo_meta": {},
          "feature_pipeline_meta": {},
          "features": {"runtime_sec": 123},
          "features_full": {"runtime_sec": 123}
        }
        """
    )
    warnings = schemas.lint_client_rich_text(content)
    assert warnings == []
