import re, pathlib
for p in ["SKILL.md","references/agent-contract.md","references/experiment-protocol.md","references/portfolio-format.md"]:
    t = pathlib.Path(p).read_text(encoding="utf-8")
    lines = [l for l in t.splitlines() if l.strip()]
    body = "\n".join(lines)
    cn = len(re.findall(r"必须|不得|不要|严禁|不能|禁止", body))
    bullets = sum(1 for l in lines if re.match(r"\s*[-*] |\s*\d+\. ", l))
    obs = len(re.findall(r"portfolio\.json|run-log|tracks/|\.md|artifact|字段|命令|原始输出|表格", body))
    print(f"{p:34s} 非空行={len(lines):3d} 字符={len(body):5d} 中文约束词={cn:3d} 列表项={bullets:3d} 产物引用={obs:2d}")
