"""Deterministic tests for the portfolio checker; no network required."""

from __future__ import annotations

import copy
import unittest

from check_portfolio import inspect


SAMPLE = {
    "goal": "比较两种算法的可行性",
    "mode": "algorithm",
    "directions": [
        {"id": "D1", "lens": "几何模型"},
        {"id": "D2", "lens": "其他领域"},
    ],
    "sources": [
        {"id": "S1", "locator": "https://example.org/paper", "kind": "primary", "checked": True}
    ],
    "candidates": [
        {
            "id": "C1",
            "direction_id": "D1",
            "summary": "方案1",
            "mechanism": "利用几何约束反推模型",
            "mechanism_key": "constraint-solver",
            "evidence": [{"source_id": "S1", "supports": "可建立约束"}],
            "assumptions": ["图纸给出充足约束"],
            "failure_cases": ["缺少剖视图"],
            "verification": {
                "method": "同数据集运行",
                "criterion": "成功率大于基线",
                "result": "pass",
                "artifact": "runs/run1.log",
            },
        }
    ],
}


class PortfolioTests(unittest.TestCase):
    def test_valid_sample_reports_coverage_gap(self) -> None:
        result = inspect(copy.deepcopy(SAMPLE))
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["stats"]["uncovered_directions"], ["D2"])
        self.assertEqual(result["stats"]["families_with_checked_primary_evidence"], 1)
        self.assertEqual(result["stats"]["families_claiming_passed_tests"], 1)

    def test_duplicate_mechanism_is_not_counted_twice(self) -> None:
        data = copy.deepcopy(SAMPLE)
        duplicate = copy.deepcopy(data["candidates"][0])
        duplicate["id"] = "C2"
        duplicate["direction_id"] = "D2"
        data["candidates"].append(duplicate)
        result = inspect(data)
        self.assertEqual(result["stats"]["declared_mechanism_families"], 1)
        self.assertTrue(any("同一机制标识" in x for x in result["warnings"]))
        self.assertTrue(any("同一机制族" in x for x in result["warnings"]))

    def test_broken_source_reference_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["evidence"][0]["source_id"] = "missing"
        self.assertTrue(any("未定义来源" in x for x in inspect(data)["errors"]))

    def test_unsubstantiated_pass_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["verification"]["artifact"] = ""
        self.assertTrue(any("没有可复查" in x for x in inspect(data)["errors"]))

    def test_checked_must_be_boolean(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["sources"][0]["checked"] = "true"
        self.assertTrue(any("必须为 true 或 false" in x for x in inspect(data)["errors"]))

    def test_wrong_top_level_type(self) -> None:
        self.assertTrue(inspect(["unexpected"])["errors"])


if __name__ == "__main__":
    unittest.main()
