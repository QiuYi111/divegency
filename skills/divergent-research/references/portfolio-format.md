# 方案库格式（可选）

`portfolio.json` 用来记录搜索覆盖和证据，不决定哪条方案正确。可先只用 Markdown；需要反复迭代时再建立这份文件。

```json
{
  "goal": "把完整目标写在这里",
  "mode": "algorithm",
  "directions": [
    {"id": "D1", "lens": "从数学逆问题出发", "reason": "与其他方向的起点不同"},
    {"id": "D2", "lens": "完全自由探索", "reason": "检测预设方向的盲区"}
  ],
  "sources": [
    {"id": "S1", "locator": "https://example.org/primary-paper", "kind": "primary", "checked": false}
  ],
  "candidates": [
    {
      "id": "C1",
      "direction_id": "D1",
      "summary": "候选方案是什么",
      "mechanism": "具体说明因果原理，不能只有方案名称",
      "mechanism_key": "inverse-constraints",
      "evidence": [{"source_id": "S1", "supports": "具体支持哪条结论", "where": "第几节或哪行"}],
      "assumptions": ["必须成立的条件"],
      "failure_cases": ["最有力的反例或失败条件"],
      "verification": {
        "method": "对照测试",
        "criterion": "同一批输入的成功率高于基线",
        "result": "not-run",
        "artifact": ""
      }
    }
  ]
}
```

约定：

- `mode` 取 `facts`、`decision`、`design`、`algorithm`。
- `mechanism_key` 是**汇总者基于原理**归类的短标识，不能让候选的提出者自行通过换名字制造“新机制”。事实模式下代表不同的解释或结论类型。
- `sources.kind` 取 `primary`、`secondary`、`experiment`；`checked=true` 表示实际打开并核对原文，而不是看到搜索摘要。
- `verification.result` 取 `not-run`、`pass`、`fail`、`inconclusive`；只有实际完成测试才写 `pass`。记录 `pass` 时，`artifact` 要指向可复查的命令输出、报告或数据。
- `evidence[].supports` 表明资料支持的是哪一个子结论；并非“有一个网址”就算证据。
- 可以多轮向 `directions` 和 `candidates` 追加内容。不要覆盖历史失败和旧方案，可另行保留 Markdown 过程记录。

检查命令：

```bash
python scripts/check_portfolio.py portfolio.json
python scripts/check_portfolio.py portfolio.json --json
```

脚本检查结构、缺失引用、方向覆盖、重复 `mechanism_key` 和未留凭据的通过结果。它不能判断语义上是否重复、论文是否真实、实验是否有效；这些需要人工或独立 Agent 核查。
