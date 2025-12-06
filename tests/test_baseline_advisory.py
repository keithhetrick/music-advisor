import json, subprocess, tempfile, pathlib, sys
def test_smoke_has_advisory():
    # 1s tone
    import math, wave, struct
    sr=44100; n=int(sr*1.0)
    wav=pathlib.Path("tone.wav")
    with wave.open(str(wav),"w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        for i in range(n): w.writeframes(struct.pack("<h", int(0.2*32767*math.sin(2*math.pi*440*i/sr))))
    # run
    cmd = [
        sys.executable,
        "-m",
        "ma_audio_engine.pipe_cli",
        "--audio",
        str(wav),
        "--market",
        "0.48",
        "--emotional",
        "0.67",
        "--round",
        "3",
        "--out",
        "advisory.json",
    ]
    out = subprocess.check_output(cmd, text=True)
    d=json.loads(pathlib.Path("advisory.json").read_text())
    assert "HCI_v1" in d and "HCI_v1_score" in d["HCI_v1"]
    assert "Baseline" in d and "MARKET_NORMS" in d["Baseline"]
    adv=d["Baseline"].get("advisory",{})
    assert "Market_Fit" in adv and "tempo" in adv and "key" in adv and "runtime" in adv
