"""
Smoke guardrails for HCI builder / Automator DB wiring.

We previously hit a regression where the historical echo DB path was not
propagated to the echo probes, causing Automator runs to fail. These tests
assert the shell scripts include the explicit DB handoff to avoid silent
fallbacks in future edits.
"""
from pathlib import Path


def test_ma_hci_builder_passes_db_path():
    script = Path("infra/scripts/ma_hci_builder.sh").read_text()
    # HCI echo injection must receive an explicit DB path.
    assert '--db "$DB_PATH"' in script, "ma_hci_builder.sh must pass --db to echo probes"
    # Both echo injections (HCI + client.rich) should receive the DB path.
    assert script.count('--db "$DB_PATH"') >= 2, "ma_hci_builder.sh should pass --db in both echo steps"


def test_automator_exports_historical_echo_db():
    script = Path("automator.sh").read_text()
    assert "HISTORICAL_ECHO_DB" in script, "automator.sh should export HISTORICAL_ECHO_DB for builder"
