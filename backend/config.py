import os
from pathlib import Path

# Base workspace path
BASE_DIR = Path(__file__).resolve().parent.parent

# Safe candidate resolution for data directory
def _resolve_data_dir() -> str:
    env_dir = os.getenv("ATLAS_DATA_DIR")
    if env_dir and os.path.exists(env_dir):
        return env_dir
    candidates = [
        BASE_DIR / "data",
        BASE_DIR / "hackathon-data" / "data",
        BASE_DIR / "hackathon-data",
        Path("data"),
        Path("hackathon-data") / "data",
    ]
    for cand in candidates:
        if (cand / "cuts.csv").is_file():
            return str(cand.resolve())
    return str((BASE_DIR / "data").resolve())

DATA_DIR = _resolve_data_dir()
DEFAULT_CUT = None
