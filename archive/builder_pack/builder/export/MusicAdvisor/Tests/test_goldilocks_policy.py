# Tests/test_goldilocks_policy.py
from __future__ import annotations
from Host.goldilocks import goldilocks_advise, GoldilocksConfig
from music_advisor.host.kpi import hci_v1
from music_advisor.host.policy import Policy

def test_goldilocks_is_advisory_only():
    # HCI is ALWAYS computed by host KPI; Goldilocks does NOT change it.
    axes = [0.62, 0.63, 0.61, 0.60, 0.64, 0.62]
    h = hci_v1(axes, Policy())   # should cap at 0.58
    advice = goldilocks_advise(observed_market=0.40, observed_emotional=0.70)
    assert abs(h - 0.58) < 1e-9
    assert "advisory" in advice
    assert "safety" in advice and "HCI remains unchanged" in advice["safety"]["note"]
