# app/saam/train.py

import numpy as np
import joblib
import os
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.db_models import TrainingSample
from sklearn.linear_model import Perceptron
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# ---------------------------------------------------------
# SAAM v2 — Retrain model using real Jira interactions
# ---------------------------------------------------------

def load_training_data():
    db: Session = SessionLocal()
    samples = db.query(TrainingSample).all()
    db.close()

    if not samples:
        raise ValueError("No training samples found. Trigger Jira events first.")

    X = []
    y = []

    for s in samples:
        X.append([
            s.comments,
            s.assignments,
            s.transitions,

            # NEW: SAAM v2 behavioural features (must match runtime)
            s.silence_days or 0,
            s.blocker_count or 0,
            s.churn_rate or 0,
            s.sentiment_score or 0,
            s.workload_ratio or 0,
            s.help_requests or 0,
            s.help_offers or 0,
            s.talktime_imbalance or 0,
            s.participation_level or 0,
        ])

        y.append(s.label)

    return np.array(X), np.array(y)


def train_saam_model():
    print("Loading training samples...")
    X, y = load_training_data()

    print(f"Training on {len(X)} samples with {X.shape[1]} features...")

    # Must have at least 2 classes
    if len(set(y)) < 2:
        raise ValueError("Need at least 2 different persona labels before training.")

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", Perceptron(max_iter=2000, tol=1e-3))
    ])

    model.fit(X, y)

    os.makedirs("models", exist_ok=True)
    joblib.dump({"model": model}, "models/perceptron.pkl")

    print("Model saved to models/perceptron.pkl")
    print("Training complete.")


if __name__ == "__main__":
    train_saam_model()
