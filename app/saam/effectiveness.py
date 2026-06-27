# app/saam/effectiveness.py

from collections import defaultdict
from statistics import mean


def intervention_effectiveness(records: list):
    """
    Compute sentiment outcomes grouped by intervention type.
    """

    buckets = defaultdict(list)

    for r in records:
        intervention = r.get("intervention_type")
        sentiment = r.get("sentiment_estimate")

        if intervention is None or sentiment is None:
            continue

        buckets[intervention].append(sentiment)

    table = []

    for intervention, sentiments in buckets.items():
        table.append({
            "Intervention Type": intervention,
            "Rounds": len(sentiments),
            "Avg Sentiment": round(mean(sentiments), 3),
            "Min Sentiment": round(min(sentiments), 3),
            "Max Sentiment": round(max(sentiments), 3),
        })

    return table
