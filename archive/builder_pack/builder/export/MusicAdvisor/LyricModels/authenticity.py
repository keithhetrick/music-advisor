from ._tone_rules import render_note
def evaluate_authenticity(text: str, mode: str) -> dict:
    hints = []
    if any(w in text.lower() for w in ["like a", "as if", "just like"]):
        hints.append(render_note("Beautiful comparisons — check the heartbeat beneath the image.", mode))
    if text.count("I ") + text.count("I'm") + text.count("me ") < 2:
        hints.append(render_note("If this is personal, invite one line that only you could write.", mode))
    return {
        "observations": [
            render_note("Aim for lived detail over performance posture.", mode)
        ],
        "nudges": hints[:2]
    }