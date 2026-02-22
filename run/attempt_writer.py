from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from run.attempt_record import AttemptRecord, validate_attempt_record_minimal


@dataclass
class AttemptWriter:
    jsonl_path: Path

    def __post_init__(self) -> None:
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: AttemptRecord) -> None:
        validate_attempt_record_minimal(record)
        # Sérialisation en JSON compact
        line = json.dumps(record.to_dict(), ensure_ascii=False, separators=(",", ":"))
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


@dataclass
class CsvAttemptWriter:
    csv_path: Path

    def __post_init__(self) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._headers_written = self.csv_path.exists() and self.csv_path.stat().st_size > 0

    def write(self, record: AttemptRecord) -> None:
        validate_attempt_record_minimal(record)
        data = record.to_dict()

        with open(self.csv_path, "a", newline='', encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=data.keys(),
                delimiter=";",
                quoting=csv.QUOTE_MINIMAL
            )

            if not self._headers_written:
                writer.writeheader()
                self._headers_written = True

            writer.writerow(data)