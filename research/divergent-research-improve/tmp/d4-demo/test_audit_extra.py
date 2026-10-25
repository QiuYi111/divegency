"""标题模板不应触发泄漏告警；未被引用的已核对来源应提示。"""

import unittest

from audit_run import leakage


class HeadingTemplateTests(unittest.TestCase):
    def test_same_headings_do_not_trigger(self) -> None:
        files = {
            "D1.md": "# 核心机制\n用约束求解处理欠定图纸。\n# 证据\n论文 4.2 节。",
            "D2.md": "# 核心机制\n用多视图一致性回归深度。\n# 证据\n手册第 3 章。",
        }
        self.assertEqual(leakage(files, "", 20), [])


if __name__ == "__main__":
    unittest.main()
