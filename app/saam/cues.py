# app/saam/cues.py

from app.engine.risk import compute_risk_score


def extract_cues(raw: dict) -> dict:
    """
    Convert raw behavioural stats + sprint context into SAAM cue values.
    """

    # -----------------------------------------------------
    # Base behavioural cues
    # -----------------------------------------------------
    participation_level = raw.get("participation_level", 0)
    talktime_imbalance = raw.get("talktime_imbalance", 0)
    blocker_age = raw.get("blocker_age", 0)

    missing_updates = 1 if raw.get("missing_updates", False) else 0
    blocker_owner_missing = 1 if raw.get("blocker_owner_missing", False) else 0

    time_remaining = raw.get("time_remaining", 0)
    goal_changes = raw.get("goal_changes", 0)

    ceremony_map = {
        "standup": 0,
        "planning": 1,
        "retro": 2,
        "refinement": 3,
    }
    ceremony_type_encoded = ceremony_map.get(
        raw.get("ceremony_type", "standup"), 0
    )

    sentiment_score = raw.get("sentiment_score", 0)
    workload_ratio = raw.get("workload_ratio", 1)
    help_requests = raw.get("help_requests", 0)
    help_offers = raw.get("help_offers", 0)

    cues = {
        "participation_level": participation_level,
        "talktime_imbalance": talktime_imbalance,
        "blocker_age": blocker_age,
        "missing_updates": missing_updates,
        "blocker_owner_missing": blocker_owner_missing,
        "time_remaining": time_remaining,
        "goal_changes": goal_changes,
        "ceremony_type_encoded": ceremony_type_encoded,
        "sentiment_score": sentiment_score,
        "workload_ratio": workload_ratio,
        "help_requests": help_requests,
        "help_offers": help_offers,
    }

    # -----------------------------------------------------
    # Sprint context cues
    # -----------------------------------------------------
    sprint = raw.get("sprint_context", {}) or {}

    cues["days_remaining"] = sprint.get("days_remaining")
    cues["sprint_progress"] = sprint.get("sprint_progress")
    cues["issue_age_days"] = sprint.get("issue_age_days")
    cues["time_in_status_days"] = sprint.get("time_in_status_days")

    # -----------------------------------------------------
    # Compute risk score (final cue)
    # -----------------------------------------------------
    cues["risk_score"] = compute_risk_score(cues)

    return cues
