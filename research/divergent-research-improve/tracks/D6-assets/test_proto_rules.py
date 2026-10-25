"""D6 原型回归测试：退化样本必须报错，诚实样本必须通过。"""
import json, unittest
from pathlib import Path
from proto_rules import check

BASE = Path(__file__).parent
def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))

class RuleTests(unittest.TestCase):
    def test_degraded_flagged(self):
        errs = check(load("fixture_degraded.json"), BASE)
        self.assertEqual(len(errs), 4)
        self.assertTrue(any(e.startswith("R2") for e in errs))
        self.assertEqual(sum(e.startswith("R1") for e in errs), 2)
        self.assertTrue(any(e.startswith("R3") for e in errs))

    def test_same_mechanism_renamed_flagged(self):
        errs = check(load("fixture_renamed.json"), BASE)
        self.assertEqual(len(errs), 3)
        self.assertTrue(all(e.startswith("R3") for e in errs))

    def test_honest_passes(self):
        self.assertEqual(check(load("fixture_honest.json"), BASE), [])

if __name__ == "__main__":
    unittest.main()
