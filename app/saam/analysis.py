# app/saam/analysis.py

import json
import os
from statistics import mean


def load_logs(filename: str):
    """
    Load a JSONL experiment log file into a list of dicts.
    """
    path = os.path.join("interaction_logs", filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Log file not found: {path}")

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def analyse_logs(records: list):
    """
    Compute summary statistics from experiment logs.
    Safely handles missing fields and inconsistent log formats.
    """

    # Extract fields safely
    sentiments = [
        r.get("sentiment_estimate")
        for r in records
        if r.get("sentiment_estimate") is not None
    ]

    predicted_labels = [
        r.get("predicted_label")
        for r in records
        if r.get("predicted_label") is not None
    ]

    intervention_types = [
        r.get("intervention_type")
        for r in records
        if r.get("intervention_type") is not None
    ]

    # Avoid crashes on empty logs
    avg_sentiment = mean(sentiments) if sentiments else 0
    sentiment_min = min(sentiments) if sentiments else 0
    sentiment_max = max(sentiments) if sentiments else 0

    return {
        "rounds": len(records),
        "avg_sentiment": avg_sentiment,
        "sentiment_min": sentiment_min,
        "sentiment_max": sentiment_max,
        "label_distribution": {
            "silent": predicted_labels.count("silent"),
            "healthy": predicted_labels.count("healthy"),
            "blocked": predicted_labels.count("blocked"),
        },
        "intervention_distribution": {
            "soft": intervention_types.count("soft"),
            "escalate": intervention_types.count("escalate"),
            "none": intervention_types.count("none"),
        }
    }
