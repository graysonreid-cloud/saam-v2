# app/saam/templates.py
"""
Persona-aware, cue-aware, and mood-aware templates for SAAM interventions.
These templates are used by select_intervention() to enrich messages with
persona-specific tone, nudges, and contextual guidance.
"""

# ---------------------------------------------------------
# Persona-specific phrasing (NEW)
# ---------------------------------------------------------

PERSONA_TEMPLATES = {
    "Eoin": {
        "healthy": (
            "Your throughput continues to be strong and consistent. "
            "Maintaining clarity across transitions helps the team stay aligned."
        ),
        "silent": (
            "Even with your usual strong throughput, a quick update here could help "
            "others stay in sync with your progress."
        ),
        "blocked": (
            "If something is slowing you down, surfacing it early helps prevent "
            "bottlenecks for the rest of the team."
        ),
    },

    "Joe Bloggs": {
        "healthy": (
            "Your steady progress is valuable. Keeping communication flowing helps "
            "avoid mid-sprint overwhelm."
        ),
        "silent": (
            "If anything feels unclear or heavy, sharing even a small update can help "
            "reduce pressure and avoid blockers."
        ),
        "blocked": (
            "If you're stuck, raising it now can help prevent further delays."
        ),
    },

    "Maria": {
        "healthy": (
            "Your attention to detail strengthens quality. Keeping feedback constructive "
            "helps maintain team flow."
        ),
        "silent": (
            "If you’ve spotted something important, sharing it early helps avoid late-sprint surprises."
        ),
        "blocked": (
            "Your testing insights are valuable — let's align on the blocker and move forward together."
        ),
        "argumentative": (
            "Your quality concerns are valid. Let’s channel them into constructive alignment "
            "so the team can move forward smoothly."
        ),
    },

    "Jane": {
        "healthy": (
            "Your progress is steady. Sharing small updates helps others stay aligned."
        ),
        "silent": (
            "If you're unsure or stuck, even a brief update can help unblock progress."
        ),
        "blocked": (
            "Let’s work together to unblock this — you don’t need to solve it alone."
        ),
    },

    "Grayson Reid": {
        "healthy": (
            "Your engagement is strong today — great momentum."
        ),
        "silent": (
            "If today feels like a low-energy day, a quick check-in could help regain momentum."
        ),
        "blocked": (
            "If something is blocking progress, surfacing it early helps restore flow."
        ),
        "mood_variability": (
            "Your engagement varies — if this is a dip, a short update can help keep things moving."
        ),
    },
}


# ---------------------------------------------------------
# Template selector (NEW)
# ---------------------------------------------------------

def select_template(persona: str, label: str, cues: dict) -> str:
    """
    Returns persona-aware template text based on:
    - persona name (Eoin, Joe, Maria, Jane, Grayson)
    - generic persona label (healthy/silent/blocked)
    - cues (argumentative_comment, engagement_variability)
    """

    persona_block = PERSONA_TEMPLATES.get(persona)
    if not persona_block:
        return ""

    # Argumentative tone → Maria-specific softening
    if persona == "Maria" and cues.get("argumentative_comment"):
        return persona_block.get("argumentative", "")

    # Mood variability → Grayson-specific nudges
    if persona == "Grayson Reid" and cues.get("engagement_variability"):
        return persona_block.get("mood_variability", "")

    # Generic persona label
    return persona_block.get(label, "")
