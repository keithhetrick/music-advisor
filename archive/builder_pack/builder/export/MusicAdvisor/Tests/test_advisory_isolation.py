from music_advisor.host.guards.import_guard import scan_for_forbidden_imports

def test_no_advisory_imports_in_engine_paths():
    offenders = scan_for_forbidden_imports(".")
    assert offenders == []
