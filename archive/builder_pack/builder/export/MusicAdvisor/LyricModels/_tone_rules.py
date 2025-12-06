TONE_RULES = {
    "poetic": {
        "style": "warm-minimal, imagery-forward, space-respecting",
        "sentence_len": "short to medium",
        "devices": ["metaphor-soft", "sensory-hint", "ellipses-rare"]
    },
    "direct": {
        "style": "studio-notes, specific, respectful",
        "sentence_len": "short",
        "devices": ["imperative-soft", "actionable-verb", "no-ornament"]
    },
    "hybrid": {
        "style": "poetic-direct balance; emotional + precise",
        "sentence_len": "short/medium mix",
        "devices": ["immediate-image", "gentle-why", "single next step"]
    }
}

def render_note(text: str, mode: str) -> str:
    # Minimal renderer; final language still comes from GPT,
    # this anchors tone for consistency across modules.
    if mode not in TONE_RULES: mode = "hybrid"
    return text
