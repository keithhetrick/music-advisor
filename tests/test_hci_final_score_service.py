from tools.hci_final_score import apply_final_score


def test_apply_final_score_recomputes_and_attaches_meta():
    hci = {"HCI_v1_score": 0.7, "HCI_v1_role": "wip"}
    updated = apply_final_score(hci, recompute=True)
    assert "HCI_v1_final_score" in updated
    assert "HCI_v1_metric_kind" in updated
    assert updated["HCI_v1_metric_kind"] == "historical_echo_audio"
