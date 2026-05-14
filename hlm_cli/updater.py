import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

STATE_DIR = Path.home() / ".hlm"
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "update_state.json"


def get_current_version():
    try:
        from importlib.metadata import version
        return version("hlm-cli")
    except Exception:
        return "0.1.0"


def fetch_latest_version():
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/chasew28/homelab-monitor/releases/latest",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "homelab-monitor",
            },
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        return data.get("tag_name", "").lstrip("v")
    except Exception:
        return None


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_check": 0, "available": False, "current": "", "latest": ""}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state))


def check_for_update(force=False):
    now = time.time()
    day = 86400
    state = load_state()

    if not force and (now - state.get("last_check", 0)) < day:
        return state

    current = get_current_version()
    latest = fetch_latest_version()

    state["last_check"] = now
    state["current"] = current
    state["available"] = bool(latest and latest != current)
    state["latest"] = latest or current
    save_state(state)
    return state


def perform_update():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade",
         "git+https://github.com/chasew28/homelab-monitor.git"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        STATE_FILE.unlink(missing_ok=True)
        return True, get_current_version()
    return False, result.stderr
