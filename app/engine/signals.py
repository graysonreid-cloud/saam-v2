from datetime import datetime, timezone

def extract_signals_from_event(event_type: str, payload: dict) -> list:
    """
    Extract behavioural signals from a Jira webhook event.
    MVP version: lightweight but produces real, useful signals.
    """

    signals = []
    now = datetime.now(timezone.utc)

    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    comment = payload.get("comment", {})
    changelog = payload.get("changelog", {})
    items = changelog.get("items", [])

    # -----------------------------------------------------
    # 1. Comment signals
    # -----------------------------------------------------
    if comment:
        body = comment.get("body", "") or ""
        body_lower = body.lower()

        # Basic comment event
        signals.append({
            "type": "comment",
            "weight": 1.0,
            "metadata": {
                "length": len(body),
                "timestamp": now.isoformat()
            }
        })

        # Help-seeking patterns
        if any(x in body_lower for x in ["stuck", "blocked", "help", "anyone", "can someone"]):
            signals.append({
                "type": "help_request",
                "weight": 1.0,
                "metadata": {"text": body}
            })

        # Help-offering patterns
        if any(x in body_lower for x in ["i can take", "i'll take", "i can help", "let me help"]):
            signals.append({
                "type": "help_offer",
                "weight": 1.0,
                "metadata": {"text": body}
            })

    # -----------------------------------------------------
    # 2. Status change signals
    # -----------------------------------------------------
    for item in items:
        if item.get("field") == "status":
            signals.append({
                "type": "status_change",
                "weight": 1.0,
                "metadata": {
                    "from": item.get("fromString"),
                    "to": item.get("toString")
                }
            })

    # -----------------------------------------------------
    # 3. Assignee change signals
    # -----------------------------------------------------
    for item in items:
        if item.get("field") == "assignee":
            signals.append({
                "type": "assignee_change",
                "weight": 1.0,
                "metadata": {
                    "from": item.get("fromString"),
                    "to": item.get("toString")
                }
            })

    # -----------------------------------------------------
    # 4. Worklog signals
    # -----------------------------------------------------
    if event_type == "worklog_updated":
        signals.append({
            "type": "worklog_update",
            "weight": 0.5,
            "metadata": {}
        })

    # -----------------------------------------------------
    # 5. Blocker signals (Flagged field)
    # -----------------------------------------------------
    flagged = fields.get("customfield_10021")
    if flagged:
        signals.append({
            "type": "blocker_flagged",
            "weight": 1.0,
            "metadata": {"flagged": True}
        })

    # -----------------------------------------------------
    # 6. Issue created / updated timestamps
    # -----------------------------------------------------
    created = fields.get("created")
    if created:
        signals.append({
            "type": "issue_created",
            "weight": 0.2,
            "metadata": {"created": created}
        })

    updated = fields.get("updated")
    if updated:
        signals.append({
            "type": "issue_updated",
            "weight": 0.1,
            "metadata": {"updated": updated}
        })

    return signals
