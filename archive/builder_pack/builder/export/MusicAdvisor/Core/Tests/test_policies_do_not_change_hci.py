# MusicAdvisor/Core/tests/test_policies_do_not_change_hci.py
from MusicAdvisor.Core.engine import run_hci  # your scorer entrypoint
from MusicAdvisor.Core.ingest_pipeline import ingest

def test_goldilocks_does_not_change_numeric_hci(example_pack_path, gpt_a, gpt_b):
    # gpt_a and gpt_b differ ONLY in GOLDILOCKS priors/caps wording
    staged_a = ingest(example_pack_path, open(gpt_a).read())
    staged_b = ingest(example_pack_path, open(gpt_b).read())
    out_a = run_hci(staged_a)   # returns dict with HCI_v1 and subdomains
    out_b = run_hci(staged_b)
    # Numeric HCI and subdomains must match exactly
    assert out_a["HCI_v1"]["HCI_v1_score"] == out_b["HCI_v1"]["HCI_v1_score"]
    for k in ["Historical","Cultural","Market","Emotional","Sonic","Creative"]:
        assert out_a["HCI_v1"][k] == out_b["HCI_v1"][k]
import pytest

pytest.skip("Engine fixtures not available in this environment; skipped under client rollout.", allow_module_level=True)
