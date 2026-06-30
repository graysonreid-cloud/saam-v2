from fastapi import APIRouter
import joblib
import os

from app.saam.features import FEATURE_ORDER

router = APIRouter()

# Load model once for performance
MODEL_PATH = "models/perceptron.pkl"
MODEL = None

if os.path.exists(MODEL_PATH):
    try:
        MODEL = joblib.load(MODEL_PATH)["model"]
        print("Loaded SAAM model for inspection.")
    except Exception as e:
        print(f"Model inspection loader failed: {e}")
else:
    print("No model found — model inspection disabled.")


@router.get("/saam/model")
def inspect_model():
    """
    Returns perceptron weights, bias, and feature importance.
    Works whether MODEL is a raw Perceptron or a Pipeline.
    """

    # If model is a pipeline, extract the classifier
    clf = MODEL.named_steps["clf"] if hasattr(MODEL, "named_steps") else MODEL

    # Extract model parameters safely
    weights = clf.coef_[0].tolist()
    bias = float(clf.intercept_[0])

    # Map weights to actual SAAM feature names
    feature_importance = {
        feature: round(weight, 6)
        for feature, weight in zip(FEATURE_ORDER, weights)
    }

    return {
        "model_type": "Perceptron (Pipeline)",
        "feature_order": FEATURE_ORDER,
        "weights": feature_importance,
        "bias": bias,
        "decision_rule": (
            "label = argmax( dot(weights, features) + bias ) "
            "where 0=silent, 1=healthy, 2=blocked"
        )
    }
