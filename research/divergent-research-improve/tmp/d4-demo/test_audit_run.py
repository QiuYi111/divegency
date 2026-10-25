"""audit_run 的确定性测试；无网络、无第三方依赖。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from audit_run import check_journal, leakage, sample_sheet, unsupported_claims

BRIEF = "共同任务书：目标是把工程图转成三维模型，硬约束是只用标准库。"


def ev(*items):
    return [dict(seq=i + 1, **item) for i, item in enumerate(items)]


class JournalTests(unittest.TestCase):
    def test_clean_run_passes(self) -> None:
        events = ev(
            {"event": "dispatch", "track": "D1"},
            {"event": "dispatch", "track": "D2"},
            {"event": "submit", "track": "D1"},
            {"event": "submit", "track": "D2"},
            {"event": "synthesis"},
            {"event": "register", "exp": "E1"},
            {"event": "result", "exp": "E1"},
        )
        self.assertEqual(check_journal(events), [])

    def test_seq_must_increase(self) -> None:
        events = ev({"event": "dispatch", "track": "D1"}, {"event": "dispatch", "track": "D2"})
        events[1]["seq"] = 1
        self.assertTrue(any("未递增" in e for e in check_journal(events)))

    def test_result_before_register_rejected(self) -> None:
        events = ev({"event": "result", "exp": "E9"})
        self.assertTrue(any("没有事前登记" in e for e in check_journal(events)))

    def test_synthesis_before_all_submits_rejected(self) -> None:
        events = ev(
            {"event": "dispatch", "track": "D1"},
            {"event": "dispatch", "track": "D2"},
            {"event": "submit", "track": "D1"},
            {"event": "synthesis"},
        )
        self.assertTrue(any("尚无交付记录" in e or "提交前就开始汇总" in e
                        for e in check_journal(events)))

    def test_peer_read_early_is_flagged(self) -> None:
        events = ev(
            {"event": "dispatch", "track": "D1"},
            {"event": "dispatch", "track": "D2"},
            {"event": "peer_read", "track": "D1", "source_track": "D2"},
            {"event": "submit", "track": "D1"},
        )
        self.assertTrue(any("首轮独立性存疑" in e for e in check_journal(events)))


class LeakageTests(unittest.TestCase):
    def test_copied_run_detected(self) -> None:
        shared = "用几何约束反推草图平面再逐面闭合，编号与拓扑一次对齐"
        files = {"D1.md": "我的路线：" + shared + "。", "D2.md": "另一条：" + shared + "，补充。"}
        self.assertTrue(leakage(files, "", 20))

    def test_brief_boilerplate_ignored(self) -> None:
        files = {"D1.md": BRIEF + "甲", "D2.md": BRIEF + "乙"}
        self.assertEqual(leakage(files, BRIEF, 20), [])

    def test_independent_prose_clean(self) -> None:
        files = {"D1.md": "从约束求解出发，把图纸当作欠定方程组处理。",
                 "D2.md": "从视觉重建出发，用多视图一致性约束深度。"}
        self.assertEqual(leakage(files, "", 20), [])


class ClaimTests(unittest.TestCase):
    def test_bare_claim_flagged(self) -> None:
        text = "实验跑完了，已证明优于基线。"
        self.assertTrue(unsupported_claims(text, "D1.md"))

    def test_claim_with_quote_or_artifact_passes(self) -> None:
        a = "论文第 4.2 节原文：「约束数不足时先补剖视图」，据此已核实该限制存在。"
        b = "已复现：runs/e3.log 显示成功率 0.71。"
        self.assertEqual(unsupported_claims(a, "D1.md"), [])
        self.assertEqual(unsupported_claims(b, "D1.md"), [])


class SamplingTests(unittest.TestCase):
    def portfolio(self):
        return {
            "sources": [
                {"id": "S1", "locator": "https://a/1", "kind": "primary", "checked": True},
                {"id": "S2", "locator": "https://a/2", "kind": "primary", "checked": True},
                {"id": "S3", "locator": "https://a/3", "kind": "secondary", "checked": False},
            ],
            "candidates": [{"id": "C1", "evidence": [{"source_id": "S1", "supports": "约束可解"}]}],
        }

    def test_only_checked_sources_and_seed_reproducible(self) -> None:
        a = sample_sheet(self.portfolio(), 2, 7)
        b = sample_sheet(self.portfolio(), 2, 7)
        self.assertEqual(a, b)
        self.assertTrue(any("S1" in x or "S2" in x for x in a))
        self.assertFalse(any("S3" in x for x in a))

    def test_sheet_lists_claimed_conclusion(self) -> None:
        sheet = "\n".join(sample_sheet(self.portfolio(), 2, 7))
        self.assertIn("约束可解", sheet)


if __name__ == "__main__":
    unittest.main()
