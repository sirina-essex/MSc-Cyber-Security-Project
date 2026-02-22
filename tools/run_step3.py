from __future__ import annotations

import os
from pathlib import Path

from run.runner import run_step3


def main() -> None:
    repo_root = Path(os.getcwd()).resolve()

    # Choose one:
    run_id = run_step3(repo_root=repo_root, config_filename="config.sir01.yaml")
    # run_id = run_step3(repo_root=repo_root, config_filename="config.sir02.yaml")

    print(f"RUN OK: {run_id}")
    print(f"Outputs: runs/{run_id}/attempts.jsonl and runs/{run_id}/runner.log")


if __name__ == "__main__":
    main()
