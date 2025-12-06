# Lightweight router glue for GPT to conceptually call.
# This file documents the contract; GPT composes the final language using these anchors.

def lyric_ei_request(text: str, mode: str = "hybrid") -> dict:
    """
    GPT entrypoint concept: returns a structured advisory object.
    """
    try:
        from MusicAdvisor.LyricModels import run_lyric_ei
        return run_lyric_ei(text, mode=mode)
    except Exception as e:
        return {"error": str(e), "meta": {"scoring": False}}