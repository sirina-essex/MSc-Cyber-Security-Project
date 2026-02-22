from __future__ import annotations

import os
from typing import Any, Dict, List

import yaml

from run.constants import SCHEMA_VERSION_CONFIG
from run.models import PersonaConfig, RunnerConfig, TargetConfig


class ConfigError(ValueError):
    pass


def _require(d: Dict[str, Any], key: str, where: str) -> Any:
    if key not in d:
        raise ConfigError(f"Missing required key '{key}' in {where}")
    return d[key]


def load_runner_config(path: str) -> RunnerConfig:
    if not os.path.isfile(path):
        raise ConfigError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a mapping (YAML dict)")


    schema_version = raw.get("schema_version")
    if schema_version != SCHEMA_VERSION_CONFIG:
        pass

    azure_tenant_id = raw.get("azure_tenant_id")
    azure_client_id = raw.get("azure_client_id")

    target_raw = _require(raw, "target", "config root")
    if not isinstance(target_raw, dict):
        raise ConfigError("config.target must be a mapping")

    base_url = _require(target_raw, "base_url", "config.target")
    timeout = target_raw.get("request_timeout_seconds", 20)
    pause = target_raw.get("pause_between_actions_ms", 0)

    if not isinstance(base_url, str) or not base_url.strip():
        raise ConfigError("target.base_url must be a non-empty string")

    target = TargetConfig(
        base_url=base_url.rstrip("/"),
        request_timeout_seconds=int(timeout),
        pause_between_actions_ms=int(pause),
    )

    # 4. Loading Personas
    personas_raw = _require(raw, "personas", "config root")
    if not isinstance(personas_raw, list) or len(personas_raw) == 0:
        raise ConfigError("config.personas must be a non-empty list")

    personas: List[PersonaConfig] = []
    seen_persona_ids = set()

    for idx, p in enumerate(personas_raw):
        where = f"config.personas[{idx}]"
        if not isinstance(p, dict):
            raise ConfigError(f"{where} must be a mapping")

        persona_id = _require(p, "persona_id", where)
        username = _require(p, "username", where)
        password = _require(p, "password", where)

        azure_email = p.get("azure_email")

        if not isinstance(persona_id, str) or not persona_id.strip():
            raise ConfigError(f"{where}.persona_id must be a non-empty string")
        if persona_id in seen_persona_ids:
            raise ConfigError(f"Duplicate persona_id detected: {persona_id}")
        seen_persona_ids.add(persona_id)

        personas.append(PersonaConfig(
            persona_id=persona_id,
            username=username,
            password=password,
            azure_email=azure_email  #
        ))

    scenarios_path = _require(raw, "scenarios_path", "config root")

    return RunnerConfig(
        schema_version=str(schema_version),
        target=target,
        personas=personas,
        scenarios_path=scenarios_path,
        azure_tenant_id=azure_tenant_id,
        azure_client_id=azure_client_id
    )