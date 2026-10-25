# 设计参考与边界

这些来源提供方法，不是本 Skill 的运行依赖。没有复制它们的代码。

- [Stanford STORM / Co-STORM](https://github.com/stanford-oval/storm)：从邻近主题发现不同视角，基于资料开展持续提问。原工具面向知识收集和成文，不能直接替代完整方案竞选。
- [IDEAgent 论文](https://arxiv.org/abs/2607.22375) / [代码](https://github.com/declare-lab/IDEAgent)：同时追求高质量和真正不同的想法，记录已接纳、历史、被拒绝的路线。开源实现偏科研想法的顺序生成。
- [Claude Brainstorm Multiagent](https://github.com/giordanorec/claude-brainstorm-multiagent)：多 Agent 发散、空白格探索、方案演化。较新的实验性插件，不应把其模型排名当作实际测试。
- [MAP-Elites](https://arxiv.org/abs/1504.04909)：保留不同区域的优秀候选，而非只保留全局最高分。此处只采用“按原理保留多种路线”的理念。
- [SenseNova Deep Research](https://github.com/OpenSenseNova/SenseNova-Skills/tree/main/skills/sn-deep-research)：并行检索、资料引用和补充搜索。研究角色按资料维度拆分，不能直接实现独立完整方案生成。
- [Solution Tournament](https://github.com/rwshiraishi/solution-tournament)：事先制定标准、比较与反证，并承认单一作者和模型评分的局限。
- [ARIS Idea Discovery](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/tree/main/skills/idea-discovery)：查新、批评、用小规模实验筛掉无效想法。对算法研究很有参考价值，通用工程任务须改实验方法。
- [Agent4Sci 论文](https://arxiv.org/html/2610.28763v1) / [代码](https://github.com/maszhongming/agent4sci)：发现 Agent 易将常见调参当作创新、闲置计算资源，并在取得一点进展后陷入局部优化。其研究构思、实验管理和定时自检三个 Skill 在所测科学机器学习任务上改善了结果；更重要的是分开“方案改进、隐藏测试、独立审计”，防止选择性报告、泄露测试信息和修改评分规则。它验证的是单 Agent、特定基准上的改进，不能据此直接声称多 Agent 本 Skill 的效果已经证实。

本 Skill 的核心选择：**相同的完整目标 + 不同且宽泛的搜索起点 + 首轮相互隔离 + 后续按缺口补搜 + 可复查的证据与实验**。子 Agent 自由选择具体做法，不被一套固定解题步骤限制。
