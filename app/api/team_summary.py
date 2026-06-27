# app/api/team_summary.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from db.database import get_db
from app.saam.team_summary import compute_daily_team_summary

router = APIRouter()

@router.get("/team/summary/daily")
def daily_team_summary(db: Session = Depends(get_db)):
    """
    Returns a daily team health summary based on the last 24 hours
    of TeamMemberInteraction events.
    """
    summary = compute_daily_team_summary(db)

    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary
    }
