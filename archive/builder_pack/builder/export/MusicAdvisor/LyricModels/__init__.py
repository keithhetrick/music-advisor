from .authenticity import evaluate_authenticity
from .clarity import evaluate_clarity
from .resonance import evaluate_resonance
from .emotional_arc import evaluate_emotional_arc
from .motif_mapping import evaluate_motifs
from .listener_projection import evaluate_listener_projection

def run_lyric_ei(text: str, mode: str = "hybrid") -> dict:
    """
    Advisory-only Lyric Emotional Intelligence pass.
    mode: 'poetic' | 'direct' | 'hybrid'
    """
    return {
        "authenticity": evaluate_authenticity(text, mode),
        "clarity": evaluate_clarity(text, mode),
        "resonance": evaluate_resonance(text, mode),
        "emotional_arc": evaluate_emotional_arc(text, mode),
        "motifs": evaluate_motifs(text, mode),
        "listener_projection": evaluate_listener_projection(text, mode),
        "meta": {"mode": mode, "scoring": False}
    }