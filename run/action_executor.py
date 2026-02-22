from __future__ import annotations

import time
from typing import Optional, Tuple, Any, Dict

import requests

from run.attempt_record import (
    hash_error_message,
    hash_response_body_bytes,
    map_http_to_functional_outcome,
    hash_request_fingerprint,
)
from run.constants import (
    ACTION_TYPE_AUTH,
    ACTION_TYPE_HTTP_CALL,
    TECH_STATUS_CLIENT_ERROR,
    TECH_STATUS_CONNECTION_ERROR,
    TECH_STATUS_OK,
    TECH_STATUS_TIMEOUT,
)
from run.models import Action, AuthContext


def _join_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    p = path if path.startswith("/") else f"/{path}"
    return f"{base}{p}"


def compute_request_fingerprint_for_action(
    action: Action,
    json_body_override: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Step 6:
    - AUTH: do NOT include secrets, use a fixed redacted body
    - HTTP_CALL: include method + endpoint + headers + json_body (canonicalized)
      If json_body_override is provided, fingerprint is computed from it.
    """
    if action.action_type == ACTION_TYPE_AUTH:
        endpoint = action.auth.login_endpoint if action.auth else None
        payload: Dict[str, Any] = {
            "action_type": ACTION_TYPE_AUTH,
            "http_method": "POST",
            "endpoint": endpoint,
            "headers": {},
            "json_body": {"email": "<redacted>", "password": "<redacted>"},
        }
        return hash_request_fingerprint(payload)

    if action.action_type == ACTION_TYPE_HTTP_CALL and action.http is not None:
        body = json_body_override if json_body_override is not None else action.http.json_body
        payload = {
            "action_type": ACTION_TYPE_HTTP_CALL,
            "http_method": action.http.method.upper(),
            "endpoint": action.http.endpoint,
            "headers": dict(action.http.headers or {}),
            "json_body": body,
        }
        return hash_request_fingerprint(payload)

    return None


def _merge_headers(session: requests.Session, action_headers: Dict[str, str]) -> Dict[str, str]:
    """
    Merge session headers (including Authorization) with action headers from YAML.
    Action headers override session headers if same key.
    """
    merged: Dict[str, str] = {}
    # session.headers is case-insensitive dict-like, copy safely
    for k, v in dict(session.headers).items():
        if isinstance(k, str) and isinstance(v, str):
            merged[k] = v
        elif isinstance(k, str) and v is not None:
            merged[k] = str(v)

    for k, v in (action_headers or {}).items():
        merged[k] = v

    return merged


def execute_http_action(
    base_url: str,
    auth_ctx: AuthContext,
    action: Action,
    timeout_seconds: int,
    json_body_override: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[int], Optional[str], Optional[str], str, int, Optional[int], Optional[str], Optional[str]]:
    """
    Executes an HTTP_CALL action using auth_ctx.session.

    Returns:
      technical_status,
      http_status_code,
      error_type,
      error_message_hash,
      functional_outcome,
      response_time_ms,
      response_size_bytes,
      response_body_hash,
      request_fingerprint
    """
    if action.http is None:
        raise ValueError("HTTP_CALL action must have http spec")

    url = _join_url(base_url, action.http.endpoint)
    method = action.http.method.upper()

    body = json_body_override if json_body_override is not None else action.http.json_body

    request_fingerprint = compute_request_fingerprint_for_action(action, json_body_override=body)

    action_headers = dict(action.http.headers or {})
    headers = _merge_headers(auth_ctx.session, action_headers)

    start = time.perf_counter()
    try:
        resp = auth_ctx.session.request(
            method=method,
            url=url,
            headers=headers,
            json=body,
            timeout=timeout_seconds,
        )
        end = time.perf_counter()

        http_status_code = resp.status_code
        response_time_ms = int((end - start) * 1000)

        body_bytes = resp.content if resp.content is not None else b""
        response_size_bytes = len(body_bytes)
        response_body_hash = hash_response_body_bytes(body_bytes)

        technical_status = TECH_STATUS_OK
        functional_outcome = map_http_to_functional_outcome(http_status_code, technical_status)

        return (
            technical_status,
            http_status_code,
            None,
            None,
            functional_outcome,
            response_time_ms,
            response_size_bytes,
            response_body_hash,
            request_fingerprint,
        )

    except requests.Timeout as e:
        end = time.perf_counter()
        response_time_ms = int((end - start) * 1000)
        technical_status = TECH_STATUS_TIMEOUT
        return (
            technical_status,
            None,
            type(e).__name__,
            hash_error_message(str(e)),
            map_http_to_functional_outcome(None, technical_status),
            response_time_ms,
            None,
            None,
            request_fingerprint,
        )

    except requests.RequestException as e:
        end = time.perf_counter()
        response_time_ms = int((end - start) * 1000)
        technical_status = TECH_STATUS_CONNECTION_ERROR
        return (
            technical_status,
            None,
            type(e).__name__,
            hash_error_message(str(e)),
            map_http_to_functional_outcome(None, technical_status),
            response_time_ms,
            None,
            None,
            request_fingerprint,
        )

    except Exception as e:
        end = time.perf_counter()
        response_time_ms = int((end - start) * 1000)
        technical_status = TECH_STATUS_CLIENT_ERROR
        return (
            technical_status,
            None,
            type(e).__name__,
            hash_error_message(str(e)),
            map_http_to_functional_outcome(None, technical_status),
            response_time_ms,
            None,
            None,
            request_fingerprint,
        )