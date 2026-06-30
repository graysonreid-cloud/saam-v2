# app/api/saam_action.py

from fastapi import APIRouter
import joblib

from app.saam.cues import extract_cues
from app.saam.features import build_feature_vector
from app.saam.interventions import select_intervention
from app.saam.interaction import sentiment_score
from app.saam.message_templates import apply_sprint_context_prefix

router = APIRouter()

# Load model once (performance)
MODEL = joblib.load("models/perceptron.pkl")["model"]


@router.post("/saam/action")
def saam_action(raw_stats: dict):
    """
    SAAM Action Endpoint:
    - Extract cues (includes risk_score + sprint context)
    - Build feature vector
    - Predict behavioural class
    - Select intervention (risk-aware)
    - Apply sprint-aware prefix
    - Estimate sentiment
    """

    # 1. Extract cues
    cues = extract_cues(raw_stats)

    # 2. Build feature vector
    X = build_feature_vector(cues)

    # 3. Predict class
    pred_class = MODEL.predict(X)[0]
    label_map = {0: "silent", 1: "healthy", 2: "blocked"}
    predicted_label = label_map.get(pred_class, "unknown")

    # 4. Select intervention (modern engine)
    action = select_intervention(predicted_label, cues)

    # 5. Sprint-aware prefix
    action["message"] = apply_sprint_context_prefix(action["message"], cues)

    # 6. Sentiment estimate
    sentiment = sentiment_score(action["message"])

    return {
        "status": "ok",
        "prediction": predicted_label,
        "risk_score": cues.get("risk_score"),
        "intervention_type": action["type"],
        "action": action["action"],
        "message": action["message"],
        "sentiment_estimate": sentiment,
        "cues": cues
    }
