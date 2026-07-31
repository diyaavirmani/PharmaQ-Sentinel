SPECIALIST_NAMES = {
    "qa": "QA Risk Agent",
    "manufacturing": "Manufacturing Investigator",
    "packaging": "Packaging and Supplier Agent",
    "pv": "Pharmacovigilance Agent",
}

MAX_SPECIALIST_PASSES = 2
MAX_REVISION_REQUESTS_PER_SPECIALIST = 1
SPECIALIST_TIMEOUT_SECONDS = 8
PROVIDER_NAME = "deterministic-war-room"
MODEL_NAME = "quality-war-room-rules-v1"

PROHIBITED_FINALITY_TERMS = (
    "confirmed root cause",
    "final root cause",
    "caused by",
    "proves causation",
    "authorized decision",
)
