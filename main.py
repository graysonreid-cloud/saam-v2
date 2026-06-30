from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel

from db.db_models import JiraIssue
from app.saam.synthetic_sprint import generate_synthetic_sprint
from db.database import SessionLocal

# Load environment variables early
load_dotenv()

app = FastAPI(title="SAAM Backend")

# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------
from app.api.webhooks.jira_webhook import router as jira_router
app.include_router(jira_router, prefix="/webhook")

from app.api.model_inspection import router as model_inspection_router
app.include_router(model_inspection_router)

from app.api.team_summary import router as team_summary_router
app.include_router(team_summary_router, prefix="/api")

from app.api.risk_trend import router as risk_trend_router
app.include_router(risk_trend_router, prefix="/api")

from app.api import interventions
app.include_router(interventions.router)

# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class TeamState(BaseModel):
    participation_level: float
    talktime_imbalance: float
    blocker_age: float
    blocker_owner_missing: bool
    ceremony_type: str
    time_remaining: float

# ---------------------------------------------------------
# Startup
# ---------------------------------------------------------
@app.on_event("startup")
def populate_if_empty():
    db = SessionLocal()

    # Correct table to check — synthetic sprint inserts JiraIssue rows
    issue_count = db.query(JiraIssue).count()

    if issue_count == 0:
        print("SAAM: Empty DB detected — generating synthetic sprint...")
        generate_synthetic_sprint(db)
    else:
        print("SAAM: Existing data detected — skipping synthetic sprint.")

    db.close()


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

