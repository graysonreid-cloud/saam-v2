import sys
import os
import subprocess
import time

# ============================================================
# 1. AUTO-SWITCH TO VENV PYTHON
# ============================================================
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(ROOT, "venv", "Scripts", "python.exe")

if sys.executable.lower() != VENV_PYTHON.lower():
    print("[SAAM] Switching to venv Python...")
    subprocess.call([VENV_PYTHON, __file__])
    sys.exit()


# ============================================================
# 2. AUTO-INSTALL DEPENDENCIES
# ============================================================
def ensure_dependencies():
    required = ["requests"]

    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            print(f"[SAAM] Missing dependency: {pkg}. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


ensure_dependencies()

import requests  # now safe to import


# ============================================================
# 3. KILL EXISTING NGROK
# ============================================================
print("[SAAM] Killing any existing ngrok processes...")
try:
    subprocess.run(
        ["taskkill", "/F", "/IM", "ngrok.exe"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print("[SAAM] Existing ngrok processes terminated.")
except Exception:
    print("[SAAM] No existing ngrok processes found.")


# ============================================================
# 4. START NGROK
# ============================================================
print("[SAAM] Starting ngrok on port 8000...")
ngrok = subprocess.Popen(["ngrok", "http", "8000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(2)  # allow ngrok to boot


# ============================================================
# 5. RETRY LOOP TO FETCH PUBLIC URL
# ============================================================
public_url = None
print("[SAAM] Fetching ngrok public URL...")

for attempt in range(1, 11):
    try:
        tunnels = requests.get("http://127.0.0.1:4042/api/tunnels").json()
        public_url = tunnels["tunnels"][0]["public_url"]
        print(f"[SAAM] ngrok tunnel established on attempt {attempt}.")
        break
    except Exception:
        print(f"[SAAM] ngrok not ready (attempt {attempt}/10)...")
        time.sleep(1)

if not public_url:
    print("[SAAM] ERROR: Could not fetch ngrok URL after retries.")
    sys.exit(1)

print(f"[SAAM] NGROK URL: {public_url}")


# ============================================================
# 6. WRITE URL TO .env FOR BACKEND USE
# ============================================================
env_path = os.path.join(ROOT, ".env")

try:
    with open(env_path, "a") as f:
        f.write(f"\nNGROK_URL={public_url}\n")
    print(f"[SAAM] ngrok URL written to .env")
except Exception as e:
    print(f"[SAAM] WARNING: Could not write to .env: {e}")


# ============================================================
# 7. KEEP PROCESS ALIVE
# ============================================================
print("[SAAM] ngrok is running. Press CTRL+C to stop.")
try:
    ngrok.wait()
except KeyboardInterrupt:
    print("\n[SAAM] Shutting down ngrok...")
    ngrok.terminate()
