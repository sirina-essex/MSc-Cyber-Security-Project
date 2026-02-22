from __future__ import annotations

import os
import importlib.util
from typing import List, Any
from dataclasses import dataclass


@dataclass
class ScenarioModule:
    scenario_id: str
    module: Any


class ScenarioError(ValueError):
    pass


def load_scenarios_from_dir(scenarios_dir: str) -> List[ScenarioModule]:

    if not os.path.isdir(scenarios_dir):
        raise ScenarioError(f"Scenarios directory not found: {scenarios_dir}")

    files = [
        f for f in os.listdir(scenarios_dir)
        if f.endswith(".py") and not f.startswith("__")
    ]

    if not files:
        print(f"[WARN] No Python script (.py) found on {scenarios_dir}")
        return []

    files.sort()

    scenarios: List[ScenarioModule] = []

    for filename in files:
        scenario_id = os.path.splitext(filename)[0].upper()
        path = os.path.join(scenarios_dir, filename)

        try:
            spec = importlib.util.spec_from_file_location(scenario_id, path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                if hasattr(mod, "execute"):
                    scenarios.append(ScenarioModule(scenario_id=scenario_id, module=mod))
                else:
                    print(f"[SKIP] {filename} ignored : no function 'execute(ctx)'.")
            else:
                print(f"[ERR] Unable to load specs for {filename}")

        except Exception as e:
            print(f"[ERR] Error on loading  {filename}: {e}")


    return scenarios