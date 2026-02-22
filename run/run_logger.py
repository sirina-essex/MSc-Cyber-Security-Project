from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RunLogger:
    log_path: Path

    def __post_init__(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_line(self, line: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line.rstrip("\n") + "\n")

    def run_start(self, run_id: str, base_url: str, timeout_seconds: int) -> None:
        self._write_line(f"[RUN_START] run_id={run_id} base_url={base_url} timeout={timeout_seconds}s")

    def scenarios_loaded(self, count: int, scenario_ids: list[str]) -> None:
        self._write_line(f"[SCENARIOS_LOADED] count={count} scenarios={scenario_ids}")

    def persona_block_start(self, scenario_id: str, persona_id: str) -> None:
        self._write_line(f"[PERSONA_BLOCK_START] scenario_id={scenario_id} persona_id={persona_id}")

    def action_start(self, attempt_id: str, scenario_id: str, persona_id: str, action_id: str) -> None:
        self._write_line(
            f"[ACTION_START] attempt_id={attempt_id} scenario_id={scenario_id} persona_id={persona_id} action_id={action_id}"
        )

    def action_end(
        self,
        attempt_id: str,
        technical_status: str,
        http_status_code: Optional[int],
        functional_outcome: str,
    ) -> None:
        self._write_line(
            f"[ACTION_END] attempt_id={attempt_id} technical_status={technical_status} http_status_code={http_status_code} functional_outcome={functional_outcome}"
        )

    def run_end(self, status: str, attempts_count: int) -> None:
        self._write_line(f"[RUN_END] status={status} attempts_count={attempts_count}")
