"""Step 1: pull complaint records from the public NHTSA API into SQLite."""
import time
from datetime import datetime

import requests

from .config import MAKE, MODELS, MODEL_YEARS, NHTSA_URL


def _iso(date_str):
    """NHTSA dates arrive as MM/DD/YYYY; store ISO so SQL can sort and group them."""
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").date().isoformat()
    except (TypeError, ValueError):
        return None


def parse_record(rec: dict, model: str, year: int):
    summary = (rec.get("summary") or "").strip()
    if not summary:
        return None
    return (
        int(rec["odiNumber"]),
        model,
        year,
        _iso(rec.get("dateOfIncident")),
        _iso(rec.get("dateComplaintFiled")),
        int(bool(rec.get("crash"))),
        int(bool(rec.get("fire"))),
        int(rec.get("numberOfInjuries") or 0),
        rec.get("components") or "",
        summary,
    )


def fetch_one(model: str, year: int) -> list[dict]:
    resp = requests.get(
        NHTSA_URL,
        params={"make": MAKE, "model": model, "modelYear": year},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def load(conn, records: list[dict], model: str, year: int) -> int:
    rows = [r for r in (parse_record(rec, model, year) for rec in records) if r]
    conn.executemany(
        "INSERT OR IGNORE INTO complaints VALUES (?,?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    return len(rows)


def run(conn):
    for model in MODELS:
        for year in MODEL_YEARS:
            records = fetch_one(model, year)
            n = load(conn, records, model, year)
            print(f"{model} {year}: {n} complaints")
            time.sleep(1)  # be polite to a public API
    total = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    print(f"Total in database: {total}")
