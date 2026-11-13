"""Offline tests on synthetic records: parsing, JSON validation, label mapping, full run."""
import json
from pathlib import Path

import pytest

from src import config, db, evaluate, fetch, report, tag

SYNTHETIC = [
    {"odiNumber": 1, "crash": True, "fire": False, "numberOfInjuries": 1,
     "dateOfIncident": "01/05/2024", "dateComplaintFiled": "01/20/2024",
     "components": "STEERING, SERVICE BRAKES",
     "summary": "Steering locked on the highway and the car hit a barrier. Crash reported."},
    {"odiNumber": 2, "crash": False, "fire": False, "numberOfInjuries": 0,
     "dateOfIncident": "02/10/2024", "dateComplaintFiled": "02/12/2024",
     "components": "ELECTRICAL SYSTEM",
     "summary": "Center screen went black. Service center replaced the unit for $1,450."},
    {"odiNumber": 3, "crash": False, "fire": False, "numberOfInjuries": 0,
     "dateOfIncident": "02/15/2024", "dateComplaintFiled": "03/01/2024",
     "components": "SUSPENSION",
     "summary": "Front brake noise at low speed."},
    {"odiNumber": 4, "crash": False, "fire": False, "numberOfInjuries": 0,
     "dateOfIncident": None, "dateComplaintFiled": "03/02/2024",
     "components": "UNKNOWN OR OTHER", "summary": ""},
]


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "test.db")
    fetch.load(c, SYNTHETIC, "MODEL 3", 2023)
    return c


def test_load_skips_empty_summaries_and_converts_dates(conn):
    rows = conn.execute("SELECT * FROM complaints ORDER BY odi_number").fetchall()
    assert len(rows) == 3
    assert rows[0]["date_filed"] == "2024-01-20"
    assert rows[0]["crash"] == 1


def test_validate_accepts_good_json_and_rejects_bad_values():
    good = json.dumps({"category": "Brakes", "failure_type": "Hardware failure",
                       "severity": "Drivability", "service_visit": True,
                       "out_of_pocket_usd": 300})
    assert tag.validate("Here you go: " + good)["out_of_pocket_usd"] == 300.0
    with pytest.raises(ValueError):
        tag.validate(good.replace("Brakes", "Engine"))
    with pytest.raises(ValueError):
        tag.validate("no json here")


def test_nhtsa_mapping():
    assert config.map_nhtsa_components("STEERING, SERVICE BRAKES") == {"Steering", "Brakes"}
    assert config.map_nhtsa_components("UNKNOWN OR OTHER") == {"Other"}


def test_full_run_with_mock_tagger(conn, tmp_path, monkeypatch):
    tag.run(conn, mock=True)
    ev = evaluate.run(conn)
    assert ev["n"] == 3
    # complaint 3 is tagged Brakes from its text but NHTSA says Suspension
    assert ev["agreement_pct"] == pytest.approx(66.7)
    monkeypatch.setattr(report, "REPORT_DIR", tmp_path)
    report.run(conn)
    assert "Agreement" in (tmp_path / "report.md").read_text() or "agrees" in (tmp_path / "report.md").read_text()
    assert (tmp_path / "volume_by_category.png").exists()
