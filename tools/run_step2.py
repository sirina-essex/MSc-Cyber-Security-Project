from __future__ import annotations

import os
from pathlib import Path

from run.runner import run_step2


def main() -> None:
    repo_root = Path(os.getcwd()).resolve()
    run_id = run_step2(repo_root=repo_root)
    print(f"STEP2 OK: run_id={run_id}")
    print(f"Outputs: runs/{run_id}/attempts.jsonl and runs/{run_id}/runner.log")


if __name__ == "__main__":
    main()
