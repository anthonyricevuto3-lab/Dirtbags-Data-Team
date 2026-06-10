"""
Fetch bullpen session CSVs from Portable Trackman B1 API and save to Trackman Bullpens/.

Fill in the API_BASE, AUTH, and endpoint paths according to the vendor docs.
This script assumes the API can return CSV or JSON that we convert to CSV.
"""

import os
import sys
import csv
import datetime as dt
from pathlib import Path
from typing import List, Dict, Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


API_BASE = os.environ.get("PORTABLE_B1_API_BASE", "https://api.example.com/v1")  # placeholder
OUTPUT_DIR = Path("Trackman Bullpens")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_env():
    if load_dotenv:
        load_dotenv()
    creds = {
        "api_key": os.environ.get("PORTABLE_B1_API_KEY"),
        "identifier": os.environ.get("PORTABLE_B1_IDENTIFIER"),
        "name": os.environ.get("PORTABLE_B1_NAME"),
        "username": os.environ.get("PORTABLE_B1_USERNAME"),
        "password": os.environ.get("PORTABLE_B1_PASSWORD"),
    }
    missing = [k for k, v in creds.items() if not v]
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")
    return creds


def authenticate(creds) -> Dict[str, str]:
    """
    Placeholder auth. Replace with the actual auth flow.
    """
    # Example: token = requests.post(f"{API_BASE}/auth", json={...})
    # return {"Authorization": f"Bearer {token}"}
    return {"x-api-key": creds["api_key"]}


def fetch_sessions(headers) -> List[Dict[str, Any]]:
    """
    Placeholder fetch. Replace endpoint/params per API.
    Should return a list of session dicts including player name and date and pitches.
    """
    # Example:
    # resp = requests.get(f"{API_BASE}/bullpen/sessions", headers=headers, timeout=30)
    # resp.raise_for_status()
    # return resp.json().get("sessions", [])
    return []


def to_filename(session) -> Path:
    # Expect session has first_name, last_name, date (YYYY-MM-DD). Adjust as needed.
    first = session.get("first_name", "Unknown")
    last = session.get("last_name", "Unknown")
    date = session.get("date", dt.date.today().isoformat())
    fname = f"{last}_{first}_{date}.csv"
    return OUTPUT_DIR / fname


def save_csv(path: Path, rows: List[Dict[str, Any]]):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    try:
        creds = load_env()
        headers = authenticate(creds)
        sessions = fetch_sessions(headers)
        saved = 0
        for s in sessions:
            rows = s.get("pitches") or []
            if not rows:
                continue
            out_path = to_filename(s)
            if out_path.exists():
                continue  # skip duplicates
            save_csv(out_path, rows)
            saved += 1
        print(f"Saved {saved} session CSV(s) to {OUTPUT_DIR}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
