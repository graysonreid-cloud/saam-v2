from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.engine.perceptron_train import train_perceptron

router = APIRouter()

class TrainingRow(BaseModel):
    user_id: str
    comments: int
    assignments: int
    transitions: int
    label: int  # 1 = healthy, 0 = low_collaboration

class TrainingPayload(BaseModel):
    data: List[TrainingRow]

@router.post("/saam/train")
def train_perceptron_endpoint(payload: TrainingPayload):
    """
    Retrains the perceptron model using the provided dataset.
    Overwrites models/perceptron.pkl.
    """
    dataset = [row.dict() for row in payload.data]
    train_perceptron(dataset)
    return {"status": "success", "message": "Perceptron model retrained."}
