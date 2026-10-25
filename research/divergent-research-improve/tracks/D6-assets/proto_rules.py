#!/usr/bin/env python3
"""D6 原型：只实现拟新增的三条规则，用来验证规则可脚本化、可区分退化样本。

规则：
R1  verification.result == "pass" 时，artifact 指向的本地文件必须真实存在
    （或用 artifact_kind="external" + http(s) URL 显式声明外部记录）。
R2  sources[].checked == true 时，必须有 at least 1 条 anchors，
    每条含 locator、quote（8–60 字符）、supports（该引文支持的具体子结论）。
R3  finalists（可选顶层数组）两两之间至少有一条 discriminator 指名对方，
    discriminator 需含 observation、prediction_self、prediction_other 三个非空字段。
    （"判别性观察"= 一个可执行输入/工况/资料查询，使两候选给出可区分的事先预测。）
局限：不判断 quote 是否真的摘自该文献，也不判断 ability 预测是否科学；这两点必须人工抽查。
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def filled(v) -> bool:
    return isinstance(v, str) and bool(v.strip())

def check(data: dict, base: Path) -> list[str]:
    errs: list[str] = []
    sources = {s.get("id"): s for s in data.get("sources", []) if isinstance(s, dict)}
    cands = {c.get("id"): c for c in data.get("candidates", []) if isinstance(c, dict)}

    for sid, s in sources.items():
        if s.get("checked") is True:
            anchors = s.get("anchors") or []
            good = [a for a in anchors if isinstance(a, dict)
                    and filled(a.get("locator")) and filled(a.get("quote"))
                    and 8 <= len(a["quote"].strip()) <= 60 and filled(a.get("supports"))]
            if not good:
                errs.append(f"R2 {sid}: checked=true 但没有合格原文锚点（需 locator+8–60字逐字引文+supports）")

    for cid, c in cands.items():
        v = c.get("verification") or {}
        if v.get("result") == "pass":
            art = v.get("artifact") or ""
            if v.get("artifact_kind") == "external":
                if not art.startswith("http"):
                    errs.append(f"R1 {cid}: 外部记录但不是 http(s) 链接")
            elif not (base / art).exists():
                errs.append(f"R1 {cid}: pass 的 artifact 不存在于磁盘：{art!r}")

    finals = data.get("finalists")
    if isinstance(finals, list) and len(finals) >= 2:
        for i, a in enumerate(finals):
            for b in finals[i + 1:]:
                ca, cb = cands.get(a), cands.get(b)
                if not ca or not cb:
                    errs.append(f"R3 finalists 引用未定义候选：{a!r} / {b!r}")
                    continue
                ok = False
                for me, other in ((ca, b), (cb, a)):
                    for d in me.get("discriminators") or []:
                        if isinstance(d, dict) and d.get("vs") == other and all(
                                filled(d.get(k)) for k in ("observation", "prediction_self", "prediction_other")):
                            ok = True
                if not ok:
                    errs.append(f"R3 {a} 与 {b} 之间没有判别性观察，不能宣称原理不同")
    return errs

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("portfolio", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    data = json.loads(a.portfolio.read_text(encoding="utf-8"))
    errs = check(data, a.portfolio.parent)
    if a.json:
        print(json.dumps({"errors": errs}, ensure_ascii=False, indent=2))
    else:
        print(f"errors: {len(errs)}")
        for e in errs: print("错误：" + e)
    return 2 if errs else 0

if __name__ == "__main__":
    raise SystemExit(main())
