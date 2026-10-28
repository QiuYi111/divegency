# Divegency

多 Agent 独立探索与方案精选 Skill。

当前版本在 [`skills/divergent-research/`](skills/divergent-research/SKILL.md)：从宽泛且不同的方向出发，让每个 Agent 独立解决完整目标；用判别问题与预测签名去重，补搜盲点，再用原始资料和独立实验验证。

v0.2 把“独立性、多样性、已验证”从声明改成可出示的产物：每路的异质来源与判别性预测、原文锚点、会失败的验证、L1–L3 降级阶梯，以及一个能拦住换名与空壳通过的方案库检查器。设计取舍与实测记录在 [`research/divergent-research-improve/`](research/divergent-research-improve/M1.md)。

适用于信息搜集、技术选型、工程设计和算法改进。运行时使用宿主 Agent 的原生并行功能，不要求安装独立的 Agent 框架。

使用时让支持 Agent Skills 的工具读取 `skills/divergent-research/SKILL.md`；是否能自动识别及如何安装，取决于所用工具。

## 当总指挥

[`skills/agent-team-lead/`](skills/agent-team-lead/SKILL.md)：一个强模型当总指挥，组织几个到几百个外部 worker 完成大项目。工作类型有赛跑（多立场出可运行原型，由决策者挑）、起草、盲点筛查、合并、反思；总指挥逐份核验（抽查原文、亲手重跑、统一编号），用审核表让决策者拍板并把决定落成记录。附任务说明模板、审核表模板、调度程序的坑与一个参考调度程序（`scripts/race_runner.py`）。

与 `divergent-research` 的分工：那一份管独立探索与选择的研究纪律，这一份管大规模执行的组织纪律；赛跑和筛查时两份一起用。经验来自 Reify V2 的设计阶段（一个 Opus 总指挥带 DeepSeek Flash worker，单批最多约 20 路并行）。
