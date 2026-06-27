# app/saam/synthetic.py

import random
import numpy as np

from app.saam.cues import extract_cues
from app.saam.features import build_feature_vector


def generate_persona_cues(persona: str) -> dict:
    """
    Generate synthetic cue values for a given persona.
    """

    if persona == "healthy":
        return {
            "participation_level": random.uniform(0.7, 1.0),
            "talktime_imbalance": random.uniform(0.0, 0.2),
            "blocker_age": random.uniform(0, 1),
            "missing_updates": False,
            "blocker_owner_missing": False,
            "time_remaining": random.uniform(3, 8),
            "goal_changes": 0,
            "ceremony_type": "standup",
            "sentiment_score": random.uniform(0.2, 0.8),
            "workload_ratio": random.uniform(0.8, 1.2),
            "help_requests": random.randint(0, 1),
            "help_offers": random.randint(1, 3),
        }

    if persona == "silent":
        return {
            "participation_level": random.uniform(0.0, 0.3),
            "talktime_imbalance": random.uniform(0.5, 0.9),
            "blocker_age": random.uniform(0, 2),
            "missing_updates": True,
            "blocker_owner_missing": False,
            "time_remaining": random.uniform(3, 8),
            "goal_changes": 0,
            "ceremony_type": "standup",
            "sentiment_score": random.uniform(-0.2, 0.2),
            "workload_ratio": random.uniform(0.8, 1.0),
            "help_requests": 0,
            "help_offers": 0,
        }

    if persona == "blocked":
        return {
            "participation_level": random.uniform(0.2, 0.5),
            "talktime_imbalance": random.uniform(0.2, 0.5),
            "blocker_age": random.uniform(3, 10),
            "missing_updates": True,
            "blocker_owner_missing": True,
            "time_remaining": random.uniform(1, 5),
            "goal_changes": random.randint(0, 1),
            "ceremony_type": "standup",
            "sentiment_score": random.uniform(-0.6, -0.1),
            "workload_ratio": random.uniform(1.2, 1.8),
            "help_requests": random.randint(1, 4),
            "help_offers": 0,
        }

    raise ValueError(f"Unknown persona: {persona}")


def generate_training_dataset(n_per_persona: int = 200):
    """
    Generate a full synthetic training dataset for:
    - healthy
    - silent
    - blocked

    Returns:
        X: numpy array of feature vectors
        y: numpy array of labels
    """

    personas = ["healthy", "silent", "blocked"]
    label_map = {"silent": 0, "healthy": 1, "blocked": 2}

    X, y = [], []

    for persona in personas:
        for _ in range(n_per_persona):
            raw = generate_persona_cues(persona)
            cues = extract_cues(raw)
            vector = build_feature_vector(cues)

            X.append(vector[0])
            y.append(label_map[persona])

    return np.array(X), np.array(y)
