#!/usr/bin/env python3
"""Run many worker agents in parallel, one job per directory.

usage: python race_runner.py jobs.json [--parallel 25] [--attempts 6] [--backoff 300]

jobs.json is a list of {"id", "cwd", "prompt"}; optional per job:
  "deliverables": ["REPORT.md", ...]  first existing file wins (default below)
  "min_chars": 800                     shortest acceptable deliverable

The worker command reads the prompt on stdin and runs with cwd = job["cwd"].
Set it with RACE_WORKER_CMD (shell-split), e.g.
  RACE_WORKER_CMD='dsh --profile headless --json -'
Load credentials into the environment before starting; this script never reads
or prints them.

Lessons baked in (see references/runner-pitfalls.md):
- stdout goes to a file, not a pipe, and each worker runs in its own session
  that is killed afterwards: servers or headless browsers a worker leaves behind
  would otherwise hold the pipe open and block this runner forever.
- retries wait longer each time: model-API outages can last tens of minutes.
- the "done" marker (out/<id>.md) is written only on success, so a partial
  reply never makes the next run skip the job.
- the deliverable file decides success, not the worker's last message; it must
  be newer than this attempt's start, so a template file left in the directory
  cannot pass as a fresh report.
"""
import argparse
import json
import os
import pathlib
import shlex
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_DELIVERABLES = ["REPORT.md", "GAPS.md", "EVIDENCE.md"]
RESUME_NOTE = ("\n\n（续跑：上一轮因接口中断或超时停止，不是你的问题。当前目录可能已有你上一轮的产物，"
               "请先检查、在此基础上继续，不要从头重写；完成后写交付文件并给出最终回复。）")


def worker_cmd():
    raw = os.environ.get("RACE_WORKER_CMD")
    if not raw:
        sys.exit("set RACE_WORKER_CMD, e.g. RACE_WORKER_CMD='dsh --profile headless --json -'")
    return shlex.split(raw)


def run_once(job, attempt, root, timeout):
    logf = root / "logs" / f"{job['id']}.{attempt}.log"
    t0 = time.time()
    prompt = job["prompt"] + (RESUME_NOTE if attempt > 1 else "")
    with open(logf, "w") as out:
        proc = subprocess.Popen(worker_cmd(), stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT,
                                cwd=job["cwd"], text=True, start_new_session=True)
        try:
            proc.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        try:  # clean up anything the worker left running
            os.killpg(proc.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    return proc.returncode, t0


def deliverable(job, started):
    for name in job.get("deliverables", DEFAULT_DELIVERABLES):
        p = pathlib.Path(job["cwd"]) / name
        if p.exists() and p.stat().st_mtime >= started:
            return p.read_text(errors="replace")
    return ""


def run(job, root, args):
    done = root / "out" / f"{job['id']}.md"
    for attempt in range(1, args.attempts + 1):
        code, started = run_once(job, attempt, root, args.timeout)
        text = deliverable(job, started)
        ok = text.lstrip().startswith("#") and len(text) >= job.get("min_chars", 800)
        rec = {"id": job["id"], "attempt": attempt, "ok": ok, "exit": code,
               "secs": int(time.time() - started), "chars": len(text)}
        with open(root / "logs" / "runs.jsonl", "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        if ok:
            done.write_text(text)  # only success marks the job done
            return rec
        if attempt < args.attempts:
            time.sleep(args.backoff * attempt)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs")
    ap.add_argument("--parallel", type=int, default=25)
    ap.add_argument("--attempts", type=int, default=6)
    ap.add_argument("--backoff", type=int, default=300, help="seconds; wait = backoff * attempt")
    ap.add_argument("--timeout", type=int, default=10800, help="seconds per attempt")
    args = ap.parse_args()
    jobs_path = pathlib.Path(args.jobs).resolve()
    root = jobs_path.parent
    (root / "out").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    jobs = json.loads(jobs_path.read_text())
    todo = [j for j in jobs if not (root / "out" / f"{j['id']}.md").exists()]
    with ThreadPoolExecutor(args.parallel) as ex:
        results = list(ex.map(lambda j: run(j, root, args), todo))
    print("done", sum(r["ok"] for r in results), "/", len(results))


if __name__ == "__main__":
    main()
