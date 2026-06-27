# app/saam/interaction.py

import joblib
from textblob import TextBlob

from .cues import extract_cues
from .features import build_feature_vector
from app.saam.interventions import select_intervention
from .personas import (
    silent_persona_reply,
    healthy_persona_reply,
    blocked_persona_reply,
)

PERSONA_MAP = {
    "silent": silent_persona_reply,
    "healthy": healthy_persona_reply,
    "blocked": blocked_persona_reply,
}


def sentiment_score(text: str) -> float:
    """
    Simple sentiment scoring using TextBlob polarity (-1 to +1).
    """
    return TextBlob(text).sentiment.polarity


def run_interaction_round(persona: str, raw_stats: dict, model_path="models/perceptron.pkl"):
    """
    Runs a single SAAM → Persona → Sentiment interaction cycle.
    """

    # -----------------------------------------------------
    # 1. Load model
    # -----------------------------------------------------
    model = joblib.load(model_path)["model"]

    # -----------------------------------------------------
    # 2. Extract cues
    # -----------------------------------------------------
    cues = extract_cues(raw_stats)

    # -----------------------------------------------------
    # 3. Build feature vector
    # -----------------------------------------------------
    X = build_feature_vector(cues)

    # -----------------------------------------------------
    # 4. Predict behavioural class
    # -----------------------------------------------------
    pred = model.predict(X)[0]
    label_map = {0: "silent", 1: "healthy", 2: "blocked"}
    predicted_label = label_map.get(pred, "healthy")

    # -----------------------------------------------------
    # 5. Select SAAM action
    # -----------------------------------------------------
    saam_action = select_action(predicted_label, cues)
    saam_message = saam_action["message"]

    # -----------------------------------------------------
    # 6. Persona replies
    # -----------------------------------------------------
    persona_fn = PERSONA_MAP.get(persona)
    if not persona_fn:
        raise ValueError(f"Unknown persona: {persona}")

    persona_reply = persona_fn(saam_message)

    # -----------------------------------------------------
    # 7. Sentiment score
    # -----------------------------------------------------
    sentiment = sentiment_score(persona_reply)

    # -----------------------------------------------------
    # 8. Return full interaction record
    # -----------------------------------------------------
    return {
        "persona": persona,
        "predicted_label": predicted_label,
        "saam_message": saam_message,
        "persona_reply": persona_reply,
        "sentiment_estimate": sentiment,   # aligned with analysis.py
        "cues": cues,
        "intervention_type": saam_action["intervention_type"],
        "action": saam_action["action"],
    }
