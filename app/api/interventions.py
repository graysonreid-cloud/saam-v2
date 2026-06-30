from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
from uuid import UUID

from db.database import SessionLocal
from db.db_models import InterventionQueue, TeamMember, TeamMemberInteraction

# NEW: import the intervention engine
from app.saam.interventions import select_intervention

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# DAILY SUMMARY ENGINE (missing function — now added)
# ---------------------------------------------------------
def compute_daily_team_summary(db: Session):
    """
    Computes a daily summary of team health using SAAM v2 behavioural metadata.
    Includes:
      - risk distribution
      - average risk score
      - per-member latest label
      - event counts
    """

    members = db.query(TeamMember).all()
    interactions = db.query(TeamMemberInteraction).all()

    summary = {
        "team_size": len(members),
        "total_events": len(interactions),
        "blocked_count": 0,
        "silent_count": 0,
        "healthy_count": 0,
        "avg_risk_score": 0.0,
        "members": []
    }

    risk_scores = []

    for m in members:
        m_events = [ev for ev in interactions if ev.team_member_id == m.id]

        labels = []
        for ev in m_events:
            meta = ev.event_metadata or {}
            label = meta.get("risk_label")
            if label:
                labels.append(label)

            rs = meta.get("risk_score")
            if isinstance(rs, (int, float)):
                risk_scores.append(rs)

        latest_label = labels[-1] if labels else None

        if latest_label == "blocked":
            summary["blocked_count"] += 1
        elif latest_label == "silent":
            summary["silent_count"] += 1
        elif latest_label == "healthy":
            summary["healthy_count"] += 1

        summary["members"].append({
            "id": m.id,
            "name": m.display_name,
            "events": len(m_events),
            "latest_label": latest_label
        })

    if risk_scores:
        summary["avg_risk_score"] = round(sum(risk_scores) / len(risk_scores), 3)

    return summary


# ---------------------------------------------------------
# FETCH NEXT INTERVENTION
# ---------------------------------------------------------
@router.get("/saam/interventions/pending")
def get_pending_intervention(db: Session = Depends(get_db)):
    """
    Fetch the next pending intervention AND run it through the full SAAM engine.
    """

    entry = (
        db.query(InterventionQueue)
        .filter(InterventionQueue.sent_at.is_(None))
        .order_by(InterventionQueue.created_at.asc())
        .first()
    )

    if not entry:
        print("PENDING: none")
        return {"status": "none"}

    member = db.query(TeamMember).filter_by(id=entry.team_member_id).first()

    # Run the intervention engine using stored cues + risk label
    intervention = select_intervention(entry.risk_label, entry.cues)

    return {
        "id": entry.id,
        "team_member_name": member.display_name if member else "Unknown",
        "intervention_text": intervention["message"],
        "risk_label": entry.risk_label,
        "cues": entry.cues,
        "created_at": entry.created_at.isoformat(),
    }


# ---------------------------------------------------------
# MARK SENT
# ---------------------------------------------------------
class MarkSentPayload(BaseModel):
    id: str


@router.post("/saam/interventions/mark-sent")
def mark_intervention_sent(payload: MarkSentPayload, db: Session = Depends(get_db)):

    clean_id = payload.id.strip()

    try:
        intervention_uuid = UUID(clean_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    entry = db.query(InterventionQueue).filter_by(id=str(intervention_uuid)).first()

    if not entry:
        return {"status": "not_found"}

    entry.sent_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "ok", "id": str(intervention_uuid)}


# ---------------------------------------------------------
# FULL LIFECYCLE LOGGING
# ---------------------------------------------------------
class MarkLifecyclePayload(BaseModel):
    id: str


@router.post("/saam/interventions/mark-delivered")
def mark_intervention_delivered(payload: MarkLifecyclePayload, db: Session = Depends(get_db)):
    clean_id = payload.id.strip()

    try:
        intervention_uuid = UUID(clean_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    entry = db.query(InterventionQueue).filter_by(id=str(intervention_uuid)).first()
    if not entry:
        return {"status": "not_found"}

    entry.delivered_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "ok", "id": str(intervention_uuid), "stage": "delivered"}


@router.post("/saam/interventions/mark-acknowledged")
def mark_intervention_acknowledged(payload: MarkLifecyclePayload, db: Session = Depends(get_db)):
    clean_id = payload.id.strip()

    try:
        intervention_uuid = UUID(clean_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    entry = db.query(InterventionQueue).filter_by(id=str(intervention_uuid)).first()
    if not entry:
        return {"status": "not_found"}

    entry.acknowledged_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "ok", "id": str(intervention_uuid), "stage": "acknowledged"}


@router.post("/saam/interventions/mark-completed")
def mark_intervention_completed(payload: MarkLifecyclePayload, db: Session = Depends(get_db)):
    clean_id = payload.id.strip()

    try:
        intervention_uuid = UUID(clean_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    entry = db.query(InterventionQueue).filter_by(id=str(intervention_uuid)).first()
    if not entry:
        return {"status": "not_found"}

    entry.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "ok", "id": str(intervention_uuid), "stage": "completed"}


# ---------------------------------------------------------
# DAILY SUMMARY ENDPOINT
# ---------------------------------------------------------
@router.get("/saam/summary/daily")
def saam_daily_summary(db: Session = Depends(get_db)):
    """
    Daily team health summary:
      - avg risk
      - participation
      - per-member breakdown
    """

    summary = compute_daily_team_summary(db)

    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary
    }
