# Tests/test_regression_hci_invariance.py
# Guards the core contract: numeric HCI_v1 depends only on audio axes + host cap.
# Structural policy (TTC, exposures) and Goldilocks must not change HCI numbers.

from __future__ import annotations
import copy
from typing import Dict, Any

from Pipeline.end_to_end import score_from_extractor_payload
from Host.policy import Policy as HostPolicy


def _base_payload() -> Dict[str, Any]:
    # Representative audio axes near/above cap to exercise capping behavior
    return {
        "audio_axes": [0.62, 0.63, 0.61, 0.60, 0.64, 0.62],
        # Segmentation scaffolding (not strictly needed for invariance tests)
        "ttc_sec": 14.0,
        "ttc_conf": 0.55,  # will fail default gate=0.60
        "verse_span": [10.0, 16.0],
        "chorus_span": [30.0, 36.0],
        "sr": 44100,
        "signal": [0.0] * 1024,
    }


def test_hci_invariant_under_ttc_gate_toggle_and_exposures_flag():
    raw = _base_payload()

    # Baseline policy (gate=0.60, cap=0.58)
    pol = HostPolicy()

    out_a = score_from_extractor_payload(
        raw=raw,
        observed_market=0.48,
        observed_emotional=0.67,
        policy=pol,
    )
    hci_a = float(out_a["HCI_v1"]["HCI_v1_score"])

    # Flip structural flags and gate threshold; HCI must remain identical
    pol_b = copy.deepcopy(pol)
    pol_b.ttc_conf_gate = 0.30  # now TTC passes
    # (Exposures flag if you expose it; here we just demonstrate gate manipulation)
    out_b = score_from_extractor_payload(
        raw=raw,
        observed_market=0.48,
        observed_emotional=0.67,
        policy=pol_b,
    )
    hci_b = float(out_b["HCI_v1"]["HCI_v1_score"])

    assert hci_a == hci_b, "HCI must not change when structural gates/flags change."


def test_hci_invariant_when_ttc_missing_vs_present():
    raw_present = _base_payload()
    raw_missing = {k: v for k, v in raw_present.items() if k not in ("ttc_sec", "ttc_conf")}

    pol = HostPolicy()

    out_present = score_from_extractor_payload(
        raw=raw_present,
        observed_market=0.40,
        observed_emotional=0.40,
        policy=pol,
    )
    out_missing = score_from_extractor_payload(
        raw=raw_missing,
        observed_market=0.40,
        observed_emotional=0.40,
        policy=pol,
    )

    hci_present = float(out_present["HCI_v1"]["HCI_v1_score"])
    hci_missing = float(out_missing["HCI_v1"]["HCI_v1_score"])

    assert hci_present == hci_missing, "HCI must not depend on TTC presence/absence."


def test_hci_cap_enforced_by_host_only():
    # Make axes that would average above a hypothetical higher cap to ensure cap applies.
    raw = {
        "audio_axes": [0.90, 0.80, 0.85, 0.88, 0.92, 0.87],
        "sr": 44100,
    }
    pol = HostPolicy()
    # Default cap in HostPolicy should clamp HCI at pol.cap_audio
    out = score_from_extractor_payload(
        raw=raw,
        observed_market=0.50,
        observed_emotional=0.50,
        policy=pol,
    )
    hci = float(out["HCI_v1"]["HCI_v1_score"])
    assert abs(hci - pol.cap_audio) < 1e-9, "HCI must be capped by host policy only."