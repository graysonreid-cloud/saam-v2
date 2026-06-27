# app/engine/risk.py

def compute_risk_score(cues: dict) -> float:
    """
    Compute a sprint-aware behavioural risk score between 0.0 and 1.0.
    """

    # -----------------------------
    # Extract cues safely
    # -----------------------------
    participation = cues.get("participation_level", 0) or 0
    missing_updates = 1 if cues.get("missing_updates") else 0
    talktime = cues.get("talktime_imbalance", 0) or 0

    sprint_progress = cues.get("sprint_progress", 0) or 0
    issue_age = cues.get("issue_age_days", 0) or 0
    time_in_status = cues.get("time_in_status_days", 0) or 0

    workload_ratio = cues.get("workload_ratio", 0) or 0
    blocker_age = cues.get("blocker_age", 0) or 0

    time_since_event = cues.get("time_since_last_event_days", 0) or 0

    # -----------------------------
    # 1. Behavioural Risk
    # -----------------------------
    behavioural_risk = (
        (1 - participation) * 0.4 +
        missing_updates * 0.3 +
        talktime * 0.3
    )

    # -----------------------------
    # 2. Sprint Risk
    # -----------------------------
    sprint_risk = (
        (1 - sprint_progress) * 0.2 +
        min(issue_age / 30, 1.0) * 0.4 +
        min(time_in_status / 7, 1.0) * 0.4
    )

    # -----------------------------
    # 3. Workload Risk
    # -----------------------------
    workload_risk = min(workload_ratio / 2, 1.0)

    # -----------------------------
    # 4. Blocker Risk
    # -----------------------------
    blocker_risk = min(blocker_age / 7, 1.0)

    # -----------------------------
    # 5. Time Decay Risk
    # -----------------------------
    decay_risk = min(time_since_event / 7, 1.0)

    # -----------------------------
    # Weighted sum
    # -----------------------------
    risk = (
        0.25 * behavioural_risk +
        0.25 * sprint_risk +
        0.20 * workload_risk +
        0.20 * blocker_risk +
        0.10 * decay_risk
    )

    # Clamp to [0, 1]
    return max(0.0, min(risk, 1.0))
