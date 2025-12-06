from ._tone_rules import render_note
def evaluate_motifs(text: str, mode: str) -> dict:
    motifs = []
    if any(w in text.lower() for w in ["water","river","ocean","sea"]): motifs.append("water")
    if any(w in text.lower() for w in ["fire","burn","flame"]): motifs.append("fire")
    if any(w in text.lower() for w in ["light","shadow","night","sun"]): motifs.append("light_dark")
    return {
        "observations": [render_note(f"Recurring motifs: {', '.join(motifs) if motifs else 'subtle'}", mode)],
        "nudges": [render_note("Echo a motif once more in the bridge or final line for cohesion.", mode)]
    }