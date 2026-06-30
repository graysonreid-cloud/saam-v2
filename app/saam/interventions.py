# app/saam/interventions.py
from app.saam.templates import select_template

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
        "type": "escalate",
        "action": "escalate_blocker",
        "message": (
            "I see a blocker that has been open for a while. "
            "Let’s address it together or escalate if needed."
        ),
    },
}


# ---------------------------------------------------------
# Coaching messages (risk-aware)
# ---------------------------------------------------------

COACHING_MESSAGES = {
    0: "Everything looks steady. Keep supporting collaboration and maintaining momentum.",
    1: "Some signals suggest emerging risk. A quick check‑in could prevent escalation.",
    2: "Multiple indicators show elevated risk. Immediate attention or escalation may be required."
}


# ---------------------------------------------------------
# Role-aware guidance
# ---------------------------------------------------------

ROLE_MESSAGES = {
    "developer": "Focus on unblocking technical tasks and clarifying implementation details.",
    "qa": "Consider reviewing test coverage or verifying recent changes for stability.",
    "product_owner": "It may help to clarify priorities or adjust scope to reduce pressure.",
    "scrum_master": "A facilitation touchpoint could help restore flow and reduce friction.",
    "designer": "Reviewing user flows or aligning on design intent may help reduce ambiguity.",
}


def format_role_message(role: str) -> str:
    if not role:
        return "No role-specific guidance available."
    role_key = role.lower().replace(" ", "_")
    return ROLE_MESSAGES.get(role_key, "No role-specific guidance available.")


# ---------------------------------------------------------
# Team grouping formatter
# ---------------------------------------------------------

def format_team_group(team_group: str) -> str:
    if not team_group:
        return "Unassigned"
    return team_group


# ---------------------------------------------------------
# Cue breakdown
# ---------------------------------------------------------

def format_cue_breakdown(cues: dict) -> str:
    meaningful = {}

    for key, value in cues.items():
        if value in (0, None, False):
            continue
        meaningful[key] = value

    if not meaningful:
        return "No significant behavioural cues detected."

    parts = [f"{k}: {v}" for k, v in meaningful.items()]
    return " | ".join(parts)


# ---------------------------------------------------------
# Sentiment score (simple aggregation)
# ---------------------------------------------------------

def compute_sentiment_score(cues: dict) -> float:
    """
    Compute a simple sentiment/pressure score from cues.
    Uses weighted signals if present, otherwise risk_score.
    """
    score = 0.0

    # Use risk_score as baseline
    risk = cues.get("risk_score", 0)
    score += risk * 0.6

    # Add blocker pressure
    if cues.get("blocker_age"):
        score += min(cues["blocker_age"] / 10, 1.0) * 0.3

    # Add activity signals
    if cues.get("recent_activity_drop"):
        score += 0.2

    # NEW: argumentative tone increases pressure
    if cues.get("argumentative_comment"):
        score += 0.15

    # NEW: mood variability increases pressure
    if cues.get("engagement_variability"):
        score += 0.10

    # Clamp between 0 and 1
    return round(min(score, 1.0), 3)


# ---------------------------------------------------------
# Persona-aware messaging (NEW)
# ---------------------------------------------------------

PERSONA_MESSAGES = {
    "Eoin": "Your throughput is strong — keep maintaining clarity across transitions.",
    "Joe Bloggs": "If anything feels unclear or overwhelming, a quick sync could help.",
    "Maria": (
        "Your attention to detail is valuable. "
        "Let’s channel that into constructive alignment with the team."
    ),
    "Jane": (
        "If you're stuck or unsure, sharing even a small update can help unblock progress."
    ),
    "Grayson Reid": (
        "Your engagement varies — if today feels like a low‑energy day, "
        "a brief check‑in might help regain momentum."
    ),
}


def persona_specific_message(cues: dict) -> str:
    persona = cues.get("user")
    return PERSONA_MESSAGES.get(persona, "")


# ---------------------------------------------------------
# Main intervention selector (UPDATED)
# ---------------------------------------------------------

def select_intervention(label: str, cues: dict) -> dict:
    """
    Risk-aware + role-aware + cue-aware + sentiment-aware + persona-aware + team-aware intervention selection.
    """

    risk = cues.get("risk_score", 0)
    sprint_progress = cues.get("sprint_progress")
    role = cues.get("role")
    team_group = cues.get("team_group")

    cue_breakdown = format_cue_breakdown(cues)
    role_message = format_role_message(role)
    sentiment_score = compute_sentiment_score(cues)
    team_group_label = format_team_group(team_group)
    persona_message = select_template(cues.get("user"), label, cues)
    # ---------------------------------------------------------
    # 1. High-risk override
    # ---------------------------------------------------------
    if risk >= 0.7:
        return {
            "type": "escalate",
            "action": "highlight_risk",
            "message": (
                "This issue shows several risk indicators. It may need attention.\n\n"
                f"{persona_message}\n\n"
                f"Team: {team_group_label}\n\n"
                f"Coaching: {COACHING_MESSAGES[2]}\n\n"
                f"Role Guidance: {role_message}\n\n"
                f"Cues: {cue_breakdown}\n\n"
                f"Sentiment Score: {sentiment_score}"
            ),
        }

    # ---------------------------------------------------------
    # 2. Medium-risk
    # ---------------------------------------------------------
    if risk >= 0.4:
        return {
            "type": "soft",
            "action": "invite_contribution",
            "message": (
                "There are some signs of risk. Could you share an update when possible?\n\n"
                f"{persona_message}\n\n"
                f"Team: {team_group_label}\n\n"
                f"Coaching: {COACHING_MESSAGES[1]}\n\n"
                f"Role Guidance: {role_message}\n\n"
                f"Cues: {cue_breakdown}\n\n"
                f"Sentiment Score: {sentiment_score}"
            ),
        }

    # ---------------------------------------------------------
    # 3. Low-risk → matrix
    # ---------------------------------------------------------
    base = INTERVENTION_MATRIX.get(label, INTERVENTION_MATRIX["healthy"])

    prefix = ""
    if sprint_progress is not None:
        if sprint_progress < 0.3:
            prefix = "Early in the sprint, "
        elif sprint_progress > 0.8:
            prefix = "With the sprint nearly finished, "

    message = (
        prefix + base["message"] +
        "\n\n" +
        f"{persona_message}\n\n"
        f"Team: {team_group_label}\n\n"
        f"Coaching: {COACHING_MESSAGES[0]}\n\n"
        f"Role Guidance: {role_message}\n\n"
        f"Cues: {cue_breakdown}\n\n"
        f"Sentiment Score: {sentiment_score}"
    )

    return {
        "type": base["type"],
        "action": base["action"],
        "message": message,
    }
