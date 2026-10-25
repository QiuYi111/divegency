"""D2 原型：把"自报布尔"换成"有代价的字段"，验证能否拦住退化产物。仅标准库。"""
from __future__ import annotations
import json, sys
from pathlib import Path

FORBIDDEN_STRONG = ("优于", "证明", "显著超过", "超额完成")

def claim_level(v: dict) -> str:
    if v.get("result") != "pass":
        return "untested"
    if v.get("evaluator") == "independent" and int(v.get("n_runs") or 0) >= 2 and str(v.get("frozen") or "").strip():
        return "independently-replicated"
    return "dev-only"

def check_v2(data: dict) -> list[str]:
    errs: list[str] = []
    cands = data.get("candidates") or []
    ids = {c.get("id") for c in cands if isinstance(c, dict)}
    srcs = {s.get("id"): s for s in (data.get("sources") or []) if isinstance(s, dict)}

    # G3：已核实必须有位置 + 原文摘录
    for sid, s in srcs.items():
        if s.get("checked") is True:
            if not str(s.get("where") or "").strip():
                errs.append(f"{sid}: checked=true 但没有 where（节/页/行）")
            q = str(s.get("quote") or "").strip()
            if not q:
                errs.append(f"{sid}: checked=true 但没有 quote 原文摘录")
            elif len(q) > 120:
                errs.append(f"{sid}: quote 过长（{len(q)}>120），应摘关键句而非整段摘要")

    # G2：区分性断言，且必须双向
    diff: dict[str, set[str]] = {}
    for c in cands:
        cid = c.get("id")
        entries = c.get("differentiation")
        if not isinstance(entries, list) or not entries:
            errs.append(f"{cid}: 缺少 differentiation（与谁不同、在哪个输入上预测不同）")
            diff[cid] = set(); continue
        diff[cid] = set()
        for i, e in enumerate(entries, 1):
            if not isinstance(e, dict):
                errs.append(f"{cid}.differentiation[{i}]: 必须是对象"); continue
            vs = e.get("vs")
            if vs not in ids or vs == cid:
                errs.append(f"{cid}.differentiation[{i}].vs: 指向不存在或自身的候选 {vs!r}")
            else:
                diff[cid].add(vs)
            if len(str(e.get("witness") or "").strip()) < 8:
                errs.append(f"{cid}.differentiation[{i}].witness: 需要具体输入与两种相反预测")
            if not str(e.get("falsifier") or "").strip():
                errs.append(f"{cid}.differentiation[{i}].falsifier: 需要'看到什么就判定同一机制'")
    for cid, others in diff.items():
        for o in others:
            if cid not in diff.get(o, set()):
                errs.append(f"{cid} 声称与 {o} 不同，但 {o} 没有反向声明；单向声明视为未去重")

    # G4：验证等级与措辞一致
    for c in cands:
        cid = c.get("id")
        v = c.get("verification")
        if not isinstance(v, dict):
            errs.append(f"{cid}: verification 缺失"); continue
        lvl = claim_level(v)
        if v.get("result") == "pass" and lvl == "dev-only":
            if v.get("evaluator") != "independent":
                errs.append(f"{cid}: result=pass 但 evaluator≠independent，claim_level 只能是 dev-only")
            elif int(v.get("n_runs") or 0) < 2:
                errs.append(f"{cid}: result=pass 但 n_runs<2，不能排除单次波动")
        text = str(v.get("claim") or "")
        if lvl != "independently-replicated" and any(w in text for w in FORBIDDEN_STRONG):
            errs.append(f"{cid}: claim_level={lvl} 却使用'{text}'级别的措辞")
    return errs

if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    errs = check_v2(data)
    for e in errs:
        print("错误：" + e)
    print(f"共 {len(errs)} 条错误" + ("；通过" if not errs else "；未通过"))
    sys.exit(1 if errs else 0)
