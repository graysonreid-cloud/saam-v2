# app/saam/personas.py

import random


def silent_persona_reply(_: str) -> str:
    """
    Silent persona gives minimal, vague, or non‑committal replies.
    """
    options = [
        "Not much to add.",
        "All good here.",
        "No updates.",
        "Nothing from me.",
        "I'm fine.",
    ]
    return random.choice(options)


def healthy_persona_reply(_: str) -> str:
    """
    Healthy persona is positive, collaborative, and responsive.
    """
    options = [
        "Thanks for checking in — everything is on track.",
        "Great, I’ll keep the momentum going.",
        "All good, making steady progress.",
        "Appreciate the support!",
        "No blockers — moving forward nicely.",
    ]
    return random.choice(options)


def blocked_persona_reply(_: str) -> str:
    """
    Blocked persona expresses frustration, stress, or overwhelm.
    """
    options = [
        "I'm stuck and it's slowing everything down.",
        "Still blocked — waiting on someone to help.",
        "This is getting frustrating.",
        "I can't move forward until this is resolved.",
        "Honestly, it's been a rough sprint.",
    ]
    return random.choice(options)
