import sys
import os
import time

# Ensure project root is on PYTHONPATH
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# IMPORTANT: import models AFTER sys.path is set
import db.db_models

from db.database import init_db
import uvicorn


def run_backend():
    """
    Starts the SAAM backend in single‑worker mode.
    No reload, no duplicate processes.
    """
    print("\n========================================")
    print("        Starting SAAM Backend")
    print("========================================")
    print("Uvicorn command: uvicorn main:app")
    print("Ngrok: run start_webhook.py in another terminal")
    print("========================================\n")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,     # <-- IMPORTANT: prevents double execution
        workers=1         # <-- ensures only one worker handles webhooks
    )


if __name__ == "__main__":
    # Initialize DB once
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")

    time.sleep(0.3)

    # Start backend
    run_backend()
