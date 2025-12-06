from ._tone_rules import render_note
def evaluate_listener_projection(text: str, mode: str) -> dict:
    you_ct = text.lower().count("you")
    me_ct = text.lower().count("me")
    balance = "balanced" if abs(you_ct-me_ct) <= 2 else ("you_facing" if you_ct>me_ct else "self_facing")
    return {
        "observations": [render_note(f"Address is {balance}. Consider one line that invites the listener in.", mode)],
        "nudges": [render_note("Offer a universal image the listener can step into.", mode)]
    }
