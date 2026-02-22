from __future__ import annotations

import os

from runner.config_loader import load_runner_config
from runner.scenario_loader import load_scenarios_from_dir


def main() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = os.path.join(repo_root, "config", "config.yaml")

    cfg = load_runner_config(config_path)
    print("CONFIG OK")
    print(f"  base_url: {cfg.target.base_url}")
    print(f"  timeout: {cfg.target.request_timeout_seconds}s")
    print(f"  personas: {[p.persona_id for p in cfg.personas]}")
    print(f"  scenarios_path: {cfg.scenarios_path}")

    scenarios_dir = os.path.join(repo_root, cfg.scenarios_path)
    scenarios = load_scenarios_from_dir(scenarios_dir)
    print("SCENARIOS OK")
    print(f"  scenarios loaded: {[s.scenario_id for s in scenarios]}")
    for s in scenarios:
        print(f"  - {s.scenario_id} actions: {[a.action_id for a in s.actions]}")

    print("STEP 1 VALIDATION SUCCESS")


if __name__ == "__main__":
    main()
