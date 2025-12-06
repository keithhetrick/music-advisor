from tools import names


def test_client_token_defaults():
    # The client token should be stable to avoid surprises across platforms.
    assert names.CLIENT_TOKEN == "client"
    assert names.client_txt_suffix() == ".client.txt"
    assert names.client_json_suffix() == ".client.json"
    assert names.client_rich_suffix() == ".client.rich.txt"


def test_client_globs():
    assert names.client_txt_globs() == ["*.client.txt"]
    assert names.client_json_globs() == ["*.client.json"]
    assert names.client_rich_globs() == ["*.client.rich.txt"]
