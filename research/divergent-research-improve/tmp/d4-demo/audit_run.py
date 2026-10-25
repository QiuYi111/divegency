#!/usr/bin/env python3
"""审计一次分路研究留下的记录：顺序不变量、兄弟路线泄漏、无凭据断言、抽检清单。

只做机械一致性检查，不判断科学对错，也不证明结论为真。
退出码：0 无硬错误；2 有硬错误。
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

CLAIM = re.compile(r"已证明|已核实|已验证|已复现|独立复现|proven|verified|reproduced", re.I)
QUOTE_MARK = re.compile(r"[「『“\"]|原文|逐字|第\s*\d+\s*(页|节|行|章)|p\.\s*\d|L\d+")
ARTIFACT_MARK = re.compile(
    r"[\w./-]+\.(log|json|jsonl|csv|txt|md|png|py|svg|parquet)|(runs?|outputs?|artifacts?)/"
)
PUNCT = re.compile(r"[\s，。、；：！？（）「」『』“”‘’《》…—\-|/\\,.()\[\]{}:;!?'\"]+")


def norm(text: str) -> str:
    """去掉标题行、空白与标点，只留下可比对的正文。标题属模板，不算泄漏证据。"""
    body = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
    return PUNCT.sub("", body)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- journal

def check_journal(events: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seqs = [e.get("seq") for e in events]
    for i, s in enumerate(seqs):
        if not isinstance(s, int):
            errors.append(f"journal 第 {i + 1} 行缺少整数 seq")
        elif i and isinstance(seqs[i - 1], int) and s <= seqs[i - 1]:
            errors.append(f"journal seq 未递增：{seqs[i - 1]} -> {s}")
    bad_kind = [e for e in events if e.get("event") not in
                {"dispatch", "submit", "peer_read", "synthesis", "register", "result", "select"}]
    if bad_kind:
        errors.append(f"未知事件类型 {len(bad_kind)} 条，无法校验顺序")

    first_submit: dict[str, int] = {}
    dispatched: set[str] = set()
    for e in events:
        if not isinstance(e.get("seq"), int):
            continue
        if e.get("event") == "dispatch":
            dispatched.add(str(e.get("track")))
        elif e.get("event") == "submit":
            track = str(e.get("track"))
            if track not in dispatched:
                errors.append(f"seq {e['seq']}: {track} 未派发就提交，来源不明")
            first_submit.setdefault(track, e["seq"])
        elif e.get("event") == "peer_read":
            track, source = str(e.get("track")), str(e.get("source_track"))
            read_before_source = e["seq"] < first_submit.get(source, 10**9)
            read_before_own = e["seq"] < first_submit.get(track, 10**9)
            if read_before_source and read_before_own:
                errors.append(
                    f"seq {e['seq']}: {track} 在 {source} 交付前读它、且自己尚未提交，首轮独立性存疑")
            elif read_before_source:
                errors.append(f"seq {e['seq']}: {track} 读到的是 {source} 未交付的工作稿")
    for e in events:
        if e.get("event") == "synthesis" and isinstance(e.get("seq"), int):
            late = [t for t, s in first_submit.items() if s > e["seq"]]
            if late:
                errors.append(f"seq {e['seq']}: 在 {', '.join(sorted(late))} 提交前就开始汇总")
            missing = sorted(dispatched - set(first_submit))
            if missing:
                errors.append(f"seq {e['seq']}: 汇总时 {', '.join(missing)} 尚无交付记录")
            break

    registered: dict[str, int] = {}
    for e in events:
        if not isinstance(e.get("seq"), int):
            continue
        if e.get("event") == "register":
            registered[str(e.get("exp"))] = e["seq"]
        elif e.get("event") == "result":
            exp = str(e.get("exp"))
            if exp not in registered:
                errors.append(f"seq {e['seq']}: 实验 {exp} 没有事前登记（先登记再运行）")
            elif registered[exp] > e["seq"]:
                errors.append(f"seq {e['seq']}: 实验 {exp} 的结果早于登记")
    return errors


# ---------------------------------------------------------------- leakage

def leakage(files: dict[str, str], ignore: str, min_len: int) -> list[str]:
    warns: list[str] = []
    names = sorted(files)
    ignore_n = norm(ignore)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ta, tb = norm(files[a]), norm(files[b])
            if not ta or not tb:
                continue
            blocks = SequenceMatcher(None, ta, tb, autojunk=False).get_matching_blocks()
            for block in blocks:
                if block.size < min_len:
                    continue
                piece = ta[block.a:block.a + block.size]
                if piece in ignore_n:
                    continue
                ctx = ta[max(0, block.a - 25):block.a + block.size + 25]
                warns.append(
                    f"{a} 与 {b} 共有 {block.size} 字逐字相同的片段（共同任务书之外）：…{ctx}…")
    return warns


# ---------------------------------------------------------------- claims

def unsupported_claims(text: str, where: str) -> list[str]:
    lines = text.splitlines()
    out: list[str] = []
    for number, line in enumerate(lines, 1):
        if not CLAIM.search(line):
            continue
        window = "\n".join(lines[max(0, number - 3):number + 1])
        if QUOTE_MARK.search(window) or ARTIFACT_MARK.search(window):
            continue
        out.append(f"{where}:{number} 断言「{line.strip()[:60]}」附近没有引文、定位或产物路径")
    return out


# ---------------------------------------------------------------- sampling

def sample_sheet(portfolio: dict[str, Any], k: int, seed: int) -> list[str]:
    sources = [s for s in portfolio.get("sources", [])
               if isinstance(s, dict) and s.get("checked") is True]
    claims_by_source: dict[str, list[str]] = {}
    for cand in portfolio.get("candidates", []):
        if not isinstance(cand, dict):
            continue
        for ref in cand.get("evidence", []) or []:
            if isinstance(ref, dict) and ref.get("source_id"):
                claims_by_source.setdefault(ref["source_id"], []).append(
                    f"{cand.get('id')}: {(ref.get('supports') or '')[:70]}")
    rng = random.Random(seed)
    picked = rng.sample(sources, min(k, len(sources))) if sources else []
    out = []
    for s in picked:
        out.append(f"- [{s.get('id')}] {s.get('locator')}")
        out.append(f"  声明引用它的结论：{'; '.join(claims_by_source.get(s.get('id'), ['（未被引用）']))}")
        out.append("  动作：打开原文，定位逐字引文；核对页码/小节；判定 一致 / 部分 / 不一致 / 打不开")
    return out


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--journal", type=Path, help="journal.jsonl")
    ap.add_argument("--tracks", type=Path, help="首轮/二轮 track 文本目录")
    ap.add_argument("--portfolio", type=Path, help="portfolio.json")
    ap.add_argument("--brief", type=Path, help="共同任务书，用于排除模板重叠")
    ap.add_argument("--ignore", type=Path, action="append", default=[], help="额外排除文本")
    ap.add_argument("--min-len", type=int, default=20, help="泄漏判定的最短逐字长度")
    ap.add_argument("--sample", type=int, default=2, help="抽检来源条数")
    ap.add_argument("--seed", type=int, default=None, help="抽检随机种子（审计时决定）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    errors: list[str] = []
    warns: list[str] = []
    sheet: list[str] = []

    if args.journal:
        events = [json.loads(l) for l in read(args.journal).splitlines() if l.strip()]
        errors += check_journal(events)

    if args.tracks:
        files = {p.name: read(p) for p in sorted(args.tracks.glob("*.md"))}
        ignore = ""
        if args.brief:
            ignore += norm(read(args.brief))
        for extra in args.ignore:
            ignore += norm(read(extra))
        warns += leakage(files, ignore, args.min_len)
        for name, text in files.items():
            warns += unsupported_claims(text, name)

    if args.portfolio:
        portfolio = json.loads(read(args.portfolio))
        cited = {ref.get("source_id")
                 for cand in portfolio.get("candidates", []) if isinstance(cand, dict)
                 for ref in (cand.get("evidence") or []) if isinstance(ref, dict)}
        for src in portfolio.get("sources", []):
            if isinstance(src, dict) and src.get("checked") is True and src.get("id") not in cited:
                warns.append(f"{src.get('id')}: 标记已核对但未被任何候选引用；若只用于排除路线请写明排除了什么")
        for cand in portfolio.get("candidates", []):
            if not isinstance(cand, dict):
                continue
            if cand.get("verification", {}).get("result") == "pass" and not cand.get("discriminator"):
                warns.append(f"{cand.get('id')}: 声称通过与基线比较，但没有写判别性观察")
        sheet = sample_sheet(portfolio, args.sample, args.seed if args.seed is not None else 0)

    result = {"errors": errors, "warnings": warns, "sample": sheet}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"硬错误 {len(errors)} 条；提醒 {len(warns)} 条")
        for e in errors:
            print("错误：" + e)
        for w in warns:
            print("提醒：" + w)
        if sheet:
            print("\n抽检清单（本次随机种子：" + str(args.seed if args.seed is not None else 0) + "）")
            print("\n".join(sheet))
        print("\n机械检查不能证明结论正确；它只让「没干活」比「干活」更贵。")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
