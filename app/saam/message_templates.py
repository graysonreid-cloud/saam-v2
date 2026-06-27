# app/saam/message_templates.py

def apply_sprint_context_prefix(message: str, cues: dict) -> str:
    """
    Add sprint‑aware phrasing to the start of the message.
    This enhances the message without replacing it.
    """

    days_remaining = cues.get("days_remaining")
    sprint_progress = cues.get("sprint_progress")

    prefix = ""

    # -----------------------------------------------------
    # End of sprint
    # -----------------------------------------------------
    if days_remaining is not None and days_remaining <= 2:
        prefix = f"With only {days_remaining} days left in the sprint, "

    # -----------------------------------------------------
    # Late sprint (only if not already end‑of‑sprint)
    # -----------------------------------------------------
    elif sprint_progress is not None and sprint_progress > 0.7:
        prefix = "As we approach the end of the sprint, "

    # -----------------------------------------------------
    # Early sprint
    # -----------------------------------------------------
    elif sprint_progress is not None and sprint_progress < 0.3:
        prefix = "Early in the sprint, "

    return prefix + message
