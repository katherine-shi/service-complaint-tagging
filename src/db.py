"""SQLite schema and connection helper."""
import sqlite3
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS complaints (
    odi_number      INTEGER PRIMARY KEY,
    model           TEXT NOT NULL,
    model_year      INTEGER NOT NULL,
    date_incident   TEXT,
    date_filed      TEXT,
    crash           INTEGER,
    fire            INTEGER,
    injuries        INTEGER,
    nhtsa_components TEXT,
    summary         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tags (
    odi_number      INTEGER PRIMARY KEY REFERENCES complaints(odi_number),
    category        TEXT NOT NULL,
    failure_type    TEXT NOT NULL,
    severity        TEXT NOT NULL,
    service_visit   INTEGER NOT NULL,
    out_of_pocket_usd REAL,
    tagger          TEXT NOT NULL,
    tagged_at       TEXT NOT NULL
);
"""


def connect(path=None) -> sqlite3.Connection:
    path = path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
