import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.db_models import (
    TeamMember,
    JiraEvent,
    JiraIssue,
    JiraUser,
    InterventionQueue,
)

# Reproducible demo runs
random.seed(42)

# REAL Jira accountIds captured from webhook logs
REAL_ACCOUNT_ID_MAP = {
    "Eoin": "712020:19483e09-930f-401c-8457-b947af5fc5df",
    "Joe Bloggs": "712020:0fec41a7-bd2a-419b-b0a6-41e158307429",
    "Maria": "557058:7df0b10c-cdfb-4ac1-9a78-262c417768ae",
    "Jane": "5db844bf1712930d3a9e7116",
    "Grayson Reid": "600f0f733b1af0006981af5f",
}

# Personas tuned for realistic Jira behaviour
PERSONAS = {
    "healthy": {
        "event_volume": (10, 20),
        "comment_prob": 0.30,
        "transition_prob": 0.40,
        "assignment_prob": 0.20,
        "blocker_prob": 0.05,
        "silence_prob": 0.05,
    },
    "silent": {
        "event_volume": (2, 6),
        "comment_prob": 0.05,
        "transition_prob": 0.10,
        "assignment_prob": 0.05,
        "blocker_prob": 0.02,
        "silence_prob": 0.60,
    },
    "blocked": {
        "event_volume": (12, 25),
        "comment_prob": 0.20,
        "transition_prob": 0.60,
        "assignment_prob": 0.10,
        "blocker_prob": 0.40,
        "silence_prob": 0.10,
    },
}

STATUS_OPTIONS = ["To Do", "In Progress", "Review", "Done", "Blocked"]

HELP_COMMENTS = [
    "I'm blocked on this.",
    "Need help here.",
    "Stuck waiting for dependency.",
    "Can't proceed until this is resolved.",
]

NORMAL_COMMENTS = [
    "Pushing this forward.",
    "Added clarification.",
    "Updated acceptance criteria.",
    "Investigating root cause.",
]


def generate_realistic_jira_event(persona, issue_key):
    roll = random.random()

    # 1. Silence event (no activity for days)
    if roll < persona["silence_prob"]:
        return "jira:issue_updated", {
            "fields": {},
            "changelog": {"items": []},
            "comment": None,
            "labels": [],
            "issue_key": issue_key,
            "silent": True,
        }

    # 2. Blocker event
    if roll < persona["silence_prob"] + persona["blocker_prob"]:
        return "jira:issue_updated", {
            "fields": {
                "status": {"name": "Blocked"},
                "labels": ["blocker"],
                "comment": {
                    "total": 1,
                    "comments": [{"body": random.choice(HELP_COMMENTS)}],
                },
            },
            "changelog": {
                "items": [
                    {"field": "status", "from": "In Progress", "to": "Blocked"},
                    {"field": "labels", "from": None, "to": "blocker"},
                ]
            },
            "issue_key": issue_key,
        }

    # 3. Status transition
    if roll < persona["silence_prob"] + persona["blocker_prob"] + persona["transition_prob"]:
        from_status = random.choice(STATUS_OPTIONS)
        to_status = random.choice([s for s in STATUS_OPTIONS if s != from_status])
        return "jira:issue_updated", {
            "fields": {
                "status": {"name": to_status},
                "labels": [],
                "comment": None,
            },
            "changelog": {
                "items": [
                    {"field": "status", "from": from_status, "to": to_status}
                ]
            },
            "issue_key": issue_key,
        }

    # 4. Assignment change
    if roll < (
        persona["silence_prob"]
        + persona["blocker_prob"]
        + persona["transition_prob"]
        + persona["assignment_prob"]
    ):
        return "jira:issue_updated", {
            "fields": {
                "assignee": {"accountId": "User"},
                "labels": [],
                "comment": None,
            },
            "changelog": {
                "items": [
                    {"field": "assignee", "from": None, "to": "User"}
                ]
            },
            "issue_key": issue_key,
        }

    # 5. Normal comment
    return "jira:issue_updated", {
        "fields": {
            "comment": {
                "total": 1,
                "comments": [{"body": random.choice(NORMAL_COMMENTS)}],
            },
            "labels": [],
        },
        "changelog": {"items": [{"field": "comment"}]},
        "issue_key": issue_key,
    }


def generate_synthetic_sprint(db: Session, days: int = 10):
    """
    Synthetic sprint generator producing REALISTIC Jira events.
    Fully compatible with jira_to_stats and your real webhook.
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

            account_id = REAL_ACCOUNT_ID_MAP[name]

            jira_user = JiraUser(
                id=str(uuid.uuid4()),
                account_id=account_id,
                display_name=name,
                team_member_id=tm.id,
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
    # Create synthetic issues (IDEMPOTENT)
    # -----------------------------------------------------
    synthetic_issues = []
    for i in range(5):
        issue_key = f"SAAM-SYNTH-{i+1}"

        # ⭐ IDEMPOTENCE FIX — skip if issue already exists
        existing = (
            db.query(JiraIssue)
            .filter(JiraIssue.issue_key == issue_key)
            .first()
        )
        if existing:
            print(f"[IDEMPOTENT] Skipping existing synthetic issue: {issue_key}")
            synthetic_issues.append(existing)
            continue

        issue = JiraIssue(
            id=str(uuid.uuid4()),
            issue_key=issue_key,
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
    # Generate realistic Jira events
    # -----------------------------------------------------
    start_date = datetime.utcnow() - timedelta(days=days)

    for member in members:
        persona = PERSONAS[persona_map[member.id]]
        min_events, max_events = persona["event_volume"]
        member_event_count = random.randint(min_events, max_events)

        account_id = REAL_ACCOUNT_ID_MAP.get(member.display_name)

        for _ in range(member_event_count):

            timestamp = start_date + timedelta(
                days=random.randint(0, days - 1),
                seconds=random.randint(0, 86400),
            )

            issue = random.choice(synthetic_issues)
            event_type, raw_payload = generate_realistic_jira_event(
                persona, issue.issue_key
            )

            jira_event = JiraEvent(
                id=str(uuid.uuid4()),
                issue_id=issue.id,
                event_type=event_type,
                raw_payload=raw_payload,
                triggered_by_id=account_id,
                timestamp=timestamp,
            )
            db.add(jira_event)

    db.commit()

    # -----------------------------------------------------
    # Seed InterventionQueue with persona-based messages
    # -----------------------------------------------------
    for member in members:
        persona_key = persona_map[member.id]

        if persona_key == "healthy":
            risk_label = "healthy"
            intervention_text = "Great engagement and steady progress."
        elif persona_key == "silent":
            risk_label = "silent"
            intervention_text = "Not much activity recently — consider sharing updates."
        else:
            risk_label = "blocked"
            intervention_text = "Looks like you're stuck — let's unblock this together."

        cues = {"persona": persona_key}

        queue_entry = InterventionQueue(
            id=str(uuid.uuid4()),
            team_member_id=member.id,
            intervention_text=intervention_text,
            risk_label=risk_label,
            cues=cues,
            created_at=datetime.utcnow(),
        )
        db.add(queue_entry)

    db.commit()

    return {
        "status": "ok",
        "message": "Generated realistic Jira-style synthetic sprint.",
    }
