# app/saam/interventions.py

INTERVENTION_MATRIX = {
    "silent": {
        "type": "soft",
        "action": "invite_contribution",
        "message": (
            "I noticed you’ve been quieter than usual. "
            "Would you like to share any updates or blockers?"
        ),
    },

    "healthy": {
        "type": "none",
        "action": "reinforce_positive",
        "message": (
            "Great engagement and steady progress. "
            "Keep up the good collaboration."
        ),
    },

    "blocked": {
        "type": "escalate",   # corrected from "hard"
        "action": "escalate_blocker",
        "message": (
            "I see a blocker that has been open for a while. "
            "Let’s address it together or escalate if needed."
        ),
    },
}


def select_intervention(label: str, cues: dict) -> dict:
    """
    Risk-aware intervention selection.
    Uses:
      - model label
      - risk score
      - sprint context
    """

    risk = cues.get("risk_score", 0)
    sprint_progress = cues.get("sprint_progress")

    # ---------------------------------------------------------
    # 1. High-risk override (escalate)
    # ---------------------------------------------------------
    if risk >= 0.7:
        return {
            "type": "escalate",
            "action": "highlight_risk",
            "message": (
                "This issue shows several risk indicators. "
                "It may need attention."
            ),
        }

    # ---------------------------------------------------------
    # 2. Medium-risk → soft intervention
    # ---------------------------------------------------------
    if risk >= 0.4:
        return {
            "type": "soft",
            "action": "invite_contribution",
            "message": (
                "There are some signs of risk. "
                "Could you share an update when possible?"
            ),
        }

    # ---------------------------------------------------------
    # 3. Low-risk → use model label (matrix)
    # ---------------------------------------------------------
    base = INTERVENTION_MATRIX.get(label, INTERVENTION_MATRIX["healthy"])

    # ---------------------------------------------------------
    # 4. Sprint-aware prefixing
    # ---------------------------------------------------------
    prefix = ""

    if sprint_progress is not None:
        if sprint_progress < 0.3:
            prefix = "Early in the sprint, "
        elif sprint_progress > 0.8:
            prefix = "With the sprint nearly finished, "

    message = prefix + base["message"]

    return {
        "type": base["type"],
        "action": base["action"],
        "message": message,
    }
