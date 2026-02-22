from __future__ import annotations

import os
from pathlib import Path

from run.runner import run_step3


def main() -> None:
    repo_root = Path(os.getcwd()).resolve()
    run_id = run_step3(repo_root=repo_root, config_filename="config.local.yaml")
    print(f"LOCAL RUN OK: {run_id}")
    print(f"Outputs: runs/{run_id}/attempts.jsonl and runs/{run_id}/runner.log")


if __name__ == "__main__":
    main()
