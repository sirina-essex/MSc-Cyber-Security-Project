from __future__ import annotations

from datetime import datetime, timezone


def generate_run_id() -> str:
    # Example: RUN_20260204T153012Z
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"RUN_{ts}"


def format_attempt_id(run_id: str, attempt_seq: int) -> str:
    # Example: RUN_...__A0001
    return f"{run_id}__A{attempt_seq:04d}"
