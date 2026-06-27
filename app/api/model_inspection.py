from fastapi import APIRouter
import joblib

from app.saam.features import FEATURE_ORDER

router = APIRouter()

# Load model once for performance
MODEL_PATH = "models/perceptron.pkl"
MODEL = joblib.load(MODEL_PATH)["model"]


@router.get("/saam/model")
def inspect_model():
    """
    Returns perceptron weights, bias, and feature importance.
    Provides full transparency into SAAM's decision boundary.
    """

    # Extract model parameters
    weights = MODEL.coef_[0].tolist()
    bias = float(MODEL.intercept_[0])

    # Map weights to actual SAAM feature names
    feature_importance = {
        feature: round(weight, 6)
        for feature, weight in zip(FEATURE_ORDER, weights)
    }

    return {
        "model_type": "Perceptron",
        "feature_order": FEATURE_ORDER,
        "weights": feature_importance,
        "bias": bias,
        "decision_rule": (
            "label = argmax( dot(weights, features) + bias ) "
            "where 0=silent, 1=healthy, 2=blocked"
        )
    }
