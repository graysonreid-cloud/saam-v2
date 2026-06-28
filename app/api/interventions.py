from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
from uuid import UUID

from db.database import SessionLocal
from db.db_models import InterventionQueue, TeamMember

print("### USING THIS INTERVENTIONS.PY ###")
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/saam/interventions/pending")
def get_pending_intervention(db: Session = Depends(get_db)):
    entry = (
        db.query(InterventionQueue)
        .filter(InterventionQueue.sent_at.is_(None))
        .order_by(InterventionQueue.created_at.asc())
        .first()
    )


    if not entry:
        print("PENDING: none")
        return {"status": "none"}

    print("PENDING UUID:", entry.id)

    member = db.query(TeamMember).filter_by(id=entry.team_member_id).first()

    return {
        "id": entry.id,
        "team_member_name": member.display_name if member else "Unknown",
        "intervention_text": entry.intervention_text,
        "risk_label": entry.risk_label,
        "cues": entry.cues,
        "created_at": entry.created_at.isoformat(),
    }

class MarkSentPayload(BaseModel):
    id: str

@router.post("/saam/interventions/mark-sent")
def mark_intervention_sent(payload: MarkSentPayload, db: Session = Depends(get_db)):
    print("MARK-SENT RAW UUID:", repr(payload.id))

    clean_id = payload.id.strip()
    print("MARK-SENT CLEAN UUID:", clean_id)

    from uuid import UUID
    try:
        intervention_uuid = UUID(clean_id)
    except Exception:
        print("MARK-SENT ERROR: invalid UUID")
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    print("MARK-SENT PARSED UUID:", intervention_uuid)

    # FIX: compare using string
    entry = db.query(InterventionQueue).filter_by(id=str(intervention_uuid)).first()

    if not entry:
        print("MARK-SENT: UUID NOT FOUND IN DB")
        return {"status": "not_found"}

    print("MARK-SENT: UUID FOUND — marking sent")

    entry.sent_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "ok", "id": str(intervention_uuid)}



