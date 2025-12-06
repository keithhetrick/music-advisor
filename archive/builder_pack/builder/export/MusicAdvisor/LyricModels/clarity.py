from ._tone_rules import render_note
def evaluate_clarity(text: str, mode: str) -> dict:
    core_q = render_note("What’s the one-sentence truth the listener can retell?", mode)
    long_lines = [ln for ln in text.splitlines() if len(ln) > 90]
    nudges = []
    if long_lines:
        nudges.append(render_note("Tighten one long line; sharpen the image so the truth cuts cleaner.", mode))
    return {
        "observations": [core_q],
        "nudges": nudges[:2]
    }