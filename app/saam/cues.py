# app/saam/cues.py

from datetime import datetime, timedelta
from app.engine.risk import compute_risk_score


def extract_cues(raw: dict) -> dict:
    """
    Convert raw behavioural stats + sprint context into SAAM cue values.
    """

    # -----------------------------------------------------
    # Base behavioural cues (existing)
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
    # Sprint context cues (existing)
    # -----------------------------------------------------
    sprint = raw.get("sprint_context", {}) or {}

    cues["days_remaining"] = sprint.get("days_remaining")
    cues["sprint_progress"] = sprint.get("sprint_progress")
    cues["issue_age_days"] = sprint.get("issue_age_days")
    cues["time_in_status_days"] = sprint.get("time_in_status_days")

    # -----------------------------------------------------
    # NEW: Argumentative QA comment detection (Maria)
    # -----------------------------------------------------
    argumentative_keywords = [
        "incorrect",
        "disagree",
        "does not meet",
        "fix this properly",
        "not acceptable",
        "wrong approach",
    ]

    comment_body = ""
    if raw.get("raw_payload"):
        fields = raw["raw_payload"].get("fields", {})
        comment_data = fields.get("comment", {})
        if comment_data and comment_data.get("comments"):
            comment_body = comment_data["comments"][-1].get("body", "").lower()

    cues["argumentative_comment"] = any(
        kw in comment_body for kw in argumentative_keywords
    )

    # -----------------------------------------------------
    # NEW: Engagement variability (Grayson mood swings)
    # -----------------------------------------------------
    recent_events = raw.get("recent_events", [])

    if recent_events:
        cutoff = datetime.utcnow() - timedelta(hours=48)

        recent_count = sum(
            1 for ev in recent_events
            if ev.get("timestamp")
            and datetime.fromisoformat(ev["timestamp"]) > cutoff
        )

        # High variability if unusually high or low activity
        cues["engagement_variability"] = (
            recent_count < 2 or recent_count > 10
        )
    else:
        cues["engagement_variability"] = False

    # -----------------------------------------------------
    # Compute risk score (existing)
    # -----------------------------------------------------
    cues["risk_score"] = compute_risk_score(cues)

    return cues
