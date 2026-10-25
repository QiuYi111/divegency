#!/usr/bin/env python3
"""Check a divergent-research portfolio's structure and declared coverage.

No web access, model calls, or semantic similarity checks. A passed check does
NOT certify factual correctness, independence, or actual experimental results.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any


MODES = {"facts", "decision", "design", "algorithm"}
SOURCE_KINDS = {"primary", "secondary", "experiment"}
RESULTS = {"not-run", "pass", "fail", "inconclusive"}


def filled(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def checked_list(value: Any, where: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{where}: 必须是数组")
        return []
    return value


def inspect(data: Any) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return {"errors": ["文件顶层必须是 JSON 对象"], "warnings": [], "stats": {}}

    if not filled(data.get("goal")):
        errors.append("goal: 需要完整任务目标")
    if data.get("mode") not in MODES:
        errors.append(f"mode: 应为 {', '.join(sorted(MODES))} 之一")

    directions = checked_list(data.get("directions"), "directions", errors)
    sources = checked_list(data.get("sources"), "sources", errors)
    candidates = checked_list(data.get("candidates"), "candidates", errors)

    direction_ids: set[str] = set()
    for number, entry in enumerate(directions, 1):
        where = f"directions[{number}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: 必须是对象")
            continue
        key = entry.get("id")
        if not filled(key):
            errors.append(f"{where}.id: 缺失")
        elif key in direction_ids:
            errors.append(f"{where}.id: 重复 {key}")
        else:
            direction_ids.add(key)
        if not filled(entry.get("lens")):
            errors.append(f"{where}.lens: 缺失宽泛方向")
    if not direction_ids:
        warnings.append("没有可用方向，无法判断搜索覆盖")

    source_ids: dict[str, dict[str, Any]] = {}
    for number, entry in enumerate(sources, 1):
        where = f"sources[{number}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: 必须是对象")
            continue
        key = entry.get("id")
        if not filled(key):
            errors.append(f"{where}.id: 缺失")
        elif key in source_ids:
            errors.append(f"{where}.id: 重复 {key}")
        else:
            source_ids[key] = entry
        if not filled(entry.get("locator")):
            errors.append(f"{where}.locator: 缺少原始链接或本地路径")
        if entry.get("kind") not in SOURCE_KINDS:
            errors.append(f"{where}.kind: 类型无效")
        if not isinstance(entry.get("checked"), bool):
            errors.append(f"{where}.checked: 必须为 true 或 false")

    candidate_ids: set[str] = set()
    mechanism_groups: dict[str, list[str]] = defaultdict(list)
    direction_to_mechanisms: dict[str, set[str]] = defaultdict(set)
    covered_directions: set[str] = set()
    documented_mechanisms: set[str] = set()
    claimed_pass_mechanisms: set[str] = set()

    for number, entry in enumerate(candidates, 1):
        where = f"candidates[{number}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: 必须是对象")
            continue
        key = entry.get("id")
        if not filled(key):
            errors.append(f"{where}.id: 缺失")
            key = f"unknown-{number}"
        elif key in candidate_ids:
            errors.append(f"{where}.id: 重复 {key}")
        candidate_ids.add(key)

        direction = entry.get("direction_id")
        if direction not in direction_ids:
            errors.append(f"{where}.direction_id: 未定义方向 {direction!r}")
        else:
            covered_directions.add(direction)

        for field in ("summary", "mechanism", "mechanism_key"):
            if not filled(entry.get(field)):
                errors.append(f"{where}.{field}: 必须填写")
        family = entry.get("mechanism_key")
        family = family.strip().casefold() if filled(family) else ""
        if family:
            mechanism_groups[family].append(key)
            if direction in direction_ids:
                direction_to_mechanisms[direction].add(family)

        evidence = checked_list(entry.get("evidence"), f"{where}.evidence", errors)
        has_checked_primary = False
        if not evidence:
            warnings.append(f"{key}: 没有附带证据")
        for e_num, ref in enumerate(evidence, 1):
            e_where = f"{where}.evidence[{e_num}]"
            if not isinstance(ref, dict):
                errors.append(f"{e_where}: 必须是对象")
                continue
            sid = ref.get("source_id")
            if not filled(sid) or sid not in source_ids:
                errors.append(f"{e_where}.source_id: 未定义来源 {sid!r}")
            else:
                source = source_ids[sid]
                if source.get("checked") is True and source.get("kind") in {"primary", "experiment"}:
                    has_checked_primary = True
            if not filled(ref.get("supports")):
                warnings.append(f"{key}: 证据 {e_num} 没写明支持的具体结论")
        if family and has_checked_primary:
            documented_mechanisms.add(family)

        for field in ("assumptions", "failure_cases"):
            details = checked_list(entry.get(field), f"{where}.{field}", errors)
            if not any(filled(item) for item in details):
                warnings.append(f"{key}: {field} 为空，可能遗漏假设或反例")

        verification = entry.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{where}.verification: 必须是对象")
            continue
        result = verification.get("result")
        if result not in RESULTS:
            errors.append(f"{where}.verification.result: 类型无效")
        if not filled(verification.get("method")):
            warnings.append(f"{key}: 未说明验证方法")
        if not filled(verification.get("criterion")):
            warnings.append(f"{key}: 未说明验证通过条件")
        if result == "pass":
            if not filled(verification.get("artifact")):
                errors.append(f"{key}: 声称通过测试但没有可复查的原始记录位置")
            if family:
                claimed_pass_mechanisms.add(family)

    gaps = sorted(direction_ids - covered_directions)
    if gaps:
        warnings.append(f"方向无候选：{', '.join(gaps)}")
    for family, ids in sorted(mechanism_groups.items()):
        if len(ids) > 1:
            warnings.append(f"同一机制标识 {family!r} 出现多次：{', '.join(ids)}；需人工核对是否重复")
    if len(direction_to_mechanisms) > 1:
        common = set.intersection(*direction_to_mechanisms.values())
        distinct = set.union(*direction_to_mechanisms.values())
        if common and common == distinct:
            warnings.append("多条研究方向只产出了同一机制族，建议重新设计下一轮方向")

    stats = {
        "directions": len(direction_ids),
        "covered_directions": len(covered_directions),
        "uncovered_directions": gaps,
        "candidates": len(candidate_ids),
        "declared_mechanism_families": len(mechanism_groups),
        "families_with_checked_primary_evidence": len(documented_mechanisms),
        "families_claiming_passed_tests": len(claimed_pass_mechanisms),
    }
    return {"errors": errors, "warnings": warnings, "stats": stats}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portfolio", type=Path, help="JSON 方案库文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出检查结果")
    args = parser.parse_args()

    try:
        data = json.loads(args.portfolio.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"读取方案库失败：{exc}", file=sys.stderr)
        return 2

    result = inspect(data)
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
            print("结构检查通过；并不代表引用、原理和测试结果真实或正确。")
    return 2 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
