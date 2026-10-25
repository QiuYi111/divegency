# 设计参考与边界

这些来源提供方法，不是本 Skill 的运行依赖。没有复制它们的代码。

- [Stanford STORM / Co-STORM](https://github.com/stanford-oval/storm)：从邻近主题发现不同视角，基于资料开展持续提问。原工具面向知识收集和成文，不能直接替代完整方案竞选。
- [IDEAgent 论文](https://arxiv.org/abs/2607.22375) / [代码](https://github.com/declare-lab/IDEAgent)：同时追求高质量和真正不同的想法，记录已接纳、历史、被拒绝的路线。开源实现偏科研想法的顺序生成。
- [Claude Brainstorm Multiagent](https://github.com/giordanorec/claude-brainstorm-multiagent)：多 Agent 发散、空白格探索、方案演化。较新的实验性插件，不应把其模型排名当作实际测试。
- [MAP-Elites](https://arxiv.org/abs/1504.04909)：保留不同区域的优秀候选，而非只保留全局最高分。此处只采用“按原理保留多种路线”的理念。
- [SenseNova Deep Research](https://github.com/OpenSenseNova/SenseNova-Skills/tree/main/skills/sn-deep-research)：并行检索、资料引用和补充搜索。研究角色按资料维度拆分，不能直接实现独立完整方案生成。
- [Solution Tournament](https://github.com/rwshiraishi/solution-tournament)：事先制定标准、比较与反证，并承认单一作者和模型评分的局限。
- [ARIS Idea Discovery](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/tree/main/skills/idea-discovery)：查新、批评、用小规模实验筛掉无效想法。对算法研究很有参考价值，通用工程任务须改实验方法。
- [Agent4Sci 论文](https://arxiv.org/html/2610.28763v1) / [代码](https://github.com/maszhongming/agent4sci)：发现 Agent 易将常见调参当作创新、闲置计算资源，并在取得一点进展后陷入局部优化。作者实际发布的三个 Skill 是 [research](https://github.com/maszhongming/agent4sci/blob/main/agent4sci/skills/agents/skills/research/SKILL.md)、[experiment](https://github.com/maszhongming/agent4sci/blob/main/agent4sci/skills/agents/skills/experiment/SKILL.md)、[checklist](https://github.com/maszhongming/agent4sci/blob/main/agent4sci/skills/agents/skills/checklist/SKILL.md)。它们分别规定研究资料的起点、实验登记与失败排查、定期发现搜索方向变窄；Claude 版本的定时提醒由[工具钩子](https://github.com/maszhongming/agent4sci/blob/main/agent4sci/skills/claude/hooks/reminder.sh)触发，单纯写进 Skill 的“每小时检查”并不会自动定时。作者的四路资料搜索按领域 × 技术部位分工，**不同于**我们要求的“各路独立完成完整方案”；我们只借鉴其知识来源覆盖与纠偏办法。论文还通过隐藏测试与独立审查限制选择性报告、测试信息泄露和评分规则修改。它验证的是单 Agent、特定基准上的**整组三个 Skill**，不能据此单独归因或声称本多 Agent Skill 的效果已被证实。

## 证据边界（2026-10 复核）

- 多 Agent 辩论类方法在算力对齐后**经常不优于** self-consistency 等单 Agent 基线（[2311.17371](https://arxiv.org/abs/2311.17371)、[2502.08788](https://arxiv.org/abs/2502.08788)）；**模型／来源的异质性是较稳定的增益来源**。因此本 Skill 不把“多派 Agent”当收益来源，只把异质起点与会失败的验证当收益来源。
- 多 Agent 系统的大量失败集中在规格与验证两类，典型形态是“所有验证轮次都通过、产物仍然错”（[MAST, 2503.13657](https://arxiv.org/abs/2503.13657)）。因此“已验证”要求会失败、要求判定者带来新东西。
- 没有外部反馈时，模型自我复核可能**降低**准确率（[2310.01798](https://arxiv.org/abs/2310.01798)），评审还存在位置、长度与自我偏好偏差（[2306.05685](https://arxiv.org/abs/2306.05685)）。因此自我复核不算验证。
- “LLM 输出同质化”的证据仍有争议（对照 [2609.33936](https://arxiv.org/abs/2609.33936)）。保留首轮隔离的理由是**防止判断因看到同伴结论而漂移**（[2609.04445](https://arxiv.org/abs/2609.04445)），不是“防止模型趋同”。
- 以上为设计依据，不是本 Skill 效果的因果证据；本 Skill 尚未做多模型对照实验。

本 Skill 的核心选择：**相同的完整目标 + 不同且宽泛的搜索起点 + 首轮相互隔离 + 可判别的去重 + 可失败的验证 + 可复查的证据**。子 Agent 自由选择具体做法，不被一套固定解题步骤限制。
