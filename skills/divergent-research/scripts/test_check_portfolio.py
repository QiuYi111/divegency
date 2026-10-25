"""Deterministic tests for the portfolio checker; no network required."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from check_portfolio import inspect


SAMPLE = {
    "goal": "比较两种算法的可行性",
    "mode": "algorithm",
    "budget": "standard",
    "probes": [
        {"id": "P1", "intervention": "删掉剖视图", "question": "成功率是否显著下降"},
    ],
    "directions": [
        {"id": "D1", "lens": "几何约束", "axis": "信息来源"},
        {"id": "D2", "lens": "学习先验", "axis": "信息来源"},
    ],
    "sources": [
        {
            "id": "S1",
            "locator": "https://example.org/paper",
            "kind": "primary",
            "checked": True,
            "where": "§4.2",
            "quote": "constraint propagation improves recall on partial drawings",
        },
        {"id": "S2", "locator": "https://example.org/blog", "kind": "secondary", "checked": False},
    ],
    "dead_ends": [{"route": "纯端到端回归", "why": "在缺视图样本上误差爆炸"}],
    "candidates": [
        {
            "id": "C1",
            "direction_id": "D1",
            "summary": "方案1",
            "mechanism": "用几何约束反推模型",
            "mechanism_key": "constraint-solver",
            "predictions": {"P1": "down"},
            "differentiation": [
                {"vs": "C2", "observation": "只给主视图时 C1 预测无解，C2 仍给出近似体",
                 "prediction_self": "无解", "prediction_other": "给出近似体"}
            ],
            "evidence": [{"source_id": "S1", "supports": "约束传播能提升召回"}],
            "assumptions": ["图纸给出充足约束"],
            "failure_cases": ["缺少剖视图"],
            "verification": {
                "method": "同数据集运行",
                "criterion": "成功率高于基线",
                "result": "pass",
                "artifact": "https://example.org/runs/run1.log",
                "evaluator": "independent",
                "rerun": "python run.py --seed 1",
            },
        },
        {
            "id": "C2",
            "direction_id": "D2",
            "summary": "方案2",
            "mechanism": "从大量图纸学习先验",
            "mechanism_key": "learned-prior",
            "predictions": {"P1": "no-change"},
            "differentiation": [
                {"vs": "C1", "observation": "只给主视图时 C2 仍给出近似体，误差上升但不失败",
                 "prediction_self": "给出近似体", "prediction_other": "无解"}
            ],
            "evidence": [{"source_id": "S2", "supports": "学习先验可用于补全"}],
            "assumptions": ["训练分布覆盖目标图纸"],
            "failure_cases": ["分布外零件"],
            "verification": {
                "method": "尚未运行",
                "criterion": "成功率高于基线",
                "result": "not-run",
                "artifact": "",
                "evaluator": "self",
            },
        },
    ],
    "finalists": ["C1", "C2"],
}


class PortfolioTests(unittest.TestCase):
    def test_valid_sample_passes(self) -> None:
        result = inspect(copy.deepcopy(SAMPLE))
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["stats"]["declared_mechanism_families"], 2)
        self.assertEqual(result["stats"]["families_with_checked_primary_evidence"], 1)
        self.assertEqual(result["stats"]["distinct_prediction_signatures"], 2)
        self.assertEqual(result["stats"]["dead_ends"], 1)

    def test_exactly_renamed_mechanism_description_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        clone = copy.deepcopy(data["candidates"][0])
        clone["id"] = "C3"
        clone["direction_id"] = "D2"
        clone["mechanism_key"] = "geometric-inversion"
        data["candidates"].append(clone)
        result = inspect(data)
        self.assertTrue(any("相同机制描述" in x for x in result["errors"]))
        self.assertTrue(any("无法区分" in x for x in result["warnings"]))

    def test_equal_probe_outcomes_do_not_prove_same_mechanism(self) -> None:
        data = copy.deepcopy(SAMPLE)
        # Two genuine methods can both lose accuracy when a sectional view is removed.
        data["candidates"][1]["predictions"]["P1"] = "down"
        result = inspect(data)
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("无法区分" in x for x in result["warnings"]))

    def test_empty_predictions_rejected_when_probes_exist(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][1]["predictions"] = {}
        self.assertTrue(any("缺少判别问题" in x for x in inspect(data)["errors"]))

    def test_partial_predictions_rejected_when_probes_exist(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["probes"].append({"id": "P2", "intervention": "换新图纸", "question": "误差是否增加"})
        self.assertTrue(any("缺少判别问题" in x for x in inspect(data)["errors"]))

    def test_checked_without_quote_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["sources"][0]["quote"] = ""
        self.assertTrue(any("quote" in x for x in inspect(data)["errors"]))

    def test_checked_without_where_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["sources"][0]["where"] = ""
        self.assertTrue(any("where" in x for x in inspect(data)["errors"]))

    def test_pass_with_missing_local_artifact_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["verification"]["artifact"] = "runs/missing.log"
        with tempfile.TemporaryDirectory() as tmp:
            result = inspect(data, root=Path(tmp))
        self.assertTrue(any("不存在" in x for x in result["errors"]))

    def test_pass_with_existing_local_artifact_accepted(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["verification"]["artifact"] = "runs/run1.log"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runs").mkdir()
            (root / "runs" / "run1.log").write_text("ok", encoding="utf-8")
            result = inspect(data, root=root)
        self.assertFalse(any("不存在" in x for x in result["errors"]))

    def test_directory_is_not_a_pass_artifact(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["verification"]["artifact"] = "."
        with tempfile.TemporaryDirectory() as tmp:
            result = inspect(data, root=Path(tmp))
        self.assertTrue(any("不是文件" in x for x in result["errors"]))

    def test_finalists_need_bidirectional_witness(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][1]["differentiation"] = []
        result = inspect(data)
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("尚不能确认原理不同" in x for x in result["warnings"]))
        self.assertEqual(result["stats"]["pairs_with_claimed_witness"], 0)

    def test_direction_can_contribute_without_unique_candidate(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["directions"].append({"id": "D3", "lens": "跨领域验证"})
        data["candidates"][0]["contributor_direction_ids"] = ["D3"]
        result = inspect(data)
        self.assertNotIn("D3", result["stats"]["uncovered_directions"])

    def test_undefined_contributing_direction_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["contributor_direction_ids"] = ["D404"]
        self.assertTrue(any("contributor_direction_ids" in x for x in inspect(data)["errors"]))

    def test_pass_without_checked_evidence_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["evidence"] = [{"source_id": "S2", "supports": "二手转述"}]
        self.assertTrue(any("没有已核实" in x for x in inspect(data)["errors"]))

    def test_broken_source_reference_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["evidence"][0]["source_id"] = "missing"
        self.assertTrue(any("未定义来源" in x for x in inspect(data)["errors"]))

    def test_unknown_probe_prediction_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["predictions"] = {"P9": "down"}
        self.assertTrue(any("未定义判别问题" in x for x in inspect(data)["errors"]))

    def test_dead_end_needs_reason(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["dead_ends"][0]["why"] = ""
        self.assertTrue(any("dead_ends" in x for x in inspect(data)["errors"]))

    def test_identical_predictions_are_not_a_witness(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["differentiation"][0]["prediction_other"] = "无解"
        self.assertTrue(any("不构成判别" in x for x in inspect(data)["errors"]))

    def test_probe_without_predictions_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        del data["candidates"][1]["predictions"]
        self.assertTrue(any("都必须给出预测" in x for x in inspect(data)["errors"]))

    def test_empty_artifact_file_rejected(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["candidates"][0]["verification"]["artifact"] = "runs/empty.log"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runs").mkdir()
            (root / "runs" / "empty.log").write_text("", encoding="utf-8")
            result = inspect(data, root=root)
        self.assertTrue(any("空文件" in x for x in result["errors"]))

    def test_snapshot_must_contain_quote(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["sources"][0]["snapshot"] = "snap.txt"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "snap.txt").write_text("something else entirely", encoding="utf-8")
            self.assertTrue(any("逐字匹配" in x for x in inspect(data, root=root)["errors"]))

    def test_missing_snapshot_warns_source_is_not_machine_checked(self) -> None:
        result = inspect(copy.deepcopy(SAMPLE))
        self.assertTrue(any("未提供 snapshot" in x for x in result["warnings"]))

    def test_declared_snapshot_must_exist(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["sources"][0]["snapshot"] = "missing-source.txt"
        with tempfile.TemporaryDirectory() as tmp:
            result = inspect(data, root=Path(tmp))
        self.assertTrue(any("snapshot 不存在" in x for x in result["errors"]))

    def test_snapshot_match_accepted(self) -> None:
        data = copy.deepcopy(SAMPLE)
        data["sources"][0]["snapshot"] = "snap.txt"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "snap.txt").write_text("prefix constraint propagation improves recall on partial drawings suffix", encoding="utf-8")
            self.assertFalse(any("逐字匹配" in x for x in inspect(data, root=root)["errors"]))

    def test_wrong_top_level_type(self) -> None:
        self.assertTrue(inspect(["unexpected"])["errors"])


if __name__ == "__main__":
    unittest.main()
