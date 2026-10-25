#!/usr/bin/env python3
"""Optional probe-battery check for divergent-research portfolios.

Reads the same portfolio.json as check_portfolio.py, plus two optional blocks:

  "probes": [{"id": "P1", "intervention": "把输入顺序随机打乱", "question": "成功率下降超过 5 个百分点吗"}]
  "candidates"[i]["claimed_cause"] = "该机制声称的因果载体（一句话）"
  "candidates"[i]["predictions"] = {"P1": "degrade"}

Prediction domain: improve / degrade / no-change / unknown.

A "signature" is the tuple of a candidate's predictions over the fixed probe
battery. Two candidates with the same signature are NOT PROVEN to share a
mechanism; they are merely *indistinguishable by the battery*. That is the only
claim this script makes. It never reads the web and never judges truth.

Exit codes: 0 = no structural error; 1 = structural error, or (--strict) a
degenerate battery; 2 = unreadable file.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

VALUES = ("improve", "degrade", "no-change", "unknown")
UNKNOWN = "unknown"


def filled(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalize(text: str) -> str:
    """Casefold, drop punctuation/space, keep letters+digits (CJK kept as-is)."""
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in text if ch.isalnum())


def shingles(text: str, k: int = 3) -> set[str]:
    norm = normalize(text)
    if len(norm) <= k:
        return {norm} if norm else set()
    return {norm[i : i + k] for i in range(len(norm) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def inspect_coverage(data: Any, near_dup: float = 0.0) -> dict[str, Any]:
    """near_dup > 0 enables the lexical screen; it is OFF by default on purpose.

    Measured on Chinese one-sentence mechanism descriptions (this track, 2026-10-25):
    a true paraphrase scored 0.132 and a shared-vocabulary/different-mechanism pair
    scored 0.150, i.e. the screen has no separating power there. It stays available
    for long English text only, and is never a merge criterion.
    """
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return {"errors": ["顶层必须是 JSON 对象"], "warnings": [], "stats": {}}

    probes = data.get("probes")
    candidates = data.get("candidates")
    if not isinstance(probes, list) or not probes:
        return {"errors": ["probes: 需要非空数组（判别探针组）"], "warnings": [], "stats": {}}
    if not isinstance(candidates, list) or not candidates:
        return {"errors": ["candidates: 需要非空数组"], "warnings": [], "stats": {}}

    probe_ids: list[str] = []
    for n, probe in enumerate(probes, 1):
        where = f"probes[{n}]"
        if not isinstance(probe, dict):
            errors.append(f"{where}: 必须是对象")
            continue
        pid = probe.get("id")
        if not filled(pid):
            errors.append(f"{where}.id: 缺失")
        elif pid in probe_ids:
            errors.append(f"{where}.id: 重复 {pid}")
        else:
            probe_ids.append(pid)
        if not filled(probe.get("intervention")):
            errors.append(f"{where}.intervention: 必须写出可施加的改变")

    sigs: dict[str, tuple[str, ...]] = {}
    claimed: dict[str, str] = {}
    for n, cand in enumerate(candidates, 1):
        cid = cand.get("id") if isinstance(cand, dict) else None
        cid = cid if filled(cid) else f"unknown-{n}"
        if not isinstance(cand, dict):
            errors.append(f"candidates[{n}]: 必须是对象")
            continue
        preds = cand.get("predictions")
        if not isinstance(preds, dict):
            warnings.append(f"{cid}: 没有 predictions，无法计算签名")
            continue
        for key, value in preds.items():
            if key not in probe_ids:
                errors.append(f"{cid}.predictions.{key}: 未定义的探针")
            if value not in VALUES:
                errors.append(f"{cid}.predictions.{key}: 取值应为 {'/'.join(VALUES)}")
        sigs[cid] = tuple(str(preds.get(pid, UNKNOWN)) for pid in probe_ids)
        if filled(cand.get("claimed_cause")):
            claimed[cid] = cand["claimed_cause"]

    def definite(sig: tuple[str, ...]) -> bool:
        return any(v != UNKNOWN for v in sig)

    # 1. identical signatures = indistinguishable within the battery
    groups: dict[tuple[str, ...], list[str]] = {}
    for cid, sig in sigs.items():
        if definite(sig):
            groups.setdefault(sig, []).append(cid)
    collision_pairs: list[str] = []
    for sig, ids in sorted(groups.items()):
        if len(ids) > 1:
            collision_pairs.append(", ".join(sorted(ids)))
            warnings.append(
                "签名相同（在现有探针下不可区分）：" + ", ".join(sorted(ids))
                + "；应作为同一族处理，或补充能分开它们的探针"
            )

    distinct = len(groups)
    # 2. consensus probes = shared, untested assumption
    consensus: list[str] = []
    uncovered: list[str] = []
    for idx, pid in enumerate(probe_ids):
        vals = [sigs[cid][idx] for cid in sigs if definite(sigs[cid])]
        known = {v for v in vals if v != UNKNOWN}
        if not known:
            uncovered.append(pid)
            warnings.append(f"探针 {pid}: 没有任何候选给出确定预测——无人区分它")
        elif len(known) == 1 and len(vals) >= 2:
            consensus.append(pid)
            warnings.append(
                f"探针 {pid}: 所有候选预测一致（{next(iter(known))}），"
                "这是共同盲点，下一轮应专门检验它"
            )

    # 3. claimed cause duplication (exact after normalization)
    by_cause: dict[str, list[str]] = {}
    for cid, cause in claimed.items():
        by_cause.setdefault(normalize(cause), []).append(cid)
    for key, ids in by_cause.items():
        if len(ids) > 1:
            warnings.append("声称的因果载体相同：" + ", ".join(sorted(ids)) + "；视为同一族")
    # 4. lexical near-duplicate screen (off unless near_dup > 0; never a verdict)
    items = [(cid, shingles(claimed[cid])) for cid in sorted(claimed)]
    near: list[str] = []
    for i in range(len(items)) if near_dup > 0 else []:
        for j in range(i + 1, len(items)):
            (a, sa), (b, sb) = items[i], items[j]
            score = jaccard(sa, sb)
            if score >= near_dup:
                near.append(f"{a}~{b}:{score:.2f}")
                warnings.append(
                    f"{a} 与 {b} 的因果表述相似度 {score:.2f}（字符 3-gram Jaccard）——"
                    "仅用于筛查，是否同族以探针签名为准"
                )

    stats = {
        "probes": len(probe_ids),
        "candidates_with_predictions": len(sigs),
        "distinct_signatures": distinct,
        "signature_collisions": len(collision_pairs),
        "consensus_probes": len(consensus),
        "uncovered_probes": len(uncovered),
        "near_duplicate_pairs": len(near),
    }
    return {
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
        "consensus_probes": consensus,
        "uncovered_probes": uncovered,
        "collisions": collision_pairs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portfolio", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--near-dup",
        type=float,
        default=0.0,
        help="字符 3-gram Jaccard 阈值；默认关闭，中文短句上实测无区分度",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="签名单一、签名碰撞或存在无人区分的探针时返回 1",
    )
    args = parser.parse_args()
    try:
        data = json.loads(args.portfolio.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"读取失败：{exc}", file=sys.stderr)
        return 2

    result = inspect_coverage(data, args.near_dup)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key, value in result["stats"].items():
            print(f"{key}: {value}")
        for item in result["errors"]:
            print(f"错误：{item}")
        for item in result["warnings"]:
            print(f"提醒：{item}")
        if not result["errors"]:
            print("探针检查完成；相同签名只表示“当前探针下不可区分”，不等于机制相同。")

    if result["errors"]:
        return 1
    stats = result["stats"]
    if args.strict and (
        stats.get("distinct_signatures", 0) <= 1
        or stats.get("signature_collisions", 0)
        or stats.get("uncovered_probes", 0)
    ):
        print("严格模式：多样性退化（签名单一/碰撞/探针无人区分）。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())