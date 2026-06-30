# app/saam/saam_logging.py

import json
import os
from datetime import datetime, timezone

LOG_DIR = "interaction_logs"
os.makedirs(LOG_DIR, exist_ok=True)


def log_interaction(record: dict, filename: str = "experiment.jsonl"):
    """
    Append a single interaction record to a JSONL log file.
    Also prints a readable summary to the console for debugging.
    """

    # -----------------------------------------------------
    # Add timestamp
    # -----------------------------------------------------
    record_with_timestamp = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **record
    }

    # -----------------------------------------------------
    # JSONL logging
    # -----------------------------------------------------
    path = os.path.join(LOG_DIR, filename)

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record_with_timestamp) + "\n")

    # -----------------------------------------------------
    # Console pretty‑print
    # -----------------------------------------------------
    print("\n================ SAAM LOG ENTRY ================")
    print(f"Timestamp: {record_with_timestamp.get('timestamp')}")
    print(f"Persona: {record_with_timestamp.get('persona')}")
    print(f"Predicted Label: {record_with_timestamp.get('predicted_label')}")
    print(f"Risk Score: {record_with_timestamp.get('risk_score')}")
    print(f"Intervention: {record_with_timestamp.get('intervention_type')}")
    print(f"Action: {record_with_timestamp.get('action')}")
    print(f"Message: {record_with_timestamp.get('saam_message')}")
    print("================================================\n")

    return path
