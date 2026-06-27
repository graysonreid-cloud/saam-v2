# app/saam/results.py

from .analysis import load_logs, analyse_logs


def sentiment_summary_table(summary: dict):
    return [
        {"Metric": "Rounds", "Value": summary.get("rounds", 0)},
        {"Metric": "Average Sentiment", "Value": round(summary.get("avg_sentiment", 0), 3)},
        {"Metric": "Minimum Sentiment", "Value": round(summary.get("sentiment_min", 0), 3)},
        {"Metric": "Maximum Sentiment", "Value": round(summary.get("sentiment_max", 0), 3)},
    ]


def label_distribution_table(summary: dict):
    dist = summary.get("label_distribution", {})
    return [
        {"Label": "Silent", "Count": dist.get("silent", 0)},
        {"Label": "Healthy", "Count": dist.get("healthy", 0)},
        {"Label": "Blocked", "Count": dist.get("blocked", 0)},
    ]


def intervention_distribution_table(summary: dict):
    dist = summary.get("intervention_distribution", {})
    return [
        {"Intervention Type": "Soft", "Count": dist.get("soft", 0)},
        {"Intervention Type": "Escalate", "Count": dist.get("escalate", 0)},
        {"Intervention Type": "None", "Count": dist.get("none", 0)},
    ]


def generate_all_tables(log_filename: str):
    """
    Load logs, analyse them, and generate all results tables.
    """
    records = load_logs(log_filename)
    summary = analyse_logs(records)

    return {
        "sentiment_summary": sentiment_summary_table(summary),
        "label_distribution": label_distribution_table(summary),
        "intervention_distribution": intervention_distribution_table(summary),
    }
