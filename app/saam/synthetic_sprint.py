import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.db_models import (
    TeamMember,
    TeamMemberInteraction,
    JiraEvent,
    JiraIssue,
    JiraUser,
)

# Reproducible demo runs
random.seed(42)

# REAL Jira accountIds captured from webhook logs
REAL_ACCOUNT_ID_MAP = {
    "Eoin": "712020:19483e09-930f-401c-8457-b947af5fc5df",
    "Joe Bloggs": "712020:0fec41a7-bd2a-419b-b0a6-41e158307429",
    "Maria": "557058:7df0b10c-cdfb-4ac1-9a78-262c417768ae",
    "Jane": "5db844bf1712930d3a9e7116",
    "Grayson Reid": "600f0f733b1af0006981af5f"
}

# Behavioural personas with volume + severity variation
PERSONAS = {
    "healthy": {
        "comment_prob": 0.35,
        "transition_prob": 0.35,
        "assignment_prob": 0.20,
        "field_edit_prob": 0.10,
        "blocked_transition_prob": 0.05,
        "event_volume": (20, 40),
        "blocked_weight": 1.0
    },
    "silent": {
        "comment_prob": 0.01,
        "transition_prob": 0.05,
        "assignment_prob": 0.01,
        "field_edit_prob": 0.93,
        "blocked_transition_prob": 0.01,
        "event_volume": (2, 6),
        "blocked_weight": 1.0
    },
    "blocked": {
        "comment_prob": 0.02,
        "transition_prob": 0.80,
        "assignment_prob": 0.03,
        "field_edit_prob": 0.15,
        "blocked_transition_prob": 0.50,
        "event_volume": (15, 30),
        "blocked_weight": 3.0
    }
}

STATUS_OPTIONS = ["To Do", "In Progress", "Review", "Done", "Blocked"]
COMMENT_SNIPPETS = [
    "Pushing this forward.",
    "Added clarification to the description.",
    "Waiting on feedback.",
    "Updated acceptance criteria.",
    "Resolved merge conflict.",
    "Investigating root cause."
]


def generate_synthetic_sprint(db: Session, days: int = 10):
    """
    Populate the SAAM DB with persona‑driven synthetic Jira-like interactions.
    """

    # -----------------------------------------------------
    # Ensure team members exist + attach REAL Jira identities
    # -----------------------------------------------------
    members = db.query(TeamMember).all()
    if not members:
        demo_names = ["Eoin", "Joe Bloggs", "Maria", "Jane", "Grayson Reid"]

        for name in demo_names:
            tm = TeamMember(display_name=name)
            db.add(tm)
            db.flush()

            # Attach real Jira identity
            account_id = REAL_ACCOUNT_ID_MAP[name]

            jira_user = JiraUser(
                id=str(uuid.uuid4()),
                account_id=account_id,
                display_name=name,
                team_member_id=tm.id
            )
            db.add(jira_user)


        db.commit()
        members = db.query(TeamMember).all()

    # -----------------------------------------------------
    # Assign personas
    # -----------------------------------------------------
    persona_map = {}
    persona_choices = ["healthy", "silent", "blocked"]
    for member in members:
        persona_map[member.id] = random.choice(persona_choices)

    # -----------------------------------------------------
    # Create synthetic issues
    # -----------------------------------------------------
    synthetic_issues = []
    for i in range(3):
        issue = JiraIssue(
            id=str(uuid.uuid4()),
            issue_key=f"SAAM-SYNTH-{i+1}",
            summary=f"Synthetic Sprint Issue {i+1}",
            status="In Progress",
            issue_type="Task",
            priority="Medium",
            reporter_id=None,
            assignee_id=None,
        )
        db.add(issue)
        synthetic_issues.append(issue)
    db.flush()

    # -----------------------------------------------------
    # Generate persona-driven interactions
    # -----------------------------------------------------
    start_date = datetime.utcnow() - timedelta(days=days)

    for member in members:
        persona = PERSONAS[persona_map[member.id]]
        min_events, max_events = persona["event_volume"]
        member_event_count = random.randint(min_events, max_events)

        # Real Jira accountId for this synthetic member
        real_account_id = REAL_ACCOUNT_ID_MAP.get(member.display_name)

        for _ in range(member_event_count):

            timestamp = start_date + timedelta(
                days=random.randint(0, days - 1),
                seconds=random.randint(0, 86400)
            )

            signal_type, metadata = generate_persona_signal(persona)

            issue = random.choice(synthetic_issues)

            # Synthetic JiraEvent with REAL Jira accountId
            jira_event = JiraEvent(
                id=str(uuid.uuid4()),
                issue_id=issue.id,
                event_type=signal_type,
                raw_payload={"synthetic": True, "signal_type": signal_type},
                triggered_by_id=real_account_id,  # <-- FIXED
                timestamp=timestamp
            )
            db.add(jira_event)
            db.flush()

            interaction = TeamMemberInteraction(
                team_member_id=member.id,
                jira_event_id=jira_event.id,
                signal_type=signal_type,
                weight=metadata.get("weight", 1.0),
                event_metadata=metadata,
                timestamp=timestamp
            )
            db.add(interaction)

    db.commit()

    return {
        "status": "ok",
        "message": "Generated persona‑driven synthetic sprint with real Jira identities"
    }


def generate_persona_signal(persona):
    roll = random.random()

    if roll < persona["comment_prob"]:
        return "comment_created", {
            "weight": 1.0,
            "body": random.choice(COMMENT_SNIPPETS)
        }

    if roll < persona["comment_prob"] + persona["transition_prob"]:
        from_status = random.choice(STATUS_OPTIONS)
        to_status = random.choice([s for s in STATUS_OPTIONS if s != from_status])

        if random.random() < persona["blocked_transition_prob"]:
            to_status = "Blocked"

        weight = persona["blocked_weight"] if to_status == "Blocked" else 1.0

        return "status_transition", {
            "weight": weight,
            "from": from_status,
            "to": to_status
        }

    if roll < persona["comment_prob"] + persona["transition_prob"] + persona["assignment_prob"]:
        return "assignment_changed", {
            "weight": 1.2,
            "from": None,
            "to": "User"
        }

    return "field_edited", {
        "weight": 0.5,
        "field": "Rank",
        "from": "Medium",
        "to": "High"
    }
