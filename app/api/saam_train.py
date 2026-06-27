from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

from app.engine.perceptron_train import train_perceptron
from app.saam.features import FEATURE_ORDER

router = APIRouter()

class TrainingRow(BaseModel):
    user_id: str
    features: Dict[str, Any]   # must match FEATURE_ORDER
    label: int                 # 0 = silent, 1 = healthy, 2 = blocked

class TrainingPayload(BaseModel):
    data: List[TrainingRow]

@router.post("/saam/train")
def saam_train_endpoint(payload: TrainingPayload):
    """
    Retrains the perceptron model using labelled JSON data.
    Expects:
      - features in FEATURE_ORDER
      - labels: 0=silent, 1=healthy, 2=blocked
    """

    dataset = []

    for row in payload.data:
        # Validate feature completeness
        missing = [f for f in FEATURE_ORDER if f not in row.features]
        if missing:
            return {
                "status": "error",
                "message": f"Missing features: {missing}"
            }

        dataset.append({
            "user_id": row.user_id,
            "features": [row.features[f] for f in FEATURE_ORDER],
            "label": row.label
        })

    # Train model using the real-data training engine
    train_perceptron(dataset)

    return {
        "status": "ok",
        "message": "Perceptron model retrained successfully.",
        "feature_order": FEATURE_ORDER,
        "count": len(dataset)
    }
