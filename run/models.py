from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import requests



@dataclass(frozen=True)
class TargetConfig:
    base_url: str
    request_timeout_seconds: int
    pause_between_actions_ms: int = 0


@dataclass(frozen=True)
class PersonaConfig:
    persona_id: str
    username: str
    password: str
    azure_email: Optional[str] = None


@dataclass(frozen=True)
class RunnerConfig:
    schema_version: str
    target: TargetConfig
    personas: List[PersonaConfig]
    scenarios_path: str
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None



@dataclass(frozen=True)
class HttpActionSpec:
    method: str
    endpoint: str
    headers: Dict[str, str]
    json_body: Optional[Dict[str, Any]]


@dataclass(frozen=True)
class AuthActionSpec:
    method: str
    login_endpoint: str


@dataclass(frozen=True)
class Action:
    action_id: str
    action_name: str
    action_type: str
    is_privileged_action: bool
    http: Optional[HttpActionSpec] = None
    auth: Optional[AuthActionSpec] = None


@dataclass(frozen=True)
class Scenario:
    schema_version: str
    scenario_id: str
    scenario_name: str
    description: str
    actions: List[Action]



@dataclass
class AuditResult:
    scenario_id: str
    name: str
    persona_id: str
    http_code: str
    verdict: str
    details: str
    timestamp: str


@dataclass
class AuthContext:

    persona_id: str

    session: Optional[requests.Session] = None

    is_authenticated: bool = False

    auth_error_type: Optional[str] = None
    auth_error_message_hash: Optional[str] = None
    auth_http_status_code: Optional[int] = None

    bearer_token: Optional[str] = None
    basket_id: Optional[int] = None
    user_email: Optional[str] = None