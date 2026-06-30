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

# Personas tuned for realistic Jira behaviour (REAL USERS)
PERSONAS = {
    # 1. Eoin — Senior Developer, High Throughput, Low Chatter
    "Eoin": {
        "event_volume": (45, 70),
        "comment_prob": 0.10,
        "transition_prob": 0.75,
        "assignment_prob": 0.20,
        "blocker_prob": 0.05,
        "silence_prob": 0.05,
    },

    # 2. Joe Bloggs — Mid-Level Dev, Steady but Sometimes Overwhelmed
    "Joe Bloggs": {
        "event_volume": (25, 40),
        "comment_prob": 0.35,
        "transition_prob": 0.40,
        "assignment_prob": 0.15,
        "blocker_prob": 0.10,
        "silence_prob": 0.20,
    },

    # 3. Maria — Senior QA, Hyper-Confident, Argument-Prone
    "Maria": {
        "event_volume": (35, 55),
        "comment_prob": 0.75,
        "transition_prob": 0.30,
        "assignment_prob": 0.10,
        "blocker_prob": 0.15,
        "silence_prob": 0.10,
        "argument_comment_prob": 0.40,
    },

    # 4. Jane — Junior Dev, Quiet, Frequently Needs Help
    "Jane": {
        "event_volume": (10, 18),
        "comment_prob": 0.25,
        "transition_prob": 0.20,
        "assignment_prob": 0.05,
        "blocker_prob": 0.20,
        "silence_prob": 0.35,
    },

    # 5. Grayson Reid — Developer with Mood-Driven Engagement
    "Grayson Reid": {
        "event_volume": (20, 45),
        "comment_prob": 0.35,  # baseline, overridden by mood
        "transition_prob": 0.30,
        "assignment_prob": 0.10,
        "blocker_prob": 0.15,
        "silence_prob": 0.20,
        "mood_cycle_days": (2, 4),
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
    # Assign personas (REAL USERS → REAL PERSONAS)
    # -----------------------------------------------------
    persona_map = {}
    for member in members:
        persona_map[member.id] = member.display_name

    # -----------------------------------------------------
    # Create synthetic issues (IDEMPOTENT)
    # -----------------------------------------------------
    synthetic_issues = []
    for i in range(5):
        issue_key = f"SAAM-SYNTH-{i+1}"

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

        # --- Mood-driven behaviour (Grayson) ---
        if persona_map[member.id] == "Grayson Reid":
            cycle = random.randint(*persona["mood_cycle_days"])
            mood_roll = random.random()

            if mood_roll < 0.35:   # high-energy
                persona["comment_prob"] = 0.60
                persona["silence_prob"] = 0.05
                persona["blocker_prob"] = 0.05
            elif mood_roll < 0.75: # neutral
                persona["comment_prob"] = 0.35
                persona["silence_prob"] = 0.20
                persona["blocker_prob"] = 0.15
            else:                  # low-energy
                persona["comment_prob"] = 0.15
                persona["silence_prob"] = 0.35
                persona["blocker_prob"] = 0.25

        # --- Argumentative QA (Maria) ---
        if persona_map[member.id] == "Maria":
            if random.random() < persona["argument_comment_prob"]:
                NORMAL_COMMENTS.append(
                    random.choice([
                        "This implementation is incorrect.",
                        "We need to fix this properly.",
                        "This does not meet the test requirements.",
                        "I strongly disagree with this approach.",
                    ])
                )

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
    # Seed InterventionQueue with GENERIC persona-based messages
    # -----------------------------------------------------
    for member in members:
        persona_key = persona_map[member.id]

        # Map real personas → generic risk labels
        if persona_key == "Eoin":
            risk_label = "healthy"
            intervention_text = "Great engagement and steady progress."
        elif persona_key == "Joe Bloggs":
            risk_label = "silent"
            intervention_text = "Not much activity recently — consider sharing updates."
        elif persona_key == "Maria":
            risk_label = "blocked"
            intervention_text = "Looks like you're stuck — let's unblock this together."
        elif persona_key == "Jane":
            risk_label = "blocked"
            intervention_text = "Looks like you're stuck — let's unblock this together."
        else:  # Grayson Reid
            risk_label = "silent"
            intervention_text = "Not much activity recently — consider sharing updates."

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
