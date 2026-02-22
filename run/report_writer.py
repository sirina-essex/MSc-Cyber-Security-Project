import csv
from pathlib import Path
from typing import List
from run.models import AuditResult


class ReportWriter:
    def __init__(self, report_path: Path):
        self.report_path = report_path
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.results: List[AuditResult] = []

    def add_result(self, result: AuditResult):
        self.results.append(result)

    def save_report(self, run_id: str):
        with open(self.report_path, "w", newline='', encoding='utf-8-sig') as f:

            f.write("sep=;\n")

            writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)

            headers = ["RUN_ID", "SCENARIO_ID", "SCENARIO_NAME", "PERSONA", "HTTP_CODE", "VERDICT", "TIMESTAMP",
                       "DETAILS"]
            writer.writerow(headers)

            for item in self.results:
                writer.writerow([
                    run_id,
                    item.scenario_id,
                    item.name,
                    item.persona_id,
                    item.http_code,
                    item.verdict,
                    item.timestamp,
                    item.details
                ])