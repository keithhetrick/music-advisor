from ._tone_rules import render_note
def evaluate_resonance(text: str, mode: str) -> dict:
    punch = []
    for tag in ["love", "hurt", "home", "alone", "stay", "leave"]:
        if tag in text.lower(): punch.append(tag)
    note = "Common themes present — ensure one line hurts in a way only this song can."
    if not punch:
        note = "If the theme avoids common words, let the feeling still be unmistakable."
    return {
        "observations": [render_note(note, mode)],
        "nudges": [render_note("Find the ‘soul line’ — the sentence that makes the room go quiet.", mode)]
    }
