from pathlib import Path
from datetime import datetime

def with_daily_rollover(path: Path) -> Path:
    """Return a path with YYYYMMDD suffix; e.g., events_20250805.jsonl"""
    d = datetime.now().strftime("%Y%m%d")
    return path.with_name(f"{path.stem}_{d}{path.suffix}") 