#!/usr/bin/env python3
"""最小锚点对账：quote 必须能在同目录下的某个本地抓取件里逐字找到。
约 25 行，纯标准库、零网络。用于演示 check_portfolio.py 查不出的"编造锚点"。"""
import json, sys, pathlib

pf = json.loads(pathlib.Path(sys.argv[1]).read_text())
root = pathlib.Path(sys.argv[1]).parent
def body(p):  # 只取抓取件正文，不吃 schema 字段
    return p.read_text(errors="ignore")
self_path = pathlib.Path(sys.argv[1]).resolve()
corpus = "\n".join(body(p) for p in root.glob("*")
                   if p.is_file() and p.resolve() != self_path
                   and not p.name.startswith("portfolio") and p.suffix in {".json", ".out", ".htm", ".html", ".txt"})
bad = [s["id"] for s in pf.get("sources", [])
       if s.get("checked") and s.get("quote", "").strip() not in corpus]
print("锚点对账:", "全部命中" if not bad else f"以下来源的引文在本地抓取件中找不到: {bad}")
sys.exit(1 if bad else 0)
