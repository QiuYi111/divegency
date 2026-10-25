#!/usr/bin/env python3
"""Check a divergent-research portfolio's structure and declared coverage.

No web access, model calls, or semantic checks. A passed check does NOT certify
factual correctness, independence, or that experiments really ran.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse


MODES = {"facts", "decision", "design", "algorithm"}
SOURCE_KINDS = {"primary", "secondary", "experiment"}
RESULTS = {"not-run", "pass", "fail", "inconclusive"}
EVALUATORS = {"self", "independent"}
PREDICTIONS = {"up", "down", "no-change", "unknown"}
BUDGETS = {"quick", "standard", "deep"}


def filled(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def checked_list(value: Any, where: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{where}: 必须是数组")
        return []
    return value


def is_url(text: str) -> bool:
    parsed = urlparse(text)
    return parsed.scheme in {"http", "https"}


def normalize(text: str) -> str:
    return " ".join(text.split())


def local_artifact(root: Path | None, artifact: str) -> Path | None:
    """Resolve a local artifact path; None for URLs or when no root is known."""
    if not artifact.strip() or is_url(artifact):
        return None
    path = Path(artifact).expanduser()
    if not path.is_absolute():
        if root is None:
            return None
        path = root / path
    return path


def inspect(data: Any, root: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return {"errors": ["文件顶层必须是 JSON 对象"], "warnings": [], "stats": {}}

    if not filled(data.get("goal")):
        errors.append("goal: 需要完整任务目标")
    if data.get("mode") not in MODES:
        errors.append(f"mode: 应为 {', '.join(sorted(MODES))} 之一")
    if "budget" in data and data.get("budget") not in BUDGETS:
        warnings.append("budget: 应为 quick/standard/deep 之一")
    if "root" in data:  # 常见笔误
        warnings.append("顶层疑似误用 root，未定义该字段")

    probes: dict[str, dict[str, Any]] = {}
    for number, entry in enumerate(checked_list(data.get("probes", []), "probes", errors), 1):
        where = f"probes[{number}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: 必须是对象")
            continue
        key = entry.get("id")
        if not filled(key):
            errors.append(f"{where}.id: 缺失")
        elif key in probes:
            errors.append(f"{where}.id: 重复 {key}")
        else:
            probes[key] = entry
        if not filled(entry.get("intervention")):
            warnings.append(f"{where}.intervention: 未写明施加什么改变")
        if not filled(entry.get("question")):
            warnings.append(f"{where}.question: 未写明观察什么")

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
        if entry.get("checked") is True:
            if not filled(entry.get("where")):
                errors.append(f"{where}: checked=true 但缺少 where（页/节/行）；只见到摘要应写 false")
            quote = entry.get("quote")
            if not filled(quote) or len(str(quote).strip()) < 8:
                errors.append(f"{where}: checked=true 但缺少 quote（≥8 字的逐字原文）")
            snapshot = entry.get("snapshot")
            if filled(snapshot) and root is not None:
                snap_path = Path(str(snapshot)).expanduser()
                if not snap_path.is_absolute():
                    snap_path = root / snap_path
                if not snap_path.exists():
                    warnings.append(f"{where}: snapshot 不存在：{snapshot}")
                elif filled(quote):
                    try:
                        haystack = normalize(snap_path.read_text(encoding="utf-8", errors="ignore"))
                    except OSError:
                        haystack = ""
                    if normalize(str(quote)) not in haystack:
                        errors.append(f"{where}: quote 在 snapshot 中找不到逐字匹配：{snapshot}")

    candidate_ids: set[str] = set()
    mechanism_groups: dict[str, list[str]] = defaultdict(list)
    direction_to_mechanisms: dict[str, set[str]] = defaultdict(set)
    covered_directions: set[str] = set()
    documented_mechanisms: set[str] = set()
    claimed_pass_mechanisms: set[str] = set()
    evidence_sources: set[str] = set()
    pass_artifacts: list[str] = []
    checked_by_candidate: dict[str, bool] = {}

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

        predictions = entry.get("predictions")
        if probes and not isinstance(predictions, dict):
            errors.append(f"{where}.predictions: 已声明判别问题，所有候选都必须给出预测")
        if predictions is not None:
            if not isinstance(predictions, dict):
                errors.append(f"{where}.predictions: 必须是对象")
            else:
                for probe_id, value in predictions.items():
                    if probes and probe_id not in probes:
                        errors.append(f"{where}.predictions: 未定义判别问题 {probe_id!r}")
                    if value not in PREDICTIONS:
                        errors.append(f"{where}.predictions.{probe_id}: 取值为 {', '.join(sorted(PREDICTIONS))}")

        differentiation = checked_list(entry.get("differentiation", []), f"{where}.differentiation", errors)
        for d_num, diff in enumerate(differentiation, 1):
            d_where = f"{where}.differentiation[{d_num}]"
            if not isinstance(diff, dict):
                errors.append(f"{d_where}: 必须是对象")
                continue
            if not filled(diff.get("vs")):
                errors.append(f"{d_where}.vs: 需要指出与哪条候选区分")
            if not filled(diff.get("observation")):
                errors.append(f"{d_where}.observation: 需要给出具体输入/工况/查询")
            elif len(str(diff["observation"]).strip()) < 12:
                warnings.append(f"{d_where}.observation: 太短，可能不是可执行的观察")
            self_pred = diff.get("prediction_self")
            other_pred = diff.get("prediction_other")
            if not filled(self_pred) or not filled(other_pred):
                errors.append(f"{d_where}: 需要 prediction_self 与 prediction_other（两方预测必须不同）")
            elif str(self_pred).strip().casefold() == str(other_pred).strip().casefold():
                errors.append(f"{d_where}: prediction_self 与 prediction_other 相同，不构成判别性观察")

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
                continue
            evidence_sources.add(sid)
            source = source_ids[sid]
            ok = source.get("checked") is True and source.get("kind") in {"primary", "experiment"} and filled(ref.get("supports"))
            if ok:
                has_checked_primary = True
            if not filled(ref.get("supports")):
                warnings.append(f"{key}: 证据 {e_num} 没写明支持的具体结论")
        checked_by_candidate[key] = has_checked_primary
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
        evaluator = verification.get("evaluator")
        if evaluator not in EVALUATORS:
            warnings.append(f"{key}: verification.evaluator 应为 self 或 independent")
        if result == "pass":
            artifact = verification.get("artifact")
            if not filled(artifact):
                errors.append(f"{key}: 声称通过测试但没有可复查的原始记录位置")
            else:
                local = local_artifact(root, str(artifact))
                if is_url(str(artifact)):
                    warnings.append(f"{key}: artifact 是外部链接，未离线核验；复核者需打开确认")
                elif local is None:
                    warnings.append(f"{key}: artifact 无法核验（检查时未提供根目录）")
                    pass_artifacts.append((key, str(artifact)))
                elif not local.exists():
                    errors.append(f"{key}: artifact 指向不存在的文件：{artifact}")
                elif local.is_file() and local.stat().st_size == 0:
                    errors.append(f"{key}: artifact 是空文件：{artifact}")
                else:
                    pass_artifacts.append((key, str(local.resolve())))
            if evaluator == "self":
                warnings.append(f"{key}: 自测通过；措辞不得写“已证明优于基线”")
            if not has_checked_primary:
                errors.append(f"{key}: 声称通过测试，但没有已核实的一手证据或实验记录")
            if family:
                claimed_pass_mechanisms.add(family)

    gaps = sorted(direction_ids - covered_directions)
    if gaps:
        warnings.append(f"方向无候选：{', '.join(gaps)}")
    for family, ids in sorted(mechanism_groups.items()):
        if len(ids) > 1:
            warnings.append(f"同一机制标识 {family!r} 出现多次：{', '.join(ids)}；需人工核对是否重复")
    for family, ids in sorted(mechanism_groups.items()):
        if family in documented_mechanisms:
            thin = [cid for cid in ids if not checked_by_candidate.get(cid)]
            if thin:
                warnings.append(f"机制族 {family!r} 中 {', '.join(thin)} 没有已核实的一手证据，族证据链不完整")
    if len(direction_to_mechanisms) > 1:
        common = set.intersection(*direction_to_mechanisms.values())
        distinct = set.union(*direction_to_mechanisms.values())
        if common and common == distinct:
            warnings.append("多条研究方向只产出了同一机制族，建议重新设计下一轮方向")

    finalists = checked_list(data.get("finalists", []), "finalists", errors)
    if finalists:
        if len(finalists) < 2:
            warnings.append("finalists 少于两条，无法做两两判别")
        for fid in finalists:
            if fid not in candidate_ids:
                errors.append(f"finalists: 未定义候选 {fid!r}")
        by_id = {c.get("id"): c for c in candidates if isinstance(c, dict)}
        for i, first in enumerate(finalists):
            for second in finalists[i + 1:]:
                if first not in by_id or second not in by_id:
                    continue
                def witness(src: str, dst: str) -> bool:
                    for diff in by_id[src].get("differentiation", []) or []:
                        if isinstance(diff, dict) and diff.get("vs") == dst and filled(diff.get("observation")):
                            return True
                    return False
                if not witness(first, second) or not witness(second, first):
                    errors.append(f"finalists: {first} 与 {second} 缺少双向判别性观察，不能宣称原理不同")

    by_artifact: dict[str, list[str]] = defaultdict(list)
    for candidate_id, artifact in pass_artifacts:
        by_artifact[artifact].append(candidate_id)
    for artifact, ids in sorted(by_artifact.items()):
        if len(ids) > 1:
            warnings.append(f"{', '.join(ids)} 共用同一 artifact（{artifact}）：一次运行不能同时证明多个候选")

    id_to_family = {cid: fam for fam, ids in mechanism_groups.items() for cid in ids}
    signatures: dict[tuple[str, ...], list[str]] = defaultdict(list)
    if probes:
        ordered = sorted(probes)
        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            preds = entry.get("predictions")
            if isinstance(preds, dict) and all(p in preds for p in ordered):
                signatures[tuple(str(preds[p]) for p in ordered)].append(str(entry.get("id")))
        for signature, ids in signatures.items():
            if len(ids) > 1:
                families = {id_to_family.get(cid) for cid in ids}
                if len(families) > 1:
                    errors.append(f"同一预测签名 {signature} 却标为不同机制族：{', '.join(ids)}；这是换名，合并或补一条能分开的判别问题")
                else:
                    warnings.append(f"同一预测签名 {signature}：{', '.join(ids)}；按同一族处理")
        if len(candidates) > 1 and len(signatures) < 2 and len(signatures) > 0:
            warnings.append("所有候选在现有判别问题上签名相同，多样性不足")

    dead_ends = checked_list(data.get("dead_ends", []), "dead_ends", errors)
    for number, entry in enumerate(dead_ends, 1):
        where = f"dead_ends[{number}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: 必须是对象")
            continue
        for field in ("route", "why"):
            if not filled(entry.get(field)):
                errors.append(f"{where}.{field}: 必须填写")

    if len(candidate_ids) >= 3 and len(evidence_sources) == 1:
        warnings.append("所有候选只引用同一个来源，证据面可能过窄")
    if data.get("budget") in {"standard", "deep"} and (len(direction_ids) < 3 or len(candidate_ids) < 3):
        warnings.append("档位是 standard/deep，但方向或候选少于 3 个：先确认是问题真的窄，还是覆盖不足")

    stats = {
        "directions": len(direction_ids),
        "covered_directions": len(covered_directions),
        "uncovered_directions": gaps,
        "candidates": len(candidate_ids),
        "declared_mechanism_families": len(mechanism_groups),
        "families_with_checked_primary_evidence": len(documented_mechanisms),
        "families_claiming_passed_tests": len(claimed_pass_mechanisms),
        "distinct_prediction_signatures": len(signatures) if probes else 0,
        "dead_ends": len(dead_ends),
    }
    return {"errors": errors, "warnings": warnings, "stats": stats}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portfolio", type=Path, help="JSON 方案库文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出检查结果")
    parser.add_argument("--strict", action="store_true", help="把提醒也视为失败（退出码 2）")
    args = parser.parse_args()

    try:
        data = json.loads(args.portfolio.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"读取方案库失败：{exc}", file=sys.stderr)
        return 2

    result = inspect(data, root=args.portfolio.resolve().parent)
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
    failed = bool(result["errors"]) or (args.strict and bool(result["warnings"]))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
