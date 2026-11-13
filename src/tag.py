"""Step 2: tag each complaint's free text with an LLM, returning validated JSON."""
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

from .config import CATEGORIES, FAILURE_TYPES, SEVERITIES

SYSTEM_PROMPT = f"""You classify vehicle owner complaints for a service operations team.
Read the complaint and return ONE JSON object with exactly these keys:

"category": the single vehicle system most responsible. One of: {json.dumps(CATEGORIES)}
"failure_type": one of: {json.dumps(FAILURE_TYPES)}
"severity": one of: {json.dumps(SEVERITIES)}
  - "Safety-critical": crash, fire, injury, or loss of steering, braking or propulsion while driving
  - "Drivability": the car can be driven but a core function is degraded
  - "Inconvenience": comfort, cosmetic or minor annoyance
"service_visit": true if the owner says the car went to a service center or was repaired, else false
"out_of_pocket_usd": the dollar amount the owner says they paid for repair, as a number, or null if none is stated

Rules: choose from the listed values only. Do not guess a cost. Return JSON only, no other text."""


def validate(raw: str) -> dict:
    """Parse the model's reply and reject anything outside the allowed values."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in reply")
    data = json.loads(match.group(0))
    if data.get("category") not in CATEGORIES:
        raise ValueError(f"bad category: {data.get('category')}")
    if data.get("failure_type") not in FAILURE_TYPES:
        raise ValueError(f"bad failure_type: {data.get('failure_type')}")
    if data.get("severity") not in SEVERITIES:
        raise ValueError(f"bad severity: {data.get('severity')}")
    cost = data.get("out_of_pocket_usd")
    if cost is not None:
        cost = float(cost)
        if cost <= 0:
            cost = None
    return {
        "category": data["category"],
        "failure_type": data["failure_type"],
        "severity": data["severity"],
        "service_visit": int(bool(data.get("service_visit"))),
        "out_of_pocket_usd": cost,
    }


def llm_tag(summary: str) -> dict:
    """Call any OpenAI-compatible chat completions endpoint."""
    resp = requests.post(
        os.environ["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
        json={
            "model": os.environ["LLM_MODEL"],
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": summary[:6000]},
            ],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return validate(resp.json()["choices"][0]["message"]["content"])


def mock_tag(summary: str) -> dict:
    """Keyword rules used only to test the pipeline offline. Not used for results."""
    text = summary.lower()
    rules = [
        ("autopilot", "Driver assistance & software"),
        ("steering", "Steering"),
        ("brak", "Brakes"),
        ("suspension", "Suspension, wheels & tires"),
        ("battery", "Battery, charging & propulsion"),
        ("screen", "Electrical & electronics"),
        ("door", "Body, doors & glass"),
        ("airbag", "Restraints & seats"),
    ]
    category = next((cat for kw, cat in rules if kw in text), "Other")
    cost = re.search(r"\$\s?([\d,]+)", summary)
    return {
        "category": category,
        "failure_type": "Unclear",
        "severity": "Safety-critical" if "crash" in text else "Drivability",
        "service_visit": int("service center" in text),
        "out_of_pocket_usd": float(cost.group(1).replace(",", "")) if cost else None,
    }


def _tag_with_retry(odi_number, summary: str, mock: bool):
    """Tag one complaint, retrying up to 3 times. Returns None if every attempt fails."""
    for attempt in range(3):
        try:
            return mock_tag(summary) if mock else llm_tag(summary)
        except Exception as exc:  # bad JSON, invalid value, or network error
            print(f"  retry {odi_number} ({attempt + 1}/3): {exc}", flush=True)
            time.sleep(2 * (attempt + 1))
    return None


def run(conn, limit: int = 300, mock: bool = False, workers: int = 8):
    """Tag complaints that have no tag yet, so the step can be stopped and resumed.

    LLM calls run in a thread pool; database writes stay on the calling thread.
    """
    rows = conn.execute(
        """SELECT c.odi_number, c.summary FROM complaints c
           LEFT JOIN tags t USING (odi_number)
           WHERE t.odi_number IS NULL
           ORDER BY c.date_filed DESC, c.odi_number DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    tagger = "mock" if mock else os.environ["LLM_MODEL"]
    done = failed = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(_tag_with_retry, row["odi_number"], row["summary"], mock): row
            for row in rows
        }
        for future in as_completed(futures):
            row = futures[future]
            result = future.result()
            if result is None:
                failed += 1
                continue
            conn.execute(
                "INSERT OR REPLACE INTO tags VALUES (?,?,?,?,?,?,?,?)",
                (
                    row["odi_number"],
                    result["category"],
                    result["failure_type"],
                    result["severity"],
                    result["service_visit"],
                    result["out_of_pocket_usd"],
                    tagger,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
            conn.commit()
            done += 1
            if done % 25 == 0:
                print(f"  tagged {done}/{len(rows)}", flush=True)
    print(f"Tagged {done}, failed {failed}")
