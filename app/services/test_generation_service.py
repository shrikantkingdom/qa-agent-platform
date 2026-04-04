import csv
import json
from pathlib import Path
from typing import List

from app.config.settings import settings
from app.models.schemas import TestCase, TestType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TestGenerationService:
    def parse_test_cases(self, raw: dict) -> List[TestCase]:
        test_cases: List[TestCase] = []
        for item in raw.get("test_cases", []):
            try:
                test_type = TestType(item.get("test_type", "Happy Path"))
            except ValueError:
                test_type = TestType.HAPPY_PATH

            test_cases.append(
                TestCase(
                    test_id=item.get("test_id", f"TC-{len(test_cases) + 1:03d}"),
                    scenario=item.get("scenario", ""),
                    steps=item.get("steps", []),
                    expected_result=item.get("expected_result", ""),
                    test_type=test_type,
                    priority=item.get("priority", "Medium"),
                    tags=item.get("tags", []),
                )
            )
        return test_cases

    def export_as_csv(self, test_cases: List[TestCase], jira_id: str) -> str:
        path = Path(settings.testcases_path) / f"{jira_id}_testcases.csv"
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = ["Test ID", "Type", "Priority", "Scenario", "Steps", "Expected Result", "Tags"]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for tc in test_cases:
                writer.writerow(
                    {
                        "Test ID": tc.test_id,
                        "Type": tc.test_type.value,
                        "Priority": tc.priority,
                        "Scenario": tc.scenario,
                        "Steps": " | ".join(tc.steps),
                        "Expected Result": tc.expected_result,
                        "Tags": ", ".join(tc.tags),
                    }
                )

        logger.info(f"Test cases → CSV: {path}")
        return str(path)

    def export_as_json(self, test_cases: List[TestCase], jira_id: str) -> str:
        path = Path(settings.testcases_path) / f"{jira_id}_testcases.json"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as fh:
            json.dump([tc.model_dump() for tc in test_cases], fh, indent=2, default=str)

        logger.info(f"Test cases → JSON: {path}")
        return str(path)


test_generation_service = TestGenerationService()
