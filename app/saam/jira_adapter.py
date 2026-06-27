from datetime import datetime, timezone


def jira_to_stats(events: list[dict]) -> dict:
    """
    Convert raw Jira events into behavioural stats.
    MVP version with time-based behavioural metrics.
    """

    now = datetime.now(timezone.utc)

    stats = {
        "event_count": len(events),
        "comment_count": 0,
        "total_comment_length": 0,
        "avg_comment_length": 0,
        "last_event_ts": None,
        "last_comment_ts": None,
        "last_status_change_ts": None,
        "last_assignment_ts": None,
        "help_requests": 0,
        "help_offers": 0,
        "issues_assigned": 0,
        "team_issues": 0,
        "workload_ratio": 0,
        "missing_updates": False,
        "participation_level": 0.0,
        "talktime_imbalance": 0.0,
        "blocker_age": 0,
        "goal_changes": 0,
        "time_since_last_event_days": None,
        "time_since_last_comment_days": None,
        "time_since_last_status_change_days": None,
        "time_since_last_assignment_days": None,
    }

    # -----------------------------------------------------
    # 1. Process events
    # -----------------------------------------------------
    for ev in events:
        ts_raw = ev.get("timestamp")
        ts = None

        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except ValueError:
                ts = None

        # Track last event timestamp
        if ts and (stats["last_event_ts"] is None or ts > stats["last_event_ts"]):
            stats["last_event_ts"] = ts

        # -------------------------------------------------
        # Comment events
        # -------------------------------------------------
        comment = ev.get("raw_payload", {}).get("comment")
        if comment:
            body = comment.get("body") or ""
            stats["comment_count"] += 1
            stats["total_comment_length"] += len(body)

            if ts:
                stats["last_comment_ts"] = ts

            text = body.lower()

            # Help-seeking
            if any(x in text for x in ["stuck", "blocked", "help", "anyone", "can someone"]):
                stats["help_requests"] += 1

            # Help-offering
            if any(x in text for x in ["i can take", "i'll take", "i can help", "let me help"]):
                stats["help_offers"] += 1

        # -------------------------------------------------
        # Status change
        # -------------------------------------------------
        if ev.get("signal_type") == "status_change" and ts:
            stats["last_status_change_ts"] = ts

        # -------------------------------------------------
        # Assignment change
        # -------------------------------------------------
        if ev.get("signal_type") == "assignee_change" and ts:
            stats["last_assignment_ts"] = ts

    # -----------------------------------------------------
    # 2. Averages
    # -----------------------------------------------------
    if stats["comment_count"] > 0:
        stats["avg_comment_length"] = (
            stats["total_comment_length"] / stats["comment_count"]
        )

    # -----------------------------------------------------
    # 3. Time-based metrics
    # -----------------------------------------------------
    def days_since(dt):
        if not dt:
            return None
        return max((now - dt).days, 0)

    stats["time_since_last_event_days"] = days_since(stats["last_event_ts"])
    stats["time_since_last_comment_days"] = days_since(stats["last_comment_ts"])
    stats["time_since_last_status_change_days"] = days_since(stats["last_status_change_ts"])
    stats["time_since_last_assignment_days"] = days_since(stats["last_assignment_ts"])

    # -----------------------------------------------------
    # 4. Missing updates
    # -----------------------------------------------------
    if stats["time_since_last_event_days"] is not None:
        stats["missing_updates"] = stats["time_since_last_event_days"] >= 3

    # -----------------------------------------------------
    # 5. Participation level
    # -----------------------------------------------------
    if stats["time_since_last_event_days"] is not None:
        recency_factor = max(1 - (stats["time_since_last_event_days"] / 14), 0)
    else:
        recency_factor = 0

    stats["participation_level"] = min(
        (stats["event_count"] / 10) * recency_factor,
        1.0
    )

    # -----------------------------------------------------
    # 6. Talktime imbalance
    # -----------------------------------------------------
    if stats["avg_comment_length"] > 0:
        stats["talktime_imbalance"] = min(stats["avg_comment_length"] / 300, 1.0)

    # -----------------------------------------------------
    # 7. Workload ratio
    # -----------------------------------------------------
    assigned = [
        ev for ev in events
        if ev.get("raw_payload", {}).get("issue", {}).get("fields", {}).get("assignee")
    ]
    stats["issues_assigned"] = len(assigned)
    stats["team_issues"] = len({ev.get("issue_id") for ev in events})

    if stats["team_issues"] > 0:
        team_avg = stats["team_issues"] / 5  # MVP assumption
        stats["workload_ratio"] = stats["issues_assigned"] / max(team_avg, 1)

    return stats
