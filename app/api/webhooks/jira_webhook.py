from fastapi import APIRouter, Request as FastAPIRequest
from sqlalchemy.orm import Session
import numpy as np
import uuid
from datetime import datetime, timezone

from db.database import SessionLocal
from db.db_models import (
    Request as SAAMRequest,
    JiraUser,
    JiraIssue,
    JiraEvent,
    TeamMember,
    TeamMemberInteraction,
    InterventionQueue,
    TrainingSample
)

from app.saam.cues import extract_cues
from app.saam.features import build_feature_vector
from app.saam.interventions import select_intervention
from app.saam.model_loader import load_model
from app.saam.jira_adapter import jira_to_stats


def sanitize(obj):
    import numpy as np
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj


def serialize_cues(cues):
    out = {}
    for k, v in cues.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


router = APIRouter()


@router.post("/jira")
async def jira_webhook(request: FastAPIRequest):
    db: Session = SessionLocal()

    try:
        payload = await request.json()
        event_type = payload.get("webhookEvent")
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})

        print("### PAYLOAD ###")
        print(payload)

        # -----------------------------------------------------
        # 1. Log raw request
        # -----------------------------------------------------
        req = SAAMRequest(
            id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            source="jira",
            payload=payload
        )
        db.add(req)
        db.commit()

        # -----------------------------------------------------
        # 2. Extract identity
        # -----------------------------------------------------
        actor = fields.get("assignee") or payload.get("user", {})
        account_id = actor.get("accountId")
        display_name = actor.get("displayName")
        email = actor.get("emailAddress")

        jira_user = db.query(JiraUser).filter_by(account_id=account_id).first()
        if not jira_user:
            jira_user = JiraUser(
                id=str(uuid.uuid4()),
                account_id=account_id,
                display_name=display_name,
                email=email
            )
            db.add(jira_user)
            db.commit()

        if jira_user.team_member_id:
            tm = db.query(TeamMember).filter_by(id=jira_user.team_member_id).first()
        else:
            tm = TeamMember(
                id=str(uuid.uuid4()),
                display_name=display_name,
                email=email
            )
            db.add(tm)
            db.commit()

            jira_user.team_member_id = tm.id
            db.commit()

        # -----------------------------------------------------
        # 3. Upsert JiraIssue
        # -----------------------------------------------------
        issue_key = issue.get("key")
        jira_issue = db.query(JiraIssue).filter_by(issue_key=issue_key).first()

        if not jira_issue:
            jira_issue = JiraIssue(
                id=str(uuid.uuid4()),
                issue_key=issue_key
            )
            db.add(jira_issue)

        jira_issue.summary = fields.get("summary")
        jira_issue.status = fields.get("status", {}).get("name")
        jira_issue.issue_type = fields.get("issuetype", {}).get("name")
        jira_issue.priority = fields.get("priority", {}).get("name")
        jira_issue.updated_at = datetime.now(timezone.utc)

        db.commit()

        # -----------------------------------------------------
        # 4. Create JiraEvent
        # -----------------------------------------------------
        jira_event = JiraEvent(
            id=str(uuid.uuid4()),
            issue_id=jira_issue.id,
            event_type=event_type,
            raw_payload=payload,
            triggered_by_id=jira_user.id,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(jira_event)
        db.commit()

        # -----------------------------------------------------
        # 5. Build event_dict
        # -----------------------------------------------------
        labels = fields.get("labels", []) or []
        is_blocker = "blocker" in labels

        comment_data = fields.get("comment", {})
        team_comment_count = comment_data.get("total", 0)

        event_dict = {
            "issue_key": issue_key,
            "event_type": event_type,
            "is_blocker": is_blocker,
            "assignee": fields.get("assignee", {}).get("accountId"),
            "user": display_name,
            "team_comment_count": team_comment_count,
        }

        # -----------------------------------------------------
        # 5a. Comment body → blocker detection
        # -----------------------------------------------------
        comment_body = ""
        if payload.get("comment") and payload["comment"].get("body"):
            comment_body = payload["comment"]["body"].lower()
        elif fields.get("comment") and fields["comment"].get("comments"):
            comment_body = fields["comment"]["comments"][-1].get("body", "").lower()

        print("### comment_body ###")
        print(comment_body)

        BLOCKER_KEYWORDS = ["blocked", "stuck", "need help", "can't proceed", "cannot proceed"]

        if any(word in comment_body for word in BLOCKER_KEYWORDS):
            event_dict["is_blocker"] = True

        # -----------------------------------------------------
        # 5b. Status transitions → blocker detection
        # -----------------------------------------------------
        changelog = payload.get("changelog", {})
        for item in changelog.get("items", []):
            if item.get("field") == "status":
                to_status = (item.get("toString") or "").lower()
                if "blocked" in to_status:
                    event_dict["is_blocker"] = True

        current_status = (fields.get("status", {}) or {}).get("name", "")
        if isinstance(current_status, str) and "blocked" in current_status.lower():
            event_dict["is_blocker"] = True

        print("### event_dict ###")
        print(event_dict)

        # -----------------------------------------------------
        # 6. SAAM v2: cues → features → ML risk → persona
        # -----------------------------------------------------
        cues = extract_cues(event_dict)
        features = build_feature_vector(cues)

        model = load_model()
        risk_index_raw = model.predict(features)[0] if model else 0.5

        risk_raw = float(risk_index_raw)
        risk_raw = max(0.0, min(1.0, risk_raw))

        if risk_raw < 0.33:
            ml_persona_label = "healthy"
        elif risk_raw < 0.66:
            ml_persona_label = "silent"
        else:
            ml_persona_label = "blocked"

        persona_label = ml_persona_label

        override_reason = None

        if event_dict.get("is_blocker", False):
            persona_label = "blocked"
            override_reason = "blocker_comment"

        current_status = (fields.get("status", {}) or {}).get("name", "")
        if isinstance(current_status, str) and "blocked" in current_status.lower():
            persona_label = "blocked"
            override_reason = override_reason or "blocked_status"

        cues["risk_score"] = round(risk_raw, 3)

        if persona_label == "blocked":
            cues["risk_score"] = max(cues["risk_score"], 0.75)

        cues["override_trace"] = {
            "ml_score": risk_raw,
            "ml_persona": ml_persona_label,
            "final_persona": persona_label,
            "override_reason": override_reason,
        }

        # -----------------------------------------------------
        # 7. Behavioural stats
        # -----------------------------------------------------
        member_events = (
            db.query(JiraEvent)
            .filter_by(triggered_by_id=jira_user.id)
            .order_by(JiraEvent.timestamp.asc())
            .all()
        )

        event_dicts = []
        for ev in member_events:
            event_dicts.append({
                "timestamp": ev.timestamp.isoformat(),
                "signal_type": ev.event_type,
                "raw_payload": ev.raw_payload,
                "issue_id": ev.issue_id,
            })

        stats = jira_to_stats(event_dicts)
        cues.update(stats)

        # -----------------------------------------------------
        # 8. Generate intervention
        # -----------------------------------------------------
        intervention = select_intervention(persona_label, cues)

        # -----------------------------------------------------
        # 9. Serialize cues
        # -----------------------------------------------------
        cues = serialize_cues(cues)

        queue_entry = InterventionQueue(
            id=str(uuid.uuid4()),
            team_member_id=tm.id,
            intervention_text=intervention.get("message"),
            risk_label=persona_label,
            cues=cues,
            created_at=datetime.now(timezone.utc),
            sent_at=None
        )

        db.add(queue_entry)
        db.commit()

        # -----------------------------------------------------
        # 10. Store behavioural signal
        # -----------------------------------------------------
        interaction = TeamMemberInteraction(
            id=str(uuid.uuid4()),
            team_member_id=tm.id,
            jira_event_id=jira_event.id,
            signal_type=event_type,
            weight=1.0,
            event_metadata=event_dict,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(interaction)
        db.commit()

        # -----------------------------------------------------
        # 11. Self‑labelling (NOW INSIDE THE TRY BLOCK)
        # -----------------------------------------------------
        comments = cues.get("comment_count", 0) or event_dict.get("team_comment_count", 0)
        assignments = cues.get("assignment_count", 0)
        transitions = cues.get("status_transition_count", 0)

        label_map = {"silent": 0, "healthy": 1, "blocked": 2}
        label = label_map.get(persona_label, 0)

        training_sample = TrainingSample(
            id=str(uuid.uuid4()),
            team_member_id=tm.id,
            issue_id=jira_issue.id,
            timestamp=datetime.now(timezone.utc),
            comments=comments,
            assignments=assignments,
            transitions=transitions,
            label=label,
        )

        db.add(training_sample)
        db.commit()

        print(">>> TRAINING SAMPLE STORED <<<")

        # -----------------------------------------------------
        # 12. Return SAAM v2 output
        # -----------------------------------------------------
        cues = sanitize(cues)
        intervention = sanitize(intervention)

        return {
            "status": "ok",
            "team_member_id": tm.id,
            "risk_label": persona_label,
            "cues": cues,
            "intervention": intervention,
        }

    except Exception as e:
        db.rollback()
        raise e

    finally:
        db.close()
