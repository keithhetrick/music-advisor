from pathlib import Path


def test_no_sys_path_mutations_outside_allowlist():
    """
    Guardrail: flag new sys.path mutations outside an allowlist of legacy scripts.
    """
    repo = Path(__file__).resolve().parent.parent
    allow = {
        "sitecustomize.py",
        # Legacy tooling still using sys.path hacks; trim over time.
        "engines/audio_engine/src/ma_audio_engine/adapters_src/bootstrap.py",
        # Known legacy callers; retain until refactored.
        "tools/lyric_wip_pipeline.py",
        "engines/lyrics_engine/tools/lyric_wip_pipeline.py",
        "tools/append_metadata_to_client_rich.py",
        "tools/pipeline_driver.py",
        "archive/builder_pack/builder/export/MusicAdvisor/Tools/smoke_end_to_end.py",
        "archive/builder_pack/builder/export/MusicAdvisor/Core/Tests/conftest.py",
        "archive/builder_pack/builder/export/MusicAdvisor/Tests/conftest.py",
        "archive/builder_pack/builder/export/MusicAdvisor/CLI/advisor_cli.py",
    }
    offenders = []
    for path in repo.rglob("*.py"):
        if "tests" in path.parts or "ma_config" in path.parts or "__pycache__" in path.parts:
            continue
        if ".venv" in path.parts or "vendor" in path.parts:
            continue
        if "archive_shims" in path.parts:
            continue
        # Skip legacy audio spine/external tooling for now
        if "audio" in path.parts and "spine" in path.parts:
            continue
        if "external" in path.parts:
            continue
        rel = str(path.relative_to(repo))
        if rel in allow:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "sys.path" in text:
            offenders.append(rel)
    assert not offenders, f"sys.path mutation detected in: {offenders}"
