from __future__ import annotations

import os
import time
import urllib3
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from run.config_loader import load_runner_config
from run.id_utils import generate_run_id
from run.scenario_loader import load_scenarios_from_dir

from run.attempt_writer import AttemptWriter, CsvAttemptWriter
from run.report_writer import ReportWriter
from run.context import ScenarioContext

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class RunnerPaths:
    repo_root: Path
    config_path: Path
    scenarios_dir: Path
    runs_root: Path


def build_paths(repo_root: Path) -> RunnerPaths:
    return RunnerPaths(
        repo_root=repo_root,
        config_path=repo_root / "config" / "config.yaml",
        scenarios_dir=repo_root / "scenarios",
        runs_root=repo_root / "runs",
    )


def run_audit(repo_root: Optional[Path] = None, config_filename: str = "config.yaml") -> str:

    if repo_root is None:
        repo_root = Path(os.getcwd()).resolve()

    paths = build_paths(repo_root)
    if config_filename != "config.yaml":
        paths.config_path = paths.config_path.parent / config_filename

    print(f"[*] Configuration loading : {paths.config_path}")
    cfg = load_runner_config(str(paths.config_path))

    print(f"[*] Scenario loading   : {paths.scenarios_dir}")
    scenarios = load_scenarios_from_dir(str(paths.scenarios_dir))

    if not scenarios:
        print("[!] No scenario loaded.")
        return "NO_RUN"

    run_id = generate_run_id()
    run_dir = paths.runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Starting RUN_ID     : {run_id}")
    print(f"[*] Result folder    : {run_dir}")

    filename_jsonl = f"attempts_{run_id}.jsonl"
    filename_csv = f"attempts_{run_id}.csv"
    filename_obs = f"observations_{run_id}.csv"

    json_writer = AttemptWriter(jsonl_path=run_dir / filename_jsonl)
    csv_writer = CsvAttemptWriter(csv_path=run_dir / filename_csv)
    report_writer = ReportWriter(report_path=run_dir / filename_obs)

    ctx = ScenarioContext(
        config=cfg,
        run_id=run_id,
        json_writer=json_writer,
        csv_writer=csv_writer,
        report_writer=report_writer
    )

    start_time = time.time()
    for sc in scenarios:
        print(f"\n>>> Scenario : {sc.scenario_id}")
        try:
            sc.module.execute(ctx)
        except Exception as e:
            print(f"[CRITICAL] Error on {sc.scenario_id} : {e}")
            import traceback
            traceback.print_exc()

    duration = time.time() - start_time

    report_writer.save_report(run_id)

    print(f"\n[*] Run ended in {duration:.2f}s")
    print(f"[*] Board (Observations) : {run_dir / filename_obs}")
    print(f"[*] Technical Logs  (CSV)          : {run_dir / filename_csv}")
    print(f"[*] Technical Logs (JSONL)        : {run_dir / filename_jsonl}")

    return run_id


if __name__ == "__main__":
    run_audit(config_filename="config.yaml")