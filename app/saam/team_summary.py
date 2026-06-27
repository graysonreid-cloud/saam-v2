# app/saam/team_summary.py

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from db.db_models import TeamMember, TeamMemberInteraction


def compute_daily_team_summary(db: Session):
    """
    Compute a daily team health summary using:
    - risk scores
    - participation
    - sentiment
    """

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    # -----------------------------------------
    # 1. Fetch interactions in last 24 hours
    # -----------------------------------------
    interactions = (
        db.query(TeamMemberInteraction)
        .filter(TeamMemberInteraction.timestamp >= since)
        .all()
    )

    if not interactions:
        return {
            "team_risk_avg": 0,
            "team_sentiment_avg": 0,
            "team_participation_avg": 0,
            "members": []
        }

    # -----------------------------------------
    # 2. Group by team member
    # -----------------------------------------
    member_data = {}

    # Preload all team members once (avoid repeated DB hits)
    team_members = {
        tm.id: tm.display_name
        for tm in db.query(TeamMember).all()
    }

    for inter in interactions:
        tm_id = inter.team_member_id

        if tm_id not in member_data:
            member_data[tm_id] = {
                "risk_scores": [],
                "sentiments": [],
                "participation": 0,
                "display_name": team_members.get(tm_id, "Unknown")
            }

        meta = inter.event_metadata or {}

        # Risk score
        risk = meta.get("risk_score")
        if risk is not None:
            member_data[tm_id]["risk_scores"].append(risk)

        # Sentiment (your logs use "sentiment_estimate")
        sentiment = meta.get("sentiment_estimate")
        if sentiment is not None:
            member_data[tm_id]["sentiments"].append(sentiment)

        # Participation proxy
        member_data[tm_id]["participation"] += 1

    # -----------------------------------------
    # 3. Compute per-member aggregates
    # -----------------------------------------
    members_summary = []

    for tm_id, data in member_data.items():
        risk_scores = data["risk_scores"]
        sentiments = data["sentiments"]

        risk_avg = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        sentiment_avg = sum(sentiments) / len(sentiments) if sentiments else 0

        members_summary.append({
            "team_member_id": tm_id,
            "display_name": data["display_name"],
            "risk_avg": round(risk_avg, 3),
            "sentiment_avg": round(sentiment_avg, 3),
            "participation_count": data["participation"]
        })

    # -----------------------------------------
    # 4. Compute team-level aggregates
    # -----------------------------------------
    team_risk_avg = sum(m["risk_avg"] for m in members_summary) / len(members_summary)
    team_sentiment_avg = sum(m["sentiment_avg"] for m in members_summary) / len(members_summary)
    team_participation_avg = sum(m["participation_count"] for m in members_summary) / len(members_summary)

    return {
        "team_risk_avg": round(team_risk_avg, 3),
        "team_sentiment_avg": round(team_sentiment_avg, 3),
        "team_participation_avg": round(team_participation_avg, 3),
        "members": members_summary
    }
