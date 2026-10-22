"""Configuration and environment management for ZentroMart VoiceOps 2026."""
import os
import datetime
from pathlib import Path

# Paths
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

# Locate dataset root
candidate_dataset_paths = [
    PROJECT_ROOT / "Capstone_Project_Dataset_FTTT_2026" / "Capstone_Project_Dataset_FTTT_2026",
    PROJECT_ROOT / "Capstone_Project_Dataset_FTTT_2026",
    PROJECT_ROOT,
]

DATASET_ROOT = None
for p in candidate_dataset_paths:
    if (p / "kb").exists() and (p / "data").exists():
        DATASET_ROOT = p
        break

if DATASET_ROOT is None:
    DATASET_ROOT = candidate_dataset_paths[0]

KB_DIR = DATASET_ROOT / "kb"
DATA_DIR = DATASET_ROOT / "data"
PRACTICE_DIR = DATASET_ROOT / "practice"
TOOLS_DIR = DATASET_ROOT / "tools"

# Frozen Reference Date
REFERENCE_DATE = datetime.date(2026, 10, 20)
TODAY_STR = "2026-10-20"

# Known Holidays (from holidays.csv)
HOLIDAYS = {
    datetime.date(2026, 8, 15),  # Independence Day
    datetime.date(2026, 10, 2),  # Gandhi Jayanti
    datetime.date(2026, 10, 19), # Warehouse closure (festival)
    datetime.date(2026, 11, 9),  # Warehouse closure (festival)
}

# API Configuration
GNANI_API_KEY = os.environ.get("GNANI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))

# Voice defaults
DEFAULT_VOICE = "Kaveri"
DEFAULT_TTS_MODEL = "timbre-v2.5"
DEFAULT_STT_LANG = "en-IN"
DEFAULT_TTS_LANG = "en-IN"

def is_business_day(d: datetime.date) -> bool:
    """Monday (0) through Saturday (5) are business days. Sunday (6) is not.
    Warehouse holidays are also excluded."""
    if d.weekday() == 6:  # Sunday
        return False
    if d in HOLIDAYS:
        return False
    return True

def add_business_days(start_date: datetime.date, n: int) -> datetime.date:
    """Add n business days to start_date."""
    cur = start_date
    added = 0
    while added < n:
        cur += datetime.timedelta(days=1)
        if is_business_day(cur):
            added += 1
    return cur

def get_refund_window(start_date: datetime.date, method: str):
    """Calculate refund date range according to REF-2 and business days."""
    method = (method or "").lower()
    if "wallet" in method:
        return "Instant, within 2 hours of initiation."
    elif "upi" in method:
        d1 = add_business_days(start_date, 1)
        d3 = add_business_days(start_date, 3)
        return (d1, d3)
    elif "netbanking" in method or "net banking" in method:
        d3 = add_business_days(start_date, 3)
        d5 = add_business_days(start_date, 5)
        return (d3, d5)
    elif "card" in method:
        d5 = add_business_days(start_date, 5)
        d7 = add_business_days(start_date, 7)
        return (d5, d7)
    elif "cod" in method or "bank" in method:
        d5 = add_business_days(start_date, 5)
        d7 = add_business_days(start_date, 7)
        return (d5, d7)
    else:
        d5 = add_business_days(start_date, 5)
        d7 = add_business_days(start_date, 7)
        return (d5, d7)
