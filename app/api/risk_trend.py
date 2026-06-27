# app/api/risk_trend.py

from fastapi import APIRouter
from datetime import datetime, timezone

from app.saam.risk_trend import compute_risk_trend

router = APIRouter()

@router.get("/team/risk/trend")
def risk_trend(days: int = 14):
    """
    Returns team-level risk trends over the last N days.
    Includes:
      - team average risk per day
      - per-member risk curves
    """
    trend = compute_risk_trend(days)

    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "data": trend
    }
