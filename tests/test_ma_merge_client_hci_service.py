from tools.ma_merge_client_and_hci import merge_client_hci


def test_merge_client_hci_basic():
    client = {"audio_name": "song", "region": "US", "profile": "Pop"}
    hci = {"HCI_v1_final_score": 0.6, "HCI_v1_role": "test"}
    merged, rich_text, warns, scores = merge_client_hci(client, hci)
    assert merged["HCI_v1_final_score"] == 0.6
    assert isinstance(warns, list)
    assert isinstance(rich_text, str)
