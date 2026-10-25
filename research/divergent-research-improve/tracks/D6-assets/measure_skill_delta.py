
from pathlib import Path
p = Path("/Users/jingyi/divegency/skills/divergent-research/SKILL.md")
s = p.read_text(encoding="utf-8")
pairs = [
("2. 比较**为什么有效**，而不是名字、措辞或所属领域。相同机制的表面变体归为同一族；不同机制、不同关键假设或失败边界的方案应分别保留。",
"2. 比较**为什么有效**，而不是名字、措辞或所属领域。默认把候选按同一族处理，**由主张“不同”的一方举证**：只有给出一个**判别性观察**才允许分列——一个可执行、成本可接受的具体输入、工况或资料查询，使两条路线给出事先写下的、方向相反或取值不重叠的预测（写“会出现什么、方向、大致量级”，不写“A 更好”）。写不出判别性观察的，无论换了什么术语、学科或工具名，一律合并为一族。不同关键假设或失败边界本身不算不同原理，除非它们导出了不同的判别性观察。判别性观察可以暂不执行，但必须可执行；一旦执行后两方预测相同，立即合并。"),
("若宿主不提供真实隔离的子 Agent：使用可用的独立新会话；仍不支持时，明确写出“单 Agent 模拟，独立性未验证”，**不得**假称完成多 Agent 研究。",
"若宿主不提供真实隔离的子 Agent：优先用可用的独立新会话；仍不支持时按**顺序封存**降级：一次只跑一条路线，把它的完整答案、证据与失败记录写进 `tracks/Dk.md` 后封存（此后不回看、不改写），再开始下一条；下一条的视角按“与已封存路线最不相邻”或抽签选取，不得据已封存内容重写视角。交付中必须写明“单 Agent 顺序模拟，独立性弱于真并行”，并列出已知污染路径（例如第 2 路的检索词受第 1 路影响）。顺序封存仍好于把一份报告切成几段；但“我扮演了三个角色”不算多路研究。"),
]
base = len(s)
for old, new in pairs:
    assert old in s, old[:20]
    s = s.replace(old, new)
print("chars before:", base, "after:", len(s), "delta:", len(s)-base, "pct: %.1f%%" % (100*(len(s)-base)/base))
print("lines before:", 82, "lines after (paragraph-level, no new lines added):", s.count(chr(10)))
print("bytes before:", len(p.read_bytes()))
