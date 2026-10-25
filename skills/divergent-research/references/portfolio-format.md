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
- `probes` 是派发前锁定的判别问题；`predictions` 取 `up`、`down`、`no-change`、`unknown`。声明了 `probes`，每个候选都必须给出全部预测——少写一条会报错（否则“不填”反而比“填错”安全）。签名相同只表示“在这组问题下不可区分”，不表示已证明机制相同。
- `mechanism_key` 只是**汇总者的族标签**，不是证据；真正去重靠 `differentiation`（可执行的具体输入＋两方相反预测）与 `probes` 签名。每条 `differentiation` 必须同时给 `prediction_self` 与 `prediction_other`，且两者不能相同；只写 `vs` 与 `observation` 会报错。
- `sources.kind` 取 `primary`、`secondary`、`experiment`。`checked=true` 必须同时给 `where` 与 `quote`（≥8 字逐字原文），否则按未核实处理。只看到标题或摘要的写 `false`。
- 能把原文落盘时加 `snapshot`（本地抓取件路径）：检查器会核对 `quote` 能否在文件里逐字找到。这是把锚点从声明变成可对账的最便宜办法；书籍、付费库等无法落盘的来源可不填，由审计者按 `locator` 抽查。
- `artifact` 是路径或 URL，不是叙述句；本地路径必须真实存在且非空（空文件会被判错）。URL 会标为“外部、未离线核验”，需要复核者打开确认；多个候选共用同一 artifact 会被提醒——一次运行通常只能证明一个候选。`evaluator` 取 `self` 或 `independent`；只有独立执行且可重跑，才能在正文写“在保留集上优于基线”。
- `finalists` 两两之间必须有**双向**判别性观察，否则不能宣称原理不同。
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

恢复时先读 `RUN.md`，核对产物存在，不重读旧轨迹、不重派已完成视角。

## 检查命令

```bash
python scripts/check_portfolio.py portfolio.json
python scripts/check_portfolio.py portfolio.json --json
python scripts/check_portfolio.py portfolio.json --strict   # 提醒也算失败，适合 CI
```

脚本检查：字段与引用、`checked` 是否有锚点、`pass` 的 artifact 是否存在且非空并含已核实证据、`finalists` 是否双向区分、判别问题签名是否撞车（不同机制族却同签名会报错）、死路是否写了原因。它**不能**判断语义重复、引文真伪、链接是否 404，也不能证明“研究真的发生过”；这些仍需独立核查。

> 0.1 → 0.2 的破坏性变更：旧方案库里 `checked=true` 没有 `where`/`quote` 的，现在会报错。补上锚点，或改成 `false` 并在候选里标“未核实”。
