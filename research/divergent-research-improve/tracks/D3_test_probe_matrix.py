"""Tests for the optional probe-battery check (no network, stdlib only)."""

from __future__ import annotations

import copy
import subprocess
import sys
import unittest
from pathlib import Path

from D3_probe_matrix import inspect_coverage, shingles, jaccard

BASE = {
    "goal": "给工程图转三维模型找到原理不同的方案",
    "mode": "design",
    "probes": [
        {"id": "P1", "intervention": "把输入顺序随机打乱", "question": "成功率是否下降"},
        {"id": "P2", "intervention": "把图上的尺寸标注全部删掉", "question": "是否还能重建"},
        {"id": "P3", "intervention": "允许额外拍摄一张照片", "question": "成功率是否显著上升"},
        {"id": "P4", "intervention": "把训练样本减半", "question": "成功率是否下降"},
    ],
    "candidates": [
        {
            "id": "C1",
            "direction_id": "D1",
            "claimed_cause": "用几何约束求解器反推尺寸，缺失标注时约束不完备",
            "predictions": {"P1": "no-change", "P2": "degrade", "P3": "improve", "P4": "no-change"},
        },
        {
            "id": "C2",
            "direction_id": "D2",
            "claimed_cause": "用多视图视觉重建拟合点云，对视角数量敏感",
            "predictions": {"P1": "no-change", "P2": "degrade", "P3": "improve", "P4": "degrade"},
        },
        {
            "id": "C3",
            "direction_id": "D3",
            "claimed_cause": "用程序搜索枚举建模序列，靠搜索预算而非信息量",
            "predictions": {"P1": "degrade", "P2": "no-change", "P3": "no-change", "P4": "improve"},
        },
    ],
}


class CoverageTests(unittest.TestCase):
    def test_distinct_signatures_counted(self) -> None:
        r = inspect_coverage(copy.deepcopy(BASE))
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["stats"]["distinct_signatures"], 3)
        self.assertEqual(r["stats"]["signature_collisions"], 0)

    def test_identical_signature_flagged(self) -> None:
        data = copy.deepcopy(BASE)
        data["candidates"][1]["predictions"] = copy.deepcopy(data["candidates"][0]["predictions"])
        r = inspect_coverage(data)
        self.assertEqual(r["stats"]["signature_collisions"], 1)
        self.assertTrue(any("不可区分" in w for w in r["warnings"]))

    def test_consensus_probe_exposed(self) -> None:
        data = copy.deepcopy(BASE)
        for cand in data["candidates"]:
            cand["predictions"]["P3"] = "improve"
        r = inspect_coverage(data)
        self.assertIn("P3", r["consensus_probes"])
        self.assertTrue(any("共同盲点" in w for w in r["warnings"]))

    def test_uncovered_probe_exposed(self) -> None:
        data = copy.deepcopy(BASE)
        for cand in data["candidates"]:
            cand["predictions"]["P4"] = "unknown"
        r = inspect_coverage(data)
        self.assertIn("P4", r["uncovered_probes"])

    def test_bad_value_is_error(self) -> None:
        data = copy.deepcopy(BASE)
        data["candidates"][0]["predictions"]["P1"] = "maybe"
        self.assertTrue(any("取值应为" in e for e in inspect_coverage(data)["errors"]))

    def test_missing_probe_becomes_unknown(self) -> None:
        data = copy.deepcopy(BASE)
        del data["candidates"][0]["predictions"]["P2"]
        r = inspect_coverage(data)
        self.assertEqual(r["errors"], [])

    def test_same_claimed_cause_flagged(self) -> None:
        data = copy.deepcopy(BASE)
        data["candidates"][1]["claimed_cause"] = data["candidates"][0]["claimed_cause"]
        r = inspect_coverage(data)
        self.assertTrue(any("因果载体相同" in w for w in r["warnings"]))

    def test_lexical_screen_fails_on_chinese_short_sentences(self) -> None:
        # Regression lock for a measured negative result: the char-3gram screen
        # cannot separate a paraphrase from a shared-vocabulary different mechanism,
        # therefore it must not be used as a merge criterion (default off).
        paraphrase = jaccard(
            shingles("用几何约束求解器反推尺寸，约束不完备时退化为猜测"),
            shingles("把图纸转成几何约束方程组求解尺寸，约束不足就只能猜"),
        )
        different = jaccard(
            shingles("用几何约束求解器反推尺寸，约束不完备时退化为猜测"),
            shingles("不做尺寸反推，只用几何约束求解器检查候选模型是否自相矛盾"),
        )
        self.assertLess(abs(paraphrase - different), 0.05)

    def test_lexical_screen_off_by_default(self) -> None:
        data = copy.deepcopy(BASE)
        for cand in data["candidates"]:
            cand["claimed_cause"] = "用几何约束求解器反推尺寸"
        self.assertEqual(inspect_coverage(data)["stats"]["near_duplicate_pairs"], 0)

    def test_strict_mode_depth(self) -> None:
        data = copy.deepcopy(BASE)
        data["candidates"][1]["predictions"] = copy.deepcopy(data["candidates"][0]["predictions"])
        path = Path(__file__).with_name("_d3_tmp_portfolio.json")
        import json
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        code = subprocess.call(
            [sys.executable, str(Path(__file__).with_name("D3_probe_matrix.py")), str(path), "--strict"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        path.unlink()
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()