# app/saam/risk_trend.py

import json
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict

LOG_DIR = "interaction_logs"
LOG_FILE = "experiment.jsonl"


def load_jsonl_logs(days: int):
    """
    Load JSONL logs from the last N days.
    Returns a list of parsed log entries.
    """

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    logs = []

    path = os.path.join(LOG_DIR, LOG_FILE)
    if not os.path.exists(path):
        return logs

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                ts_raw = entry.get("timestamp")
                if not ts_raw:
                    continue

                ts = datetime.fromisoformat(ts_raw)
                if ts >= cutoff:
                    logs.append(entry)

            except (json.JSONDecodeError, ValueError):
                # Skip malformed lines
                continue

    return logs


def compute_risk_trend(days: int = 14):
    """
    Compute team-level and per-member risk trends over time.
    Output:
        {
            "team_risk_trend": [...],
            "members": [...]
        }
    """

    logs = load_jsonl_logs(days)
    if not logs:
        return {"team_risk_trend": [], "members": []}

    # -----------------------------------------
    # Group by date
    # -----------------------------------------
    team_daily = defaultdict(list)
    member_daily = defaultdict(lambda: defaultdict(list))

    for entry in logs:
        ts_raw = entry.get("timestamp")
        if not ts_raw:
            continue

        try:
            ts = datetime.fromisoformat(ts_raw)
        except ValueError:
            continue

        date_key = ts.date().isoformat()

        risk = entry.get("risk_score")
        name = entry.get("persona")

        if risk is None or name is None:
            continue

        team_daily[date_key].append(risk)
        member_daily[name][date_key].append(risk)

    # -----------------------------------------
    # Compute team-level averages
    # -----------------------------------------
    team_trend = []
    for date_key in sorted(team_daily.keys()):
        values = team_daily[date_key]
        avg_risk = sum(values) / len(values)
        team_trend.append({
            "date": date_key,
            "avg_risk": round(avg_risk, 3)
        })

    # -----------------------------------------
    # Compute per-member trends
    # -----------------------------------------
    members = []
    for name, dates in member_daily.items():
        trend = []
        for date_key in sorted(dates.keys()):
            values = dates[date_key]
            avg_risk = sum(values) / len(values)
            trend.append({
                "date": date_key,
                "risk": round(avg_risk, 3)
            })

        members.append({
            "name": name,
            "risk_trend": trend
        })

    return {
        "team_risk_trend": team_trend,
        "members": members
    }
