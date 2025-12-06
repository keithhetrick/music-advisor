from ._tone_rules import render_note
def evaluate_emotional_arc(text: str, mode: str) -> dict:
    has_verse = "\n" in text
    return {
        "observations": [
            render_note("Map tension → reveal → release. Let the quiet make the lift feel earned.", mode)
        ],
        "nudges": [
            render_note("If verse 2 repeats verse 1, evolve the image or raise the stakes.", mode) if has_verse else
            render_note("Introduce a second-angle image before the final lift.", mode)
        ]
    }