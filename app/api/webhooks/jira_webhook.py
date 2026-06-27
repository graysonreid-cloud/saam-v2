from fastapi import APIRouter, Request as FastAPIRequest
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timezone

from db.database import SessionLocal
from db.db_models import (
    Request as SAAMRequest,
    JiraUser, JiraIssue, JiraEvent,
    TeamMember, TeamMemberInteraction
)

# SAAM v2 engine
from app.saam.cues import extract_cues
from app.saam.features import build_feature_vector
from app.saam.interventions import select_intervention
from app.saam.model_loader import MODEL


router = APIRouter()


@router.post("/jira")
async def jira_webhook(request: FastAPIRequest):
    db: Session = SessionLocal()

    try:
        payload = await request.json()
        event_type = payload.get("webhookEvent")
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})

        # -----------------------------------------------------
        # 0. Filter non-behavioural events
        # -----------------------------------------------------
        changelog = payload.get("changelog", {})
        items = changelog.get("items", [])

        behavioural = (
            "comment" in payload
            or any(i.get("field") == "assignee" for i in items)
            or any(i.get("field") == "status" for i in items)
            or event_type == "worklog_updated"
        )

        if not behavioural:
            print(f"Ignoring non-behavioural event: {event_type}")
            return {"status": "ignored_event"}

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
        # 2. Extract identity (SAAM v2)
        # -----------------------------------------------------
        actor = fields.get("assignee") or payload.get("user", {})
        account_id = actor.get("accountId")
        display_name = actor.get("displayName")
        email = actor.get("emailAddress")

        # JiraUser
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

        # TeamMember
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
        # 5. Build SAAM v2 event dict
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
        # 6. SAAM v2: cues → features → risk → intervention
        # -----------------------------------------------------
        cues = extract_cues(event_dict)
        features = build_feature_vector(cues)
        risk_label = MODEL.predict(features)[0]
        intervention = select_intervention(risk_label, cues)

        # -----------------------------------------------------
        # 7. Store behavioural signal
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
        # 8. Return SAAM v2 output
        # -----------------------------------------------------

        import numpy as np

        # Convert numpy scalar → Python int
        if isinstance(risk_label, np.generic):
            risk_label = risk_label.item()

        # Convert any numpy values inside cues
        cues = {k: (v.item() if isinstance(v, np.generic) else v) for k, v in cues.items()}

        # Convert any numpy values inside intervention
        intervention = {
            k: (v.item() if isinstance(v, np.generic) else v)
            for k, v in intervention.items()
        }



        return {
            "status": "ok",
            "team_member_id": tm.id,
            "risk_label": risk_label,
            "cues": cues,
            "intervention": intervention,
        }

    except Exception as e:
        db.rollback()
        raise e

    finally:
        db.close()
