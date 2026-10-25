# Divegency

多 Agent 独立探索与方案精选 Skill。

当前版本在 [`skills/divergent-research/`](skills/divergent-research/SKILL.md)：从宽泛且不同的方向出发，让每个 Agent 独立解决完整目标；用判别问题与预测签名去重，补搜盲点，再用原始资料和独立实验验证。

v0.2 把“独立性、多样性、已验证”从声明改成可出示的产物：每路的异质来源与判别性预测、原文锚点、会失败的验证、L1–L3 降级阶梯，以及一个能拦住换名与空壳通过的方案库检查器。设计取舍与实测记录在 [`research/divergent-research-improve/`](research/divergent-research-improve/M1.md)。

适用于信息搜集、技术选型、工程设计和算法改进。运行时使用宿主 Agent 的原生并行功能，不要求安装独立的 Agent 框架。

使用时让支持 Agent Skills 的工具读取 `skills/divergent-research/SKILL.md`；是否能自动识别及如何安装，取决于所用工具。
