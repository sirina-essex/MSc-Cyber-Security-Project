from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from run.constants import (
    FUNC_OUTCOME_ALLOW,
    FUNC_OUTCOME_DENY,
    FUNC_OUTCOME_UNKNOWN,
    SCHEMA_VERSION_ATTEMPT_RECORD,
    TARGET_SYSTEM,
    TECH_STATUS_OK,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def hash_error_message(msg: str) -> str:
    normalized = " ".join(msg.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_response_body_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_request_fingerprint(payload: Dict[str, Any]) -> str:
    canon = canonical_json(payload)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def map_http_to_functional_outcome(http_status_code: Optional[int], technical_status: str) -> str:
    if technical_status != TECH_STATUS_OK:
        return FUNC_OUTCOME_UNKNOWN
    if http_status_code is None:
        return FUNC_OUTCOME_UNKNOWN
    if 200 <= http_status_code <= 299:
        return FUNC_OUTCOME_ALLOW
    if http_status_code in (401, 403):
        return FUNC_OUTCOME_DENY
    return FUNC_OUTCOME_UNKNOWN


@dataclass(frozen=True)
class AttemptRecord:
    schema_version: str

    run_id: str
    attempt_seq: int
    attempt_id: str

    scenario_id: str
    persona_id: str
    action_id: str
    action_name: str
    action_type: str

    target_system: str
    endpoint: Optional[str]
    http_method: Optional[str]

    ts_start_utc: str
    ts_end_utc: str
    duration_ms: int

    technical_status: str
    functional_outcome: str

    http_status_code: Optional[int]
    error_type: Optional[str]
    error_message_hash: Optional[str]

    response_size_bytes: Optional[int]
    response_body_hash: Optional[str]

    request_fingerprint: Optional[str]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "attempt_seq": self.attempt_seq,
            "attempt_id": self.attempt_id,
            "scenario_id": self.scenario_id,
            "persona_id": self.persona_id,
            "action_id": self.action_id,
            "action_name": self.action_name,
            "action_type": self.action_type,
            "target_system": self.target_system,
            "endpoint": self.endpoint,
            "http_method": self.http_method,
            "ts_start_utc": self.ts_start_utc,
            "ts_end_utc": self.ts_end_utc,
            "duration_ms": self.duration_ms,
            "technical_status": self.technical_status,
            "functional_outcome": self.functional_outcome,
            "http_status_code": self.http_status_code,
            "error_type": self.error_type,
            "error_message_hash": self.error_message_hash,
            "response_size_bytes": self.response_size_bytes,
            "response_body_hash": self.response_body_hash,
            "request_fingerprint": self.request_fingerprint,
        }


def validate_attempt_record_minimal(rec: AttemptRecord) -> None:
    if rec.schema_version != SCHEMA_VERSION_ATTEMPT_RECORD:
        raise ValueError("Invalid AttemptRecord schema_version")
    if rec.target_system != TARGET_SYSTEM:
        raise ValueError("Invalid target_system")
    if rec.attempt_seq < 1:
        raise ValueError("attempt_seq must be >= 1")
    if not rec.run_id or not rec.attempt_id:
        raise ValueError("run_id and attempt_id must be non-empty")
    if not rec.scenario_id or not rec.persona_id or not rec.action_id:
        raise ValueError("scenario_id/persona_id/action_id must be non-empty")
    if rec.duration_ms < 0:
        raise ValueError("duration_ms must be >= 0")
    if rec.response_size_bytes is not None and rec.response_size_bytes < 0:
        raise ValueError("response_size_bytes must be >= 0 if provided")