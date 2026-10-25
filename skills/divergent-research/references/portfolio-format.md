# 方案库格式（可选）

`portfolio.json` 用来记录搜索覆盖和证据，不决定哪条方案正确。可先只用 Markdown；需要反复迭代时再建立这份文件。

```json
{
  "goal": "把完整目标写在这里",
  "mode": "algorithm",
  "budget": "standard",
  "probes": [
    {"id": "P1", "intervention": "删掉剖视图", "question": "成功率是否下降超过 5 个百分点"}
  ],
  "directions": [
    {"id": "D1", "lens": "从数学逆问题出发", "axis": "信息来源"},
    {"id": "D2", "lens": "完全自由探索", "axis": "无预设"}
  ],
  "sources": [
    {
      "id": "S1",
      "locator": "https://example.org/primary-paper",
      "kind": "primary",
      "checked": true,
      "where": "§4.2",
      "quote": "逐字摘录 8–120 字，能在原文中找到"
    }
  ],
  "dead_ends": [
    {"route": "纯端到端回归", "why": "缺视图样本上误差爆炸", "evidence": "runs/e2e.log"}
  ],
  "candidates": [
    {
      "id": "C1",
      "direction_id": "D1",
      "contributor_direction_ids": ["D2"],
      "summary": "候选方案是什么",
      "mechanism": "具体说明因果原理，不能只有方案名称",
      "mechanism_key": "inverse-constraints",
      "predictions": {"P1": "down"},
      "differentiation": [
        {"vs": "C2", "observation": "只给主视图时", "prediction_self": "无解", "prediction_other": "给出近似体"}
      ],
      "evidence": [{"source_id": "S1", "supports": "具体支持哪条结论", "where": "第几节或哪行"}],
      "assumptions": ["必须成立的条件"],
      "failure_cases": ["最有力的反例或失败条件"],
      "verification": {
        "method": "对照测试",
        "criterion": "同一批输入的成功率高于基线",
        "result": "not-run",
        "artifact": "",
        "evaluator": "self",
        "rerun": "python run.py --seed 1"
      }
    }
  ],
  "finalists": ["C1", "C2"]
}
```

约定：

- `mode` 取 `facts`、`decision`、`design`、`algorithm`；`budget` 取 `quick`、`standard`、`deep`。
- `probes` 是**首轮独立完成后**汇总出的共同判别问题，在进行候选对比前锁定，不向首轮 Agent 预先透露。`predictions` 取 `up`、`down`、`no-change`、`unknown`；只要声明 `probes`，每个候选都须逐项填写，缺失或空字典会报错，真正不知道就填 `unknown`。
- `mechanism_key` 只是**汇总者的族标签**，不是证据。比较结果有三种：已证同原理、存在判别证据、尚无法区分。同一 `probes` 签名**不是同原理的证明**，检查器只提醒补更有区分力的探针；但两条**逐字相同的机制描述**却被起了不同 `mechanism_key`，属于记录自相矛盾，会报错。
- `differentiation` 用于**主张两方案可区分**的情形，必须写可执行输入和双方不相同的预测；只写 `vs` 或相同预测会报错。`finalists` 是有待选择的候选，不承诺两两原理不同；双向判别缺失时仅提示“未确认”，不得将此候选对算为已区分。
- `contributor_direction_ids` 可记录同一候选被哪些其它独立路线支持或改进。这些方向会计入“有贡献”，但不代表产生了独有机制；不能用它伪造独立性。没有贡献时可省略。
- `sources.kind` 取 `primary`、`secondary`、`experiment`。`checked=true` 必须同时给 `where` 与 `quote`（≥8 字逐字原文），否则按未核实处理。只看到标题或摘要的写 `false`。
- 原文落盘时用 `snapshot` 指向原始抓取件：检查器核对逐字引文；填了 `snapshot` 却不存在会报错。不填只表示**未机器核验**，即使 `checked=true` 也会给提醒（`--strict` 不通过），由复核者按 `locator` 真正打开核对。机器能匹配文本也不等于资料真实。
- `artifact` 是单个文件路径或 URL，不是目录或叙述句；本地路径必须真实存在且非空。URL 会标为“外部、未离线核验”，需要复核者打开确认；多个候选共用同一 artifact 会被提醒。**文件存在不等于实验结果正确**。`evaluator` 取 `self` 或 `independent`；只有独立执行且可重跑，才能在正文写“在保留集上优于基线”。
- 可多轮追加 `directions`、`candidates`、`dead_ends`。不要覆盖历史失败和旧方案。

## 过程断点 RUN.md

长任务或会被中断的任务用一个 `RUN.md`（`quick` 只写这一个文件）：

```markdown
# RUN
目标：一句话
档位：quick / standard / deep
独立性等级：L1 / L2 / L3（污染路径：…）
视角与状态：D1 完成 tracks/D1.md；D2 进行中
已确认结论（≤3）：…
下一步（一个动作）：…
停止条件：…
```

恢复时先读 `RUN.md`，核对产物存在，不重读旧轨迹、不重派已完成视角。`quick` 可以只用一个文件，但每路至少有**独立、可识别的完成记录**；仅有派发草稿或未完成的方向不能写成完成。复核没执行要显式标“未复核”。

## 检查命令

```bash
python scripts/check_portfolio.py portfolio.json
python scripts/check_portfolio.py portfolio.json --json
python scripts/check_portfolio.py portfolio.json --strict   # 提醒也算失败，适合 CI
```

脚本检查：字段与引用、引用是否附带锚点和可核验快照、`pass` 的 artifact 是否为非空文件、候选对有无双向区分主张、判别问题是否完整、有无不可区分的签名、死路是否写了原因。它**不能**判定两个原理是否等价、引文真伪、链接是否 404，也不能证明“研究真的发生过”；这些仍需独立核查。

> 0.1 → 0.2 的破坏性变更：旧方案库里 `checked=true` 没有 `where`/`quote` 的，现在会报错。补上锚点，或改成 `false` 并在候选里标“未核实”。
