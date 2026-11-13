"""Project settings: which vehicles to pull and the tagging taxonomy."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "complaints.db"
REPORT_DIR = ROOT / "reports"

MAKE = "TESLA"
MODELS = ["MODEL 3", "MODEL Y"]
MODEL_YEARS = [2021, 2022, 2023, 2024]

NHTSA_URL = "https://api.nhtsa.gov/complaints/complaintsByVehicle"

# Service-oriented taxonomy the LLM must choose from.
CATEGORIES = [
    "Driver assistance & software",
    "Steering",
    "Brakes",
    "Suspension, wheels & tires",
    "Battery, charging & propulsion",
    "Electrical & electronics",
    "Body, doors & glass",
    "Restraints & seats",
    "Other",
]

FAILURE_TYPES = [
    "Hardware failure",
    "Software or calibration",
    "Build quality or fit",
    "Wear or premature wear",
    "Unclear",
]

SEVERITIES = ["Safety-critical", "Drivability", "Inconvenience"]

# Maps NHTSA's own component labels (keyword match) onto the taxonomy above.
# Used only for evaluation: the LLM never sees NHTSA's labels.
NHTSA_KEYWORD_MAP = [
    ("LANE DEPARTURE", "Driver assistance & software"),
    ("FORWARD COLLISION", "Driver assistance & software"),
    ("BACK OVER", "Driver assistance & software"),
    ("VEHICLE SPEED CONTROL", "Driver assistance & software"),
    ("ELECTRONIC STABILITY", "Driver assistance & software"),
    ("STEERING", "Steering"),
    ("BRAKE", "Brakes"),
    ("SUSPENSION", "Suspension, wheels & tires"),
    ("WHEEL", "Suspension, wheels & tires"),
    ("TIRE", "Suspension, wheels & tires"),
    ("PROPULSION", "Battery, charging & propulsion"),
    ("POWER TRAIN", "Battery, charging & propulsion"),
    ("ENGINE", "Battery, charging & propulsion"),
    ("ELECTRICAL", "Electrical & electronics"),
    ("LIGHTING", "Electrical & electronics"),
    ("STRUCTURE", "Body, doors & glass"),
    ("VISIBILITY", "Body, doors & glass"),
    ("LATCHES", "Body, doors & glass"),
    ("AIR BAG", "Restraints & seats"),
    ("SEAT", "Restraints & seats"),
]


def map_nhtsa_components(components: str) -> set[str]:
    """Translate an NHTSA component string into the set of taxonomy categories it covers."""
    text = (components or "").upper()
    mapped = {cat for keyword, cat in NHTSA_KEYWORD_MAP if keyword in text}
    return mapped or {"Other"}
