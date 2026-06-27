# app/saam/persona_compare.py

from .analysis import load_logs, analyse_logs


def compare_personas(log_files: dict):
    """
    Compare multiple personas using their experiment log files.

    log_files = {
        "silent": "silent_experiment.jsonl",
        "healthy": "healthy_experiment.jsonl",
        "blocked": "blocked_experiment.jsonl"
    }
    """

    comparison = []

    for persona, filename in log_files.items():
        records = load_logs(filename)
        summary = analyse_logs(records)

        rounds = summary.get("rounds", 0) or 1  # avoid division by zero
        labels = summary.get("label_distribution", {})
        interventions = summary.get("intervention_distribution", {})

        comparison.append({
            "Persona": persona,
            "Rounds": summary.get("rounds", 0),
            "Avg Sentiment": round(summary.get("avg_sentiment", 0), 3),

            # Label distribution
            "Silent %": round(labels.get("silent", 0) / rounds, 2),
            "Healthy %": round(labels.get("healthy", 0) / rounds, 2),
            "Blocked %": round(labels.get("blocked", 0) / rounds, 2),

            # Intervention distribution (corrected categories)
            "Soft %": round(interventions.get("soft", 0) / rounds, 2),
            "Escalate %": round(interventions.get("escalate", 0) / rounds, 2),
            "None %": round(interventions.get("none", 0) / rounds, 2),
        })

    return comparison
