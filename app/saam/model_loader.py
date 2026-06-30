# app/saam/model_loader.py
import joblib
import os

MODEL_PATH = "models/perceptron.pkl"

def load_model():
    if not os.path.exists(MODEL_PATH):
        print("No model found — using fallback risk score.")
        return None

    data = joblib.load(MODEL_PATH)
    print("Loaded SAAM model from models/perceptron.pkl")
    return data["model"]
