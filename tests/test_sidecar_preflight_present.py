from pathlib import Path


def test_sidecar_preflight_script_exists_and_executable():
    """Guardrail: ensure sidecar dependency preflight script is present + executable (Automator relies on it)."""
    script = Path("infra/scripts/check_sidecar_deps.sh")
    assert script.exists(), "sidecar preflight script missing"
    assert script.stat().st_mode & 0o111, "sidecar preflight script not executable"
