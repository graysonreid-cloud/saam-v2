# app/saam/features.py

import numpy as np

FEATURE_ORDER = [
    "participation_level",
    "talktime_imbalance",
    "blocker_age",
    "missing_updates",
    "blocker_owner_missing",
    "time_remaining",
    "goal_changes",
    "ceremony_type_encoded",
    "sentiment_score",
    "workload_ratio",
    "help_requests",
    "help_offers",
]


def build_feature_vector(cues: dict) -> np.ndarray:
    """
    Convert cue dictionary into a consistent numpy feature vector.
    Ensures:
      - stable feature ordering
      - numeric conversion
      - safe defaults
    """

    vector = []

    for key in FEATURE_ORDER:
        value = cues.get(key, 0)

        # Defensive: ensure numeric
        try:
            vector.append(float(value))
        except (TypeError, ValueError):
            vector.append(0.0)

    # sklearn expects 2D array
    return np.array([vector])
