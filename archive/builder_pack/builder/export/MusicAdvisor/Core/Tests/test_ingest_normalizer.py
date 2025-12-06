# MusicAdvisor/Core/tests/test_ingest_normalizer.py
from MusicAdvisor.Core.ingest_normalizer import adapt_pack

def test_adapter_maps_duration_and_tempo(tmp_path):
    # emulate your Automator schema
    pack = tmp_path/"demo.pack.json"
    pack.write_text('{"analysis":{"duration_sec":183.2,"tempo":{"bpm":86.0,"band":"84-88"}}, "meta":{"profile":"Pop","region":"US"}}')
    staged = adapt_pack(str(pack))
    assert staged["MVP"]["runtime_sec"] == 183.2
    assert staged["MVP"]["tempo_bpm"] == 86.0
    assert staged["MVP"]["tempo_band_bpm"] == "80–89" or staged["MVP"]["tempo_band_bpm"] in ("84–93","84-88","84–88")
    assert staged["MVP"]["MARKET_NORMS"]["profile"] == "Pop"
