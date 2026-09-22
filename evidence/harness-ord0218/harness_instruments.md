# HARNESS instruments behind the published receipts

Every receipt in `harness_streak_bundle.json` was produced by one of these files, on a
`git archive` export of the SHA named inside it.  They are inlined so an auditor without
this machine can re-run and compare digests.  No product file is included or modified.

Re-run recipe (one line each, from the repo that holds `lab/`):

```text
python lab/tools/harness_streak_gate.py --head 56d20ec --runs 10 --target all \
    --single tests/test_qoder_anywhere_gates.py::test_g5_an_ai_run_that_changed_must_say_which_it_was \
    --classify test_g5_,test_g3_
python lab/tools/harness_gate_streak_selftest.py --head 522c414 --runs 10
python lab/tools/harness_instrument_streak.py --head 522c414 --runs 10
python lab/tools/harness_phrase_coverage_004.py --head 522c414 --export lab/snap_522c414 --run-tag s1
python lab/tools/harness_promotion_killtest.py --export lab/snap_522c414
python lab/tools/digest_teeth_check.py          # proves the digests are not deaf
```

## `harness_streak_gate.py`  (11913 B)

```python
"""GATE_ACCEPTANCE_STREAK runner (arbiter `5773071703` @15:58, frozen by commander 16:0x).

The eight frozen conditions, and how this runner satisfies each one *by construction*:

  1 exact same product/test SHA      -> one export of one SHA; every process runs inside it
  2 10 CONSECUTIVE independent procs -> N subprocesses, sequential, one attempt each
  3 fresh app-resolved temp DB       -> `CITYNEXUS_DATABASE_URL` is deliberately NOT set, so the
                                        suite's own ORD-0211 conftest mints a temp DB per process
  4 receipt per run                  -> run_index, exit_code, resolved absolute db path (the
                                        suite's own report-header line), initial + final row counts
                                        (via `-p cnx_run_receipt`)
  5 all 10 runs GREEN                -> counted and reported; NOT manufactured
  6 no sleep/retry/backoff/concurrency reduction/expectation relaxation
                                     -> no `sleep`, no re-run of a failed index, the test's own
                                        5-way ThreadPoolExecutor untouched, no marker/flag that
                                        changes expectations, `--tb=line` only
  7 no two runs silently share a temp DB path -> the 10 resolved paths are compared and reported
  8 one isolated GREEN is observation only     -> this script never writes a verdict word; it
                                        prints counts and leaves closure to the receipt reader

Two targets, both on the same SHA, because the frozen rule needs both readings:
  A) the single node id  -> what the concurrency/timing actually does
  B) the whole file      -> whether a streak is even reachable while an unrelated red lives in it

Usage:  python lab/tools/harness_streak_gate.py [--target node|file|both] [--runs 10]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
PLUGINS = LAB / "plugins"
TARGET_FILE = "tests/test_qoder_anywhere_gates.py"
MOD = "tests/test_qoder_anywhere_gates.py::"
# the two doors that run before g3 in file order; they are what a lone g3 does not have
PRECEDING = [MOD + "test_g1_destination_capability_comes_from_the_backend_not_from_a_count",
             MOD + "test_g2_an_existing_journey_becomes_plannable_without_being_recreated"]
TARGET_NODE = ("tests/test_qoder_anywhere_gates.py::"
               "test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation")
HEADER_RE = re.compile(r"ORD-0211 test database: resolved=(.+?) \| exists=(\S+) \| declared_by=(\S+)")
INITIAL_RE = re.compile(r"RUN_RECEIPT_INITIAL (\{.*\})")
OUTCOME_RE = re.compile(r"RUN_RECEIPT_OUTCOMES (\{.*\})")
SHAPES = {
    "A-single-node": "single-node",
    "B-whole-file": "whole-file",
    "C-preceding-doors-in-one-process": "node-with-preceding-doors-in-one-process",
    "C-g1+g2+g3-in-one-process": "node-with-preceding-doors-in-one-process",
}
FINAL_RE = re.compile(r"RUN_RECEIPT_FINAL (\{.*\})")


def one_run(tree: Path, target: str, index: int, env: dict) -> dict:
    # `target` may be one node id, a file, or a list of them (an ordered set of doors in ONE process)
    selected = target if isinstance(target, list) else [target]
    cmd = [str(PY), "-m", "pytest", *selected, "--tb=line", "-p", "no:cacheprovider",
           "-p", "cnx_run_receipt"]
    proc = subprocess.run(cmd, cwd=str(tree), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)
    out = proc.stdout + proc.stderr
    header = HEADER_RE.search(out)
    outcomes = None
    om = OUTCOME_RE.search(out)
    if om:
        outcomes = json.loads(om.group(1))
    initial, final = None, None
    m = INITIAL_RE.search(out)
    if m:
        initial = json.loads(m.group(1))
    m = FINAL_RE.search(out)
    if m:
        final = json.loads(m.group(1))
    summary = {}
    for pat, name in ((r"(\d+) passed", "passed"), (r"(\d+) failed", "failed"),
                      (r"(\d+) skipped", "skipped"), (r"(\d+) error", "error")):
        found = re.search(pat, out)
        summary[name] = int(found.group(1)) if found else 0
    return {
        "run_index": index,
        "exit_code": proc.returncode,
        "resolved_db_path": header.group(1) if header else None,
        "db_exists_at_header": header.group(2) if header else None,
        "declared_by": header.group(3) if header else None,
        "initial_rows": initial,
        "final_rows": final,
        "counts": summary,
        "node_outcomes": (outcomes or {}).get("outcomes"),
        "selected_count": (outcomes or {}).get("selected_count"),
        "extra_reports": (outcomes or {}).get("extra_reports"),
        "failed_node_ids": sorted({ln.split("::")[-1].split(" ")[0]
                                   for ln in out.splitlines() if ln.startswith("FAILED")}),
        # `--tb=line` prints one reason line per failure; without it a flip has no named cause
        "error_lines": [ln.strip()[:260] for ln in out.splitlines()
                        if ln.startswith("E ") or ".py:" in ln[:120]][:6],
        "ran_at": time.strftime("%H:%M:%S"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", default="56d20ec")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--single", default="", help="node id for the single-node shape")
    ap.add_argument("--classify", default="test_g3_,test_g5_",
                    help="comma-separated node fragments to classify per run")
    ap.add_argument("--target", default="both",
                    choices=["node", "file", "both", "seedthen", "all"])
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    tree = LAB / f"snap_{args.head}" / "backend"
    if not (tree / "tests" / "test_qoder_anywhere_gates.py").exists():
        print(f"no export for {args.head} at {tree}")
        return 2

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["DEEPSEEK_API_KEY"] = ""
    env["CITYNEXUS_AI_API_KEY"] = ""
    env["PYTHONPATH"] = str(PLUGINS) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"   # the assertion messages are Chinese; cp936 mangles them
    # condition 3: do NOT declare a database - the suite's own conftest must mint one per process
    env.pop("CITYNEXUS_DATABASE_URL", None)

    print(f"SHA={args.head} tree={tree} interpreter={PY} runs={args.runs} "
          f"CITYNEXUS_DATABASE_URL set? {'CITYNEXUS_DATABASE_URL' in env}")

    single = args.single or TARGET_NODE          # which door the single-node shape runs
    preceding = PRECEDING if not args.single else []   # empty for a self-contained node
    plans = []
    if args.target in ("node", "both", "all"):
        plans.append(("A-single-node", single))
    if args.target in ("file", "both", "all"):
        plans.append(("B-whole-file", TARGET_FILE))
    if args.target in ("seedthen", "all"):
        label = "C-preceding-doors-in-one-process"
        plans.append((label, (preceding + [single]) if preceding else [single]))

    result = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "sha": args.head,
              "tree": str(tree), "interpreter": str(PY), "runs_planned": args.runs, "targets": {}}

    for label, target in plans:
        runs = []
        for i in range(1, args.runs + 1):   # consecutive, one attempt each, no retry, no sleep
            runs.append(one_run(tree, target, i, env))
            r = runs[-1]
            print(f"  [{label} run {i:2}] exit={r['exit_code']} "
                  f"{r['counts']['passed']}p/{r['counts']['failed']}f "
                  f"db={'...' + (r['resolved_db_path'] or '?')[-28:]} "
                  f"rows_initial={(r['initial_rows'] or {}).get('_exists')} "
                  f"failed={','.join(x[:22] for x in r['failed_node_ids']) or '-'}")
            for line in r["error_lines"][:2]:
                print(f"        ! {line[:170]}")
        result_shape = SHAPES.get(label, label)          # condition 9
        node_ids = target if isinstance(target, list) else [target]

        def verdict_of(frag: str, run: dict) -> str:
            """The TARGET NODE's own verdict, never the container exit code."""
            table = run.get("node_outcomes")
            if isinstance(table, dict):
                for node, outcome in table.items():
                    if frag in node:
                        return outcome
                return "node_not_selected"
            if any(frag in x for x in run["failed_node_ids"]):
                return "failed"
            return "no_report"                        # missing is not green

        per_node = {}
        for frag in [f.strip() for f in args.classify.split(",") if f.strip()]:
            vs = [verdict_of(frag, r) for r in runs]
            red = sum(1 for v in vs if v in ("failed", "error"))
            green = sum(1 for v in vs if v == "passed")
            total = len(vs)
            if red == total:
                cls = f"STABLE_RED({result_shape})"
            elif green == total:
                cls = f"STABLE_GREEN({result_shape})"
            elif red and green:
                cls = f"FLIP_WITHOUT_SHARED_STATE({result_shape})"
            else:
                cls = f"UNCLASSIFIED({result_shape})"   # e.g. not selected in this shape
            per_node[frag] = {
                "verdicts": vs, "green": green, "red": red,
                "other": total - red - green,
                "red_at_runs": [i + 1 for i, v in enumerate(vs) if v in ("failed", "error")],
                "classification": cls,
            }

        paths = [r["resolved_db_path"] for r in runs]
        green = sum(1 for r in runs if r["exit_code"] == 0)
        g3_red = sum(1 for r in runs
                     if any("test_g3_" in x for x in r["failed_node_ids"]))
        result["targets"][label] = {
            "run_shape": result_shape, "target_node_ids": node_ids,
            "command": "python -m pytest " + " ".join(node_ids)
                       + " --tb=line -p no:cacheprovider -p cnx_run_receipt",
            "per_node_classification": per_node,
            "target": target, "runs": runs,
            "streak": {
                "planned": args.runs, "executed": len(runs),
                "green_count": green, "all_ten_green": green == args.runs,
                "target_g3_red_count": g3_red,
                "distinct_db_paths": len({p for p in paths if p}),
                "shared_db_path": len(paths) != len({p for p in paths if p}),
                "retry_used": False, "sleep_used": False,
                "concurrency_changed": False, "expectations_relaxed": False,
            },
        }
        for frag, info in result["targets"][label]["per_node_classification"].items():
            print(f"  [{label}] {frag}: {info['green']} green / {info['red']} red "
                  f"at runs {info['red_at_runs']} other={info['other']} => {info['classification']}")
        s = result["targets"][label]["streak"]
        print(f"  [{label}] green {s['green_count']}/{s['planned']} · distinct DB paths "
              f"{s['distinct_db_paths']} · any path shared? {s['shared_db_path']} · "
              f"g3 red in {s['target_g3_red_count']}/{s['planned']}")

    out = LAB / "evidence" / f"gate_streak_{args.head}_{args.runs}r_{time.strftime('%H%M')}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nreceipt: {out}")
    print("condition 8 reminder: counts are observations; 'closure' is not written by this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## `cnx_run_receipt.py`  (3612 B)

```python
"""Per-run DB + per-node outcome receipt (loaded with `-p`; nothing in the suite or product is edited).

Serves two frozen conditions of GATE_ACCEPTANCE_STREAK:

  condition 4  - run_index, exit_code, app-resolved absolute DB path, row counts at session start
                 and at session finish.  Read from the environment the suite's own ORD-0211
                 conftest pinned (`CITYNEXUS_DATABASE_URL`); table names are reported only when
                 non-zero so the receipt stays readable, and `_exists` / `_error` make a missing
                 or unreadable file explicit instead of silently reading as zero rows.

  condition 10 - the **target node's own verdict per run**, taken from pytest's reports, because
                 "whole-file exit code" is not a proxy for a node (arbiter `5773588112` @16:40).
                 Without this, a run that aborted during collection would look GREEN to anything
                 that only reads the failure list - the same class of error, one level down.

Outcome rule: the `call` phase decides passed/failed; a setup/teardown problem is reported as
`error`, and a node that produced no report at all is listed under `_missing_nodes` rather than
being guessed at.
"""
from __future__ import annotations

import json
import os
import sqlite3

_OUTCOMES: dict[str, str] = {}
_ORDER: list[str] = []


def _rows() -> dict:
    url = os.environ.get("CITYNEXUS_DATABASE_URL", "")
    if not url.startswith("sqlite:///"):
        return {"_non_sqlite_or_unset": url[:80] or "(unset)"}
    path = url.replace("sqlite:///", "", 1)
    if not os.path.exists(path):
        return {"_exists": False, "db": path}
    try:
        conn = sqlite3.connect(f"file:{path.replace(chr(92), '/')}?mode=ro", uri=True, timeout=3)
    except sqlite3.Error as exc:
        return {"_error": str(exc)[:120], "db": path}
    try:
        out = {"_exists": True, "db": path}
        for (table,) in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            try:
                n = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            except sqlite3.Error:
                n = -1
            if n:
                out[table] = n
        return out
    finally:
        conn.close()


def pytest_sessionstart(session):
    print("RUN_RECEIPT_INITIAL " + json.dumps(_rows(), ensure_ascii=False), flush=True)


def pytest_runtest_logreport(report):
    if report.nodeid not in _OUTCOMES:
        _ORDER.append(report.nodeid)
    if report.when == "call":
        _OUTCOMES[report.nodeid] = ("failed" if report.failed else
                                    "skipped" if report.skipped else "passed")
    elif report.failed:  # setup / teardown blew up: the node never produced a real verdict
        _OUTCOMES[report.nodeid] = "error"


def pytest_collectreport(report):
    if report.failed:
        _OUTCOMES.setdefault("<collection:" + report.nodeid + ">", "error")


def pytest_sessionfinish(session, exitstatus):
    payload = _rows()
    payload["_exit_code"] = int(exitstatus)
    payload["_pid"] = os.getpid()
    print("RUN_RECEIPT_FINAL " + json.dumps(payload, ensure_ascii=False), flush=True)

    expected = {getattr(item, "nodeid", "?") for item in session.items}
    outcomes = {node: _OUTCOMES.get(node, "no_report") for node in sorted(expected)}
    missing = sorted(set(_OUTCOMES) - expected)
    print("RUN_RECEIPT_OUTCOMES " + json.dumps(
        {"outcomes": outcomes, "extra_reports": missing,
         "selected_count": len(expected)}, ensure_ascii=False), flush=True)
```

## `harness_instrument_streak.py`  (11471 B)

```python
"""GATE_ACCEPTANCE_STREAK over my two remaining single-run instruments (HARNESS, self-assigned).

Published once, cited since:
  * `EXP-HARNESS-004` - 64 phrasings x 8 families: `SLOW_PACE 0/8`, `SENSORY_LOW_STIMULATION 1/8`…
    measured at `66cad62`, from ONE run.
  * `harness_promotion_killtest.py` - "the guard has teeth": 0 violations as-is, 3 under a naive
    mapper. Also ONE run, and it is the thing ORD-0160 ③'s promise rests on.

Condition 8 says an isolated GREEN is observation, not closure, so both get the same treatment the
g3/gate streaks got: 10 consecutive independent processes over one export of one SHA, per-run
receipt, computed digest, and a destruction control proving the digest is not deaf.

Both run in-process: no HTTP, no ports, no provider (keys blanked before import), demo mode off.
The killtest keeps its own per-pid DB; the coverage instrument now takes a per-run tag.

Usage: python lab/tools/harness_instrument_streak.py --head 522c414 --runs 10
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
VOLATILE = {"generated_at", "db", "path", "out", "head", "phrasing", "ran_at", "command"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def canon(value):
    if isinstance(value, dict):
        return {k: canon(v) for k, v in sorted(value.items()) if k.lower() not in VOLATILE}
    if isinstance(value, list):
        return [canon(v) for v in value]
    return value


def digest(value) -> str:
    return hashlib.sha256(json.dumps(canon(value), ensure_ascii=False,
                                     sort_keys=True).encode("utf-8")).hexdigest()[:16]


SECTION_RE = re.compile(r"^\s*===\s*(.+?)\s*===\s*$")
CASE_RE = re.compile(r"^\s*(VIOLATION|FORBID-OK|WATCHING)\s+(\S.*?)\s+accepted=(\d+)/(\d+)\s*$")
VERDICT_RE = re.compile(r"violations as-is\s*=\s*(\d+)\s+violations under the sloppy mapper\s*=\s*(\d+)")


def run_phrase(export: Path, head: str, tag: str) -> dict:
    cmd = [str(PY), str(LAB / "tools" / "harness_phrase_coverage_004.py"),
           "--head", head, "--export", str(export), "--run-tag", tag]
    proc = subprocess.run(cmd, cwd=str(LAB.parent), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=_env(), timeout=600)
    art = LAB / "evidence" / f"phrase_coverage_{head}_{tag}.json"
    row = {"exit_code": proc.returncode, "artifact": art.name if art.exists() else "MISSING"}
    if art.exists():
        doc = json.loads(art.read_text(encoding="utf-8"))
        fam = {name: {"with_any_code": f["with_any_code"], "with_hard": f["with_hard"],
                      "with_constraint_rows": f["with_constraint_rows"],
                      "codes_seen": f["codes_seen"]}
               for name, f in doc["families"].items()}
        row.update({"corpus": doc["corpus_size"], "families": len(fam),
                    "per_family": fam, "code_frequency": doc["code_frequency"],
                    "measured_digest": digest(fam),
                    # kept on disk on purpose: a per-run receipt should be re-openable
                    "resolved_db_path": str(LAB / "evidence" / "_db" / f"phrase_coverage_{head}_{tag}.db")})
    else:
        row["stdout_tail"] = (proc.stdout + proc.stderr).strip().splitlines()[-2:]
    return row


def run_killtest(export: Path) -> dict:
    cmd = [str(PY), str(LAB / "tools" / "harness_promotion_killtest.py"), "--export", str(export)]
    proc = subprocess.run(cmd, cwd=str(LAB.parent), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=_env(), timeout=600)
    out = proc.stdout + proc.stderr
    cases = {}
    section = "?"
    for line in out.splitlines():
        head = SECTION_RE.match(line)
        if head:
            section = head.group(1).strip()
            continue
        m = CASE_RE.match(line)
        if m:
            # two arms reuse the same labels: keying them together conflates as-is with naive
            cases[f"{section}::{m.group(2).strip()}"] = {
                "arm": "as_is" if section.upper().startswith("AS-IS") or "AS-IS" in section.upper()
                else "naive",
                "verdict": m.group(1), "accepted": int(m.group(3)), "of": int(m.group(4))}
    v = VERDICT_RE.search(out)
    row = {"exit_code": proc.returncode, "cases": cases,
           "violations_as_is": int(v.group(1)) if v else "no_verdict_line",
           "violations_naive": int(v.group(2)) if v else "no_verdict_line"}
    as_is = {k: v for k, v in cases.items() if v["arm"] == "as_is"}
    naive = {k: v for k, v in cases.items() if v["arm"] == "naive"}
    row["arm_case_counts"] = {"as_is": len(as_is), "naive": len(naive)}
    row["as_is_all_quiet"] = all(v["verdict"] in ("FORBID-OK", "WATCHING") for v in as_is.values()) \
        if as_is else "no_as_is_cases"
    row["naive_violations"] = sum(1 for v in naive.values() if v["verdict"] == "VIOLATION")
    row["measured_digest"] = digest(cases) if cases else "no_cases_parsed"
    # the killtest names its own DB per pid (`harness_promotion_killtest.py:37`), so uniqueness is
    # by construction; recorded as a pattern here rather than pretending to know each pid.
    row["db_path_pattern"] = str(LAB / "evidence" / "_db" / "promotion_killtest_<pid>.db")
    return row


def _env() -> dict:
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "DEEPSEEK_API_KEY": "",
                "CITYNEXUS_AI_API_KEY": "", "CITYNEXUS_DEMO_MODE": "false"})
    env.pop("CITYNEXUS_DATABASE_URL", None)
    return env


def streak(name, fn, runs, args):
    rows = []
    for i in range(1, runs + 1):            # consecutive, one attempt each, no retry, no sleep
        row = fn(i)
        row["run_index"] = i
        rows.append(row)
        print(f"  [{name} run {i:2}] exit={row['exit_code']} "
              f"digest={str(row.get('measured_digest'))[:16]} "
              + (f"corpus={row.get('corpus')}" if "corpus" in row else
                 f"as_is={row.get('violations_as_is')} naive={row.get('violations_naive')}"))
    d = [r.get("measured_digest") for r in rows]
    green = sum(1 for r in rows if r["exit_code"] == 0)
    dig = {x for x in d if x}
    cls = (f"STABLE_GREEN({name})" if green == runs and len(dig) == 1 else
           f"FLIP_WITHOUT_SHARED_STATE({name})" if len(dig) > 1 else f"NOT_STABLE({name})")
    return {"run_shape": f"standalone in-process instrument over one export ({args.head}); "
                         "no HTTP, no ports, no provider, demo_mode=off",
            "instrument": name, "planned": runs, "green_count": green,
            "distinct_digests": sorted(dig), "identical_across_runs": len(dig) == 1,
            "classification": cls, "retry_used": False, "sleep_used": False,
            "runs": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", default="522c414")
    ap.add_argument("--runs", type=int, default=10)
    args = ap.parse_args()

    export = LAB / f"snap_{args.head}"
    if not (export / "backend" / "app").is_dir():
        print(f"no export at {export}")
        return 2

    phrase = streak("phrase-coverage-64x8",
                    lambda i: run_phrase(export, args.head, f"s{i}"), args.runs, args)
    kill = streak("promotion-killtest",
                  lambda i: run_killtest(export), args.runs, args)

    # destruction controls: a digest that cannot move proves nothing
    fam = copy.deepcopy(phrase["runs"][0]["per_family"])
    key = list(fam)[0]
    fam[key]["with_any_code"] += 1
    ctrl_p = digest(fam) != phrase["runs"][0]["measured_digest"]
    r0 = kill["runs"][0]
    quiet = [k for k, v in r0["cases"].items() if v["arm"] == "as_is" and v["verdict"] == "FORBID-OK"]
    c1 = copy.deepcopy(r0["cases"]); c1[quiet[0]] = {**c1[quiet[0]], "verdict": "VIOLATION"}
    ctrl_k1 = digest(c1) != r0["measured_digest"]          # a promoted as-is case must move it
    c2 = copy.deepcopy(r0["cases"]); c2[quiet[1]] = {**c2[quiet[1]], "accepted": 9}
    ctrl_k2 = digest(c2) != r0["measured_digest"]          # a count change must move it
    ctrl_k = ctrl_k1 and ctrl_k2
    print(f"\nkilltest arms parsed apart: {r0['arm_case_counts']} · as-is all quiet = "
          f"{r0['as_is_all_quiet']} · naive violations = {r0['naive_violations']}")
    print(f"control: promote an as-is case -> reacts={ctrl_k1}; change an accepted count -> reacts={ctrl_k2}")
    print(f"\ncontrol: phrase digest reacts to a per-family count change = {ctrl_p}")
    print(f"control: killtest digest reacts to flipping one case verdict = {ctrl_k}")

    # compare the refreshed reading with the one I published at 66cad62
    old_path = LAB / "evidence" / "phrase_coverage_66cad62.json"
    compare = "old artifact absent"
    if old_path.exists():
        old = json.loads(old_path.read_text(encoding="utf-8"))
        old_fam = {n: {"with_any_code": f["with_any_code"], "with_hard": f["with_hard"],
                       "with_constraint_rows": f["with_constraint_rows"],
                       "codes_seen": f["codes_seen"]} for n, f in old["families"].items()}
        new_fam = phrase["runs"][0]["per_family"]
        moved = {n: (old_fam.get(n), new_fam.get(n)) for n in set(old_fam) | set(new_fam)
                 if old_fam.get(n) != new_fam.get(n)}
        compare = {"same_table": not moved, "families_that_moved": sorted(moved),
                   "detail": {k: {"then": v[0], "now": v[1]} for k, v in sorted(moved.items())}}
        print(f"\n66cad62 -> {args.head}: identical? {compare['same_table']} "
              f"moved={compare['families_that_moved'] or 'none'}")

    receipt = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "head": args.head,
               "export": str(export), "interpreter": str(PY),
               "python_version": subprocess.run([str(PY), "--version"], capture_output=True,
                                                 text=True).stdout.strip(),
               "command_phrase": "python lab/tools/harness_phrase_coverage_004.py "
                                 f"--head {args.head} --export lab/snap_{args.head} --run-tag sN",
               "command_killtest": "python lab/tools/harness_promotion_killtest.py "
                                   f"--export lab/snap_{args.head}",
               "streaks": [phrase, kill],
               "destruction_controls": {"phrase_reacts": ctrl_p,
                                        "killtest_reacts_verdict_change": ctrl_k1,
                                        "killtest_reacts_count_change": ctrl_k2},
               "cross_tip_compare": compare,
               "condition_8": "10 identical runs prove repeatability of these instruments, not that "
                              "the measured product behaviour is right"}
    out = LAB / "evidence" / f"instrument_streak_{args.head}_{args.runs}r_{time.strftime('%H%M')}.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nphrase: {phrase['classification']} ({phrase['green_count']}/{args.runs})")
    print(f"killtest: {kill['classification']} ({kill['green_count']}/{args.runs})")
    print(f"receipt: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## `harness_g5_chain_0218.py`  (7605 B)

```python
"""ORD-0218 · g5 diagnosis: which layer is missing the behaviour - emitter, projection, or UI?

Diagnostic only.  Nothing here edits product code, relaxes the gate, skips anything, or changes an
assertion.  Three readings, in this order:

  R1 runtime truth  - call the exact endpoint g5 calls, on my own throwaway SQLite file, and print
                      what `run` actually carries (`outcome`, `status`, `failure_reason`).  The
                      test's own setup uses POST /api/v1/demo/reset; I do not - I seed in-process
                      through `app.services.seed_demo`, so the banned endpoint is never issued.
  R2 static inventory - who ever *writes* an `outcome` in `app/`, whether the run model has a field
                      for it, and whether §11's named vocabulary (CATALOG_EMPTY, NO_EXISTING_PLAN_TO_
                      REPLAN, PLAN_CREATED / NO_ACTION / BLOCKED) exists anywhere at all.
  R3 contract + consumer - does `contracts/openapi.yaml` promise the field, and does the frontend
                      read it.  This is what separates "backend never produced it" from "produced
                      but not projected" from "projected but unconsumed".
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
BACKEND = LAB / "snap_56d20ec" / "backend"
FRONTEND_SRC = Path(r"D:\moodle\_qoder_integration_20260919\frontend\src")   # read-only
CONTRACTS = BACKEND.parent / "contracts"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DB = LAB / "evidence" / "_db" / f"ord0218_g5_{os.getpid()}.db"
for suffix in ("", "-wal", "-shm"):
    Path(str(DB) + suffix).unlink(missing_ok=True)

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{DB}"
os.environ["CITYNEXUS_ENV"] = "test"
os.environ["CITYNEXUS_AI_ENABLED"] = "false"
os.environ["CITYNEXUS_GUARDIAN_AUTORUN"] = "false"
os.environ["CITYNEXUS_DEMO_MODE"] = "false"      # the reset door stays shut
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["CITYNEXUS_AI_API_KEY"] = ""
sys.path.insert(0, str(BACKEND))

report: dict = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                "sha_note": "export of 56d20ec; 50b35e0 differs in 0 backend files (git diff --name-only)"}

# ---------------------------------------------------------------- R1 runtime truth ----------
from fastapi.testclient import TestClient                       # noqa: E402
import app.main as product_main                                 # noqa: E402
from app.db.session import SessionLocal                         # noqa: E402

session = SessionLocal()
try:
    seeded = product_main.seed_demo(session)
finally:
    session.close()
report["seed_demo"] = {k: seeded.get(k) for k in list(seeded)[:6]}

client = TestClient(product_main.app)
from app.db.models import Journey                               # noqa: E402

session = SessionLocal()
try:
    journey = session.query(Journey).first()
    journey_id = str(journey.id) if journey else None
finally:
    session.close()
report["journey_id"] = journey_id

resp = client.post(f"/api/v1/journeys/{journey_id}/agent/commands",
                   json={"command": "帮我把这趟行程重新安排一下", "requested_autonomy": "PLAN_ONLY"})
body = resp.json() if isinstance(resp.json(), dict) else {}
run = body.get("run") if isinstance(body.get("run"), dict) else {}
mission = body.get("mission") if isinstance(body.get("mission"), dict) else {}
report["R1"] = {
    "endpoint": f"POST /api/v1/journeys/{{id}}/agent/commands",
    "status_code": resp.status_code,
    "top_level_keys": sorted(body)[:12],
    "run_keys": sorted(run)[:20],
    "run.outcome": run.get("outcome", "<key absent>"),
    "run.outcome_type": type(run.get("outcome")).__name__,
    "run.status": run.get("status"),
    "run.failure_reason": run.get("failure_reason"),
    "mission.status": mission.get("status"),
}
print("R1 runtime:", json.dumps(report["R1"], ensure_ascii=False, indent=1)[:900])


def count_in(root: Path, needle: str, exts=(".py", ".ts", ".tsx", ".yaml", ".json")) -> dict:
    hits: dict[str, int] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in exts or "node_modules" in str(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        n = text.count(needle)
        if n:
            hits[str(path.relative_to(root))] = n
    return hits


# ------------------------------------------------------- R2 static inventory ---------------
app_dir = BACKEND / "app"
report["R2"] = {
    "files_naming_outcome": {k: v for k, v in sorted(
        count_in(app_dir, "outcome").items(), key=lambda kv: -kv[1])[:14]},
    "assignments_to_outcome": {k: v for k, v in sorted(
        count_in(app_dir, "outcome =").items(), key=lambda kv: -kv[1])[:10]},
    "outcome_key_in_payloads": {k: v for k, v in sorted(
        count_in(app_dir, '"outcome"').items(), key=lambda kv: -kv[1])[:10]},
    "vocabulary": {term: count_in(app_dir, term) for term in (
        "CATALOG_EMPTY", "CATALOG_INSUFFICIENT", "NO_EXISTING_PLAN_TO_REPLAN",
        "PLAN_CREATED", "NO_ACTION", "BLOCKED")},
}
# does the run model even have a field for it?
models = (app_dir / "db" / "models.py").read_text(encoding="utf-8")
run_classes = [ln.strip() for ln in models.splitlines()
               if ln.startswith("class ") and ("Run" in ln or "Agent" in ln)]
report["R2"]["run_model_classes"] = run_classes
for cls in run_classes:
    name = cls.split()[1].rstrip("(,:")
    block = models[models.index(f"class {name}"):][:1600]
    lines = [ln.strip()[:80] for ln in block.splitlines() if "outcome" in ln]
    report["R2"].setdefault("outcome_column_on", {})[name] = {
        "outcome_named_in_class_body": bool(lines), "lines": lines[:4]}
print("\nR2 files naming `outcome`:", json.dumps(report["R2"]["files_naming_outcome"], ensure_ascii=False))
print("R2 vocabulary hits:", {k: (v or "0 hits") for k, v in report["R2"]["vocabulary"].items()})
print("R2 run-ish model classes:", run_classes)
print("R2 outcome column present?", report["R2"].get("outcome_column_on"))

# ------------------------------------------------- R3 contract + UI consumer ---------------
spec = (CONTRACTS / "openapi.yaml")
report["R3"] = {}
if spec.exists():
    text = spec.read_text(encoding="utf-8")
    report["R3"]["contracts_openapi_outcome_hits"] = text.count("outcome")
    report["R3"]["contracts_file"] = str(spec.relative_to(BACKEND.parent))
    report["R3"]["contracts_agent_command_paths"] = sorted(
        {ln.strip() for ln in text.splitlines() if "agent/commands" in ln})[:6]
if FRONTEND_SRC.is_dir():
    report["R3"]["frontend_outcome_files"] = count_in(FRONTEND_SRC, "outcome")
    report["R3"]["frontend_run_outcome_files"] = count_in(FRONTEND_SRC, "run.outcome")
    report["R3"]["frontend_status_words"] = {
        term: sum(count_in(FRONTEND_SRC, term).values())
        for term in ("NO_EXISTING_PLAN_TO_REPLAN", "CATALOG_INSUFFICIENT", "PLAN_CREATED", "outcome")}
print("\nR3:", json.dumps(report["R3"], ensure_ascii=False)[:1200])

out = LAB / "evidence" / f"ord0218_g5_chain_{time.strftime('%H%M')}.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")

for suffix in ("", "-wal", "-shm"):
    Path(str(DB) + suffix).unlink(missing_ok=True)
print(f"\nprobe DB deleted (own temp file): {DB.name} exists={DB.exists()}")
print("evidence:", out)
```

## `harness_phrase_coverage_004.py`  (8331 B)

```python
"""EXP-HARNESS-004: does the deterministic extractor understand the phrasings at all?

The standing gate (ORD-0153/0160) reports, per need family, one of three reasons a need
never reaches a feasibility gate:

    no_code_extracted        the parser returned no capability code for that sentence
    extracted_but_not_hard   it returned a code, but not at HARD severity
    FIXTURE_LIMITED          the schedule need cannot be satisfied by a 1-activity plan

The gate uses ONE phrasing per family, so "no_code_extracted" so far means "this
sentence produced nothing" - not "the product cannot express this need".  This
experiment widens each family to 8 phrasings (colloquial Chinese + English) and counts
how many of them reach a code, and how many reach a HARD one.

Deterministic path only: `app.capabilities.extract_capabilities_from_text` in-process.
No HTTP, no database, no seed, no AI provider, no provider network - keys are blanked
before import so nothing can reach a model.

Usage:  python lab/tools/harness_phrase_coverage_004.py [--head 66cad62]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FAMILIES: dict[str, list[str]] = {
    # control: the one family the gate already shows reaching a HARD constraint
    "step_free_wheelchair": [
        "我用轮椅，必须全程 step-free，一步楼梯都不能走",
        "老人坐轮椅，有台阶的地方都不能去",
        "全程不能有任何楼梯",
        "轮椅能直达才算，楼梯不行",
        "我们需要无障碍通道，台阶超过一级就不行",
        "no steps at all, wheelchair user",
        "一阶台阶都不行，坐轮椅的",
        "必须完全无台阶",
    ],
    "avoid_stairs_route": [
        "我不想走楼梯，能坐电梯就坐电梯",
        "尽量避免爬楼梯",
        "别安排楼梯路线",
        "上下楼走扶梯也行，就是别走楼梯",
        "少爬楼梯，膝盖不好",
        "avoid stairs on the route",
        "路线里不要有台阶",
        "不想爬楼",
    ],
    "sensory_low_stimulation": [
        "孩子自闭症，需要低刺激环境",
        "太吵太亮的地方受不了",
        "感官刺激强的地方要避开",
        "需要安静、人少、不闪灯的场所",
        "有感觉统合障碍，避免拥挤嘈杂",
        "low sensory stimulation environment needed",
        "别安排灯光闪烁、噪音大的项目",
        "感官敏感，需要能随时退场的地方",
    ],
    "slow_pace": [
        "走不快，行程节奏要慢",
        "安排得松一点，别赶",
        "每天少几个点，慢慢逛",
        "我们体力差，节奏放慢",
        "不要太紧凑的行程",
        "slower pace please",
        "慢慢走，别安排太多",
        "步子慢，行程别排满",
    ],
    "quiet_environment": [
        "想要安静一点的地方",
        "太吵的地方不去",
        "需要有低声环境（听障）",
        "安静优先",
        "quiet places only",
        "别安排闹市区",
        "希望行程安静些",
        "需要一个不受噪音干扰的环境",
    ],
    "stroller_infant": [
        "推婴儿车，台阶不行",
        "带娃推车出门",
        "需要婴儿车可通行",
        "stroller accessible",
        "有推车，要能进电梯",
        "带孩子，路要平",
        "婴儿车能推过去的地方",
        "需要亲子友好的无台阶通道",
    ],
    "large_luggage": [
        "大件行李寄存",
        "有两个 28 寸箱子",
        "行李多，需要放得下",
        "large luggage storage",
        "大件行李要能带上",
        "need to store big suitcases",
        "大箱子放哪里",
        "行李超大，要能寄存",
    ],
    "indoor_only": [
        "全程要在室内（雾霾天）",
        "只安排室内活动",
        "indoor only",
        "不想在露天待着",
        "需要有屋顶的地方",
        "天气差，走室内",
        "室内为主",
        "别安排户外活动",
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", default="522c414")
    ap.add_argument("--export", default="",
                    help="export root containing backend/; defaults to lab/snap_<head>")
    ap.add_argument("--run-tag", default="", help="per-run suffix so two runs never share files")
    args = ap.parse_args()

    export_root = Path(args.export) if args.export else LAB / f"snap_{args.head}"
    backend = export_root / "backend"
    if not backend.is_dir():
        print(f"no export at {backend}")
        return 2

    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["CITYNEXUS_ENV"] = "test"
    os.environ["CITYNEXUS_AI_ENABLED"] = "false"
    os.environ["CITYNEXUS_GUARDIAN_AUTORUN"] = "false"
    os.environ["DEEPSEEK_API_KEY"] = ""
    os.environ["CITYNEXUS_AI_API_KEY"] = ""
    os.environ["CITYNEXUS_DEMO_MODE"] = "false"
    # A database URL is set only so importing the module cannot reach a shared file;
    # nothing in this experiment opens it.
    suffix = f"_{args.run_tag}" if args.run_tag else ""
    os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + str(
        LAB / "evidence" / "_db" / f"phrase_coverage_{args.head}{suffix}.db")

    sys.path.insert(0, str(backend))
    from app.capabilities import (CAPABILITY_CODES, capability_constraints,
                                  extract_capabilities_from_text)

    print(f"head={args.head}  export={export_root.name}  "
          f"vocabulary size={len(CAPABILITY_CODES)}  "
          f"AI=off  http=none  db_opened=no")

    per_family: dict[str, dict] = {}
    code_counter: Counter[str] = Counter()
    for fam, phrases in FAMILIES.items():
        rows = []
        for text in phrases:
            caps = extract_capabilities_from_text(text)
            codes = sorted({c["code"] for c in caps})
            hard = sorted({c["code"] for c in caps if c.get("severity") == "HARD"})
            rows.append({
                "phrasing": text,
                "codes": codes,
                "severities": sorted({str(c.get("severity")) for c in caps}),
                "hard_codes": hard,
                "constraint_rows": len(capability_constraints(caps)),
            })
            code_counter.update(codes)
        n = len(rows)
        per_family[fam] = {
            "phrasings": n,
            "with_any_code": sum(1 for r in rows if r["codes"]),
            "with_hard": sum(1 for r in rows if r["hard_codes"]),
            "with_constraint_rows": sum(1 for r in rows if r["constraint_rows"]),
            "codes_seen": sorted({c for r in rows for c in r["codes"]}),
            "silent_phrasings": [r["phrasing"] for r in rows if not r["codes"]],
            "rows": rows,
        }

    print(f"\n{'family':<26} {'any code':>9} {'HARD':>6} {'rows>0':>7}   codes seen")
    for fam, d in per_family.items():
        print(f"{fam:<26} {d['with_any_code']:>4}/{d['phrasings']:<4} "
              f"{d['with_hard']:>3}/{d['phrasings']:<3} {d['with_constraint_rows']:>4}/{d['phrasings']:<3}  "
              f"{','.join(d['codes_seen']) or '-'}")

    print("\n=== every code the whole corpus produced (with frequency) ===")
    for code, count in code_counter.most_common():
        print(f"  {code:<28} {count}")

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "head": args.head,
        "runtime": "in-process app.capabilities.extract_capabilities_from_text; "
                   "no HTTP, no DB opened, AI disabled, provider not reachable",
        "vocabulary_size": len(CAPABILITY_CODES),
        "corpus_size": sum(len(v) for v in FAMILIES.values()),
        "families": per_family,
        "code_frequency": dict(code_counter),
    }
    dest = LAB / "evidence" / f"phrase_coverage_{args.head}{suffix}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    print(f"\ncorpus={out['corpus_size']} phrasings   evidence: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## `harness_positive_control_004b.py`  (2787 B)

```python
"""Positive control for EXP-HARNESS-004: when the literal table DOES fire, is the need enforceable?

`harness_phrase_coverage_004.py` measured what 64 ordinary sentences produce.  A "0/8"
reading is only half a claim: the parser may key on a literal nobody says.  So this
probe feeds the exact tokens the source table lists (`app/capabilities.py:821-828`) and
reads back severity + constraint rows.  If the magic words still yield a non-HARD
"preferred" capability with zero constraint rows, the gap is not wording at all.

In-process only: no HTTP, no DB, AI disabled, provider unreachable.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "evidence", "_db", "tmp_positive_control.db"))
os.environ["CITYNEXUS_ENV"] = "test"
os.environ["CITYNEXUS_AI_ENABLED"] = "false"
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["CITYNEXUS_AI_API_KEY"] = ""
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "snap_66cad62", "backend")))

from app.capabilities import capability_constraints, extract_capabilities_from_text

CASES = [
    ("SLOW_PACE literal '慢一点'", "行程请慢一点"),
    ("SLOW_PACE literal '慢速' + hard words", "我们走不快，必须慢速，这是硬性要求不能赶路"),
    ("SLOW_PACE English literal", "please take it slowly, this is a hard requirement"),
    ("SENSORY literal '低刺激'", "必须低刺激环境，这是硬性要求，孩子自闭症"),
    ("QUIET literal '安静' + hard", "必须安静，硬性要求"),
    ("LUGGAGE literal '行李' + hard", "行李必须能寄存，硬性要求"),
    ("wheelchair + explicit hard phrasing", "轮椅必须全程无台阶，一步都不能有，这是硬性要求"),
    ("wheelchair, no hard word", "轮椅能直达才算"),
]

def kind_of(row) -> str:
    """Constraint rows carry hardness under `kind` (not `severity`) - see the readings."""
    if isinstance(row, dict):
        return str(row.get("kind", "")).upper()
    return str(getattr(row, "kind", "")).upper()


for label, text in CASES:
    caps = extract_capabilities_from_text(text)
    rows = capability_constraints(caps)
    triples = [(c["code"], c.get("severity"), c.get("class")) for c in caps]
    hard_rows = [r for r in rows if kind_of(r) == "HARD"]
    print(f"{label:<38} 「{text}」")
    print(f"    caps={triples}")
    print(f"    rows={len(rows)} hard_rows={len(hard_rows)}")
    for r in rows:
        params = r.get("params", {}) if isinstance(r, dict) else {}
        print(f"      kind={kind_of(r)} rule={r.get('rule_code')} "
              f"class={r.get('category')} needs_confirmation={params.get('needs_confirmation')}")
```

## `harness_gate_streak_selftest.py`  (7571 B)

```python
"""GATE_ACCEPTANCE_STREAK self-test of my own standing gate (HARNESS, ORD-0153/0160 instrument).

Why this is owed: on 2026-09-21 I published "same-tree `--check` RC=0 IDENTICAL" from **one** run,
and the frozen amendment says condition 8 - one isolated GREEN is observation, never closure.  So
the same bar I applied to `g3` gets applied to my own instrument, on one exact SHA:

  run shape (condition 9)  = standalone gate process over one `git archive` export of one SHA;
                             in-process seed, no HTTP, no ports, no provider, demo mode off
  processes (condition 2)  = 10 consecutive, independent, one attempt each
  fresh DB (condition 3/7) = each run gets its own SQLite file via `--run-tag rN`; the 10 resolved
                             absolute paths must be distinct - proven from the runs, not assumed
  receipt (condition 4)    = run_index, exit_code, resolved db path, cells total, blocked total,
                             changed-items count vs the named baseline, and a canonical digest of
                             the measured table with path/volatile fields removed
  no relaxation (condition 6)= no sleep, no retry, no cell-count trimming, no assertion edits

The digest is computed, not asserted: two runs that differ in any measured cell differ in digest.
Usage: python lab/tools/harness_gate_streak_selftest.py --head 522c414 --baseline <json> --runs 10
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
GATE = LAB / "tools" / "harness_evidence_gate.py"
VOLATILE_KEYS = {"db", "database", "generated_at", "out", "path", "head"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def canon(value):
    """Recurse, dropping path/time fields, so the digest covers only measured content."""
    if isinstance(value, dict):
        return {k: canon(v) for k, v in sorted(value.items()) if k.lower() not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [canon(v) for v in value]
    return value


def totals(doc: dict) -> dict:
    cells = doc.get("cells") or []
    summary = doc.get("summary") or {}
    # the gate writes `passed`, not `blocked`: counting the wrong key reads a silent 0
    blocked = sum(1 for c in cells if c.get("passed") is False)
    return {"cells": len(cells), "blocked": blocked,
            "summary_cells_blocked": summary.get("cells_blocked"),
            "summary_cells_total": summary.get("cells_total"),
            "blocked_column_matches_summary": blocked == summary.get("cells_blocked"),
            "promotion_violations": summary.get("promotion_violations"),
            "per_family_rollup": {k: v for k, v in sorted(summary.items())
                                  if isinstance(v, (int, str))}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", default="522c414")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--baseline", default=str(LAB / "evidence" / "evidence_gate_e0fc697.json"))
    args = ap.parse_args()

    tree = LAB / f"snap_{args.head}"
    if not (tree / "backend" / "app").is_dir():
        print(f"no export at {tree}")
        return 2

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["DEEPSEEK_API_KEY"] = ""
    env["CITYNEXUS_AI_API_KEY"] = ""

    runs = []
    for i in range(1, args.runs + 1):          # consecutive, one attempt each, no retry, no sleep
        tag = f"r{i}"
        cmd = [str(PY), str(GATE), "--export", str(tree), "--head", args.head,
               "--run-tag", tag, "--baseline", args.baseline, "--check"]
        proc = subprocess.run(cmd, cwd=str(LAB.parent), env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=600)
        out = proc.stdout + proc.stderr
        doc_path = LAB / "evidence" / f"evidence_gate_{args.head}_{tag}.json"
        row = {"run_index": i, "run_tag": tag, "exit_code": proc.returncode,
               "command": " ".join(cmd[-6:]),
               "ran_at": time.strftime("%H:%M:%S")}
        if doc_path.exists():
            doc = json.loads(doc_path.read_text(encoding="utf-8"))
            digest = hashlib.sha256(json.dumps(canon(doc), ensure_ascii=False,
                                               sort_keys=True).encode("utf-8")).hexdigest()[:16]
            row.update(totals(doc))
            row["content_digest"] = digest
            row["resolved_db_path"] = str(LAB / "evidence" / "_db" / f"evidence_gate_{args.head}_{tag}.db")
            row["db_bytes_on_disk"] = (Path(row["resolved_db_path"]).stat().st_size
                                       if Path(row["resolved_db_path"]).exists() else None)
            row["check_verdict_line"] = next((ln.strip()[:90] for ln in out.splitlines()
                                              if "changed item" in ln or "IDENTICAL" in ln), "")
        else:
            row["missing_output"] = str(doc_path)
        runs.append(row)
        print(f"  run {i:2}: exit={row['exit_code']} cells={row.get('cells')} "
              f"blocked={row.get('blocked')} digest={row.get('content_digest')} "
              f"db=...{tag}.db {row.get('check_verdict_line', '')}")

    paths = [r.get("resolved_db_path") for r in runs]
    digests = {r.get("content_digest") for r in runs}
    green = sum(1 for r in runs if r["exit_code"] == 0)
    streak = {
        "run_shape": "standalone gate process over one git-archive export of one SHA "
                     "(in-process seed, no HTTP, no ports, no provider, demo_mode=off)",
        "sha": args.head, "planned": args.runs, "executed": len(runs),
        "green_count": green, "all_green": green == args.runs,
        "distinct_db_paths": len({p for p in paths if p}),
        "shared_db_path": len(paths) != len({p for p in paths if p}),
        "identical_content_across_runs": len(digests) == 1,
        "digests_seen": sorted(d for d in digests if d),
        "baseline": Path(args.baseline).name,
        "retry_used": False, "sleep_used": False, "cells_trimmed": False, "assertions_relaxed": False,
        "classification": (
            f"STABLE_GREEN({args.head})" if green == args.runs and len(digests) == 1
            else f"FLIP_WITHOUT_SHARED_STATE(runs {len(digests)} distinct digests)" if len(digests) > 1
            else "NOT_STABLE"),
    }
    receipt = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "streak": streak, "runs": runs,
               "condition_8_note": "one isolated GREEN is observation, not closure; the count above "
                                   "is the 10-run observation, closure still needs the promotion-guard "
                                   "cases and a changed-tree diff"}
    out_path = LAB / "evidence" / f"gate_selfstreak_{args.head}_{args.runs}r_{time.strftime('%H%M')}.json"
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8")

    print(f"\nstreak: green {green}/{args.runs} · distinct DB paths {streak['distinct_db_paths']} "
          f"· shared path? {streak['shared_db_path']} · identical content across runs? "
          f"{streak['identical_content_across_runs']} ({len(streak['digests_seen'])} digest)")
    print(f"classification: {streak['classification']}")
    print(f"receipt: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## `harness_evidence_gate.py`  (21902 B)

```python
"""Standing evidence-shape gate (ORD-0153 ①②) — lab-only, observation only.

Re-runnable against ANY exported tree:

    <venv python> lab/tools/harness_evidence_gate.py --export lab/snap_e9efec6 \
        --head e9efec6 [--baseline lab/evidence/evidence_gate_baseline.json] [--check]

What it does
  * seeds a throwaway lab DB by calling the product's own `seed_demo()` in-process
    (never `POST /api/v1/demo/reset`, which ORD-0125/R13 ruled an unscoped
    52-table drop and banned for every lane);
  * drives the product's real gate `evaluate_feasibility` over
    every seeded place x every hard-need family x every evidence shape;
  * records the capability codes and severities the tree *actually* produced, so
    a change in vocabulary shows up as a diff rather than a silent re-interpretation;
  * with `--check`, compares against a stored baseline and exits non-zero on any
    change in cell counts, blocked counts, or reason-code distribution.

What it deliberately does NOT do: it does not change how evidence is *read*.
Until the arbiter rules, widening `accessibility_state()` to accept bare OSM tags
would weaken EAC's still-correct `UNKNOWN != ACCESSIBLE`. This tool only measures.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]

START = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)

# --- need families -----------------------------------------------------------
# `hard` phrasings are written to assert a HARD requirement; whatever severity
# the tree actually returns is recorded, not assumed.
# `curated_*` are the keys the product reads today; `osm_native` is the closest
# real provider spelling for that need (None => no provider key is defined,
# which is itself a reported fact).
FAMILIES: dict[str, dict] = {
    "step_free_wheelchair": {
        "phrasing": "我用轮椅，必须全程 step-free，一步楼梯都不能走",
        "curated_true": {"step_free": True}, "curated_false": {"step_free": False},
        "osm_native": {"wheelchair": "yes"},
    },
    "avoid_stairs_route": {
        "phrasing": "我必须走无阶梯路线，任何台阶都不行",
        "curated_true": {"step_free": True}, "curated_false": {"stairs": True},
        "osm_native": {"wheelchair": "yes", "highway": "permitted"},
    },
    "stroller_infant": {
        "phrasing": "我推婴儿车，必须全程婴幼儿车可通行",
        "curated_true": {"stroller_accessible": True},
        "curated_false": {"stroller_accessible": False},
        "osm_native": {"stroller": "yes", "baby_wheelchair": "yes"},
    },
    "large_luggage": {
        "phrasing": "我带大件行李，必须全程可带大件行李",
        "curated_true": {"luggage_accessible": True},
        "curated_false": {"luggage_accessible": False},
        "osm_native": None,
    },
    "quiet_environment": {
        "phrasing": "我必须有安静环境，不能嘈杂",
        "curated_true": {"quiet": True}, "curated_false": {"quiet": False},
        "osm_native": None,
    },
    "sensory_low_stimulation": {
        "phrasing": "我必须避免强感官刺激环境，这是硬性要求",
        "curated_true": {"low_stimulation": True},
        "curated_false": {"low_stimulation": False},
        "osm_native": None,
    },
    "indoor_only": {
        "phrasing": "必须是室内地点，不能在户外",
        "curated_true": {"indoor": True}, "curated_false": {"indoor": False},
        "osm_native": {"indoor": "yes"},
    },
    "max_walking_per_leg": {
        "phrasing": "每段步行不能超过 300 米，这是硬性要求",
        "curated_true": {}, "curated_false": {}, "osm_native": None,
    },
    "rest_cadence": {
        "phrasing": "我必须每 30 分钟能坐下休息一次，硬性要求",
        "curated_true": {}, "curated_false": {}, "osm_native": None,
    },
    "toilet_cadence": {
        "phrasing": "我必须每 90 分钟用到一次卫生间，硬性要求",
        "curated_true": {}, "curated_false": {}, "osm_native": None,
    },
    "infant_nap_window": {
        "phrasing": "宝宝下午 1 点到 3 点必须睡午觉，不能安排活动，这是硬性要求",
        "curated_true": {}, "curated_false": {}, "osm_native": None,
    },
    "midday_rest_window": {
        "phrasing": "老人中午 12 点到 14 点必须回酒店休息，硬性要求",
        "curated_true": {}, "curated_false": {}, "osm_native": None,
    },
    "slow_pace": {
        "phrasing": "必须慢节奏，硬性要求不能赶",
        "curated_true": {}, "curated_false": {}, "osm_native": None,
    },
}

ABSENT_EVIDENCE_CODES = {"ACCESSIBILITY_UNVERIFIED", "NEEDS_LIVE_EVIDENCE",
                         "PLACE_AVAILABILITY_UNKNOWN"}
CONFLICT_CODES = {"ACCESSIBILITY_CONFLICT", "STROLLER_ACCESS_UNAVAILABLE",
                  "LUGGAGE_ACCESS_UNAVAILABLE", "PLACE_CLOSED", "PLACE_UNAVAILABLE"}


def close_time(hours: dict, default: time) -> time:
    raw = hours.get("close") or hours.get("last_service")
    return _hhmm(raw, default)


def _hhmm(raw, default: time) -> time:
    if isinstance(raw, str) and ":" in raw:
        try:
            hh, mm = raw.split(":")[0:2]
            return time(int(hh) % 24, int(mm) % 60)
        except ValueError:
            return default
    return default


def build_shapes(family: dict) -> dict[str, dict | None]:
    """Six evidence shapes per family; `None` = use the place's own seed metadata."""
    shapes: dict[str, dict | None] = {
        "seed_native": None,
        "curated_true": dict(family["curated_true"]),
        "no_evidence": {},
        "unrelated_osm": {"tags": {"amenity": "cafe"}},
    }
    if family["curated_true"]:
        shapes["curated_false"] = dict(family["curated_false"])
    if family["osm_native"]:
        shapes["osm_native"] = {"tags": dict(family["osm_native"])}
    else:
        shapes["osm_native"] = {"_no_provider_key_defined": True}
    return shapes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True, help="lab export root containing backend/")
    ap.add_argument("--head", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--run-tag", default="",
                    help="per-run suffix: two runs of one SHA never share a DB or an output file")
    args = ap.parse_args()

    root = Path(args.export).resolve()
    backend = root / "backend"
    if not (backend / "app" / "main.py").is_file():
        print(f"no backend at {backend}")
        return 2

    suffix = f"_{args.run_tag}" if args.run_tag else ""
    db = LAB / "evidence" / "_db" / f"evidence_gate_{args.head}{suffix}.db"
    if db.exists():
        db.unlink()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["CITYNEXUS_ENV"] = "test"
    os.environ["CITYNEXUS_AI_ENABLED"] = "false"
    os.environ["CITYNEXUS_GUARDIAN_AUTORUN"] = "false"
    os.environ["DEEPSEEK_API_KEY"] = ""
    os.environ["CITYNEXUS_AI_API_KEY"] = ""
    os.environ["CITYNEXUS_DEMO_MODE"] = "false"  # the banned endpoint stays closed
    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db}"

    sys.path.insert(0, str(backend))
    from app.capabilities import (accessibility_state, capability_constraints,
                                  extract_capabilities_from_text)
    from app.db.session import SessionLocal, ensure_schema
    from app.integrations.mock.providers import MockMobilityProvider
    from app.main import seed_demo
    from app.replanning.feasibility import (FeasibilityActivity, FeasibilityContext,
                                            evaluate_feasibility)

    # seed in-process; no HTTP, no /demo/reset
    ensure_schema()
    session = SessionLocal()
    try:
        seed_demo(session)
    finally:
        session.close()

    session = SessionLocal()
    try:
        from app.db.models import Place

        def as_dict(raw) -> dict:
            if isinstance(raw, dict):
                return dict(raw)
            if isinstance(raw, str) and raw.strip():
                try:
                    value = json.loads(raw)
                except ValueError:
                    return {}
                return dict(value) if isinstance(value, dict) else {}
            return {}

        places = [(p.id, p.name, p.city_code, as_dict(p.metadata_json),
                   "available", as_dict(p.opening_hours_json))
                  for p in session.query(Place).order_by(Place.id)]
    finally:
        session.close()
    print(f"head={args.head}  seeded places={len(places)}  DB={db.name}  demo_mode=off")

    vocab: dict[str, dict] = {}
    for fam, spec in FAMILIES.items():
        caps = extract_capabilities_from_text(spec["phrasing"])
        codes = sorted({c["code"] for c in caps})
        sevs = sorted({str(c.get("severity")) for c in caps})
        rows = len(capability_constraints(caps))
        vocab[fam] = {
            "codes": codes, "severities": sevs,
            "has_hard": any(c.get("severity") == "HARD" for c in caps),
            "constraint_rows": rows,
            # Three different reasons a need can fail to reach the gate.
            "why_no_rows": ("" if rows else
                            ("no_code_extracted" if not codes
                             else "extracted_but_not_hard")),
        }
        print(f"  {fam:<24} codes={codes} severities={sevs} HARD={vocab[fam]['has_hard']} "
              f"rows={rows}{(' <- ' + vocab[fam]['why_no_rows']) if vocab[fam]['why_no_rows'] else ''}")

    # Needs whose gate is about the *schedule*, not the place.  A one-activity
    # fixture can never satisfy a break cadence or a rest window, so any block
    # here is my instrument's limit, not a product finding.
    FIXTURE_LIMITED = {"rest_cadence", "toilet_cadence", "infant_nap_window",
                       "midday_rest_window", "max_walking_per_leg", "slow_pace"}

    cells = []
    for fam, spec in FAMILIES.items():
        caps = extract_capabilities_from_text(spec["phrasing"])
        constraints = capability_constraints(caps)
        for shape_name, override in build_shapes(spec).items():
            for pid, pname, city, meta, status, hours in places:
                used = dict(meta) if shape_name == "seed_native" else dict(override)
                # Hours are deliberately neutralised here so this table measures
                # evidence shape only; the closure axis is the control below.
                ctx = FeasibilityContext(
                    journey_id="gate-journey", city_code=city or "CNX-DEMO",
                    journey_start=START, journey_end=START + timedelta(hours=10),
                    budget_amount_minor=200_000, budget_currency="CNY",
                    constraints=tuple(constraints),
                    places={pid: {"id": pid, "city_code": city, "status": status,
                                  "opening_hours_json": {"open": "00:00", "close": "23:59"},
                                  "metadata_json": used}},
                    services={}, mobility_provider=MockMobilityProvider(),
                    plan_currency="CNY",
                )
                acts = [FeasibilityActivity(key="a1", start_at=START + timedelta(hours=1),
                                            end_at=START + timedelta(hours=2),
                                            cost_minor=5_000, place_id=pid)]
                res = evaluate_feasibility(ctx, acts)
                codes = sorted({str(f).split(":")[0] for f in res.failures})
                cells.append({"family": fam, "shape": shape_name, "place_id": pid,
                              "passed": bool(res.passed), "codes": codes,
                              "hours_neutralised": True})

    per: dict[str, dict] = {}
    for fam in FAMILIES:
        for shape_name in build_shapes(FAMILIES[fam]):
            sel = [c for c in cells if c["family"] == fam and c["shape"] == shape_name]
            blocked = [c for c in sel if not c["passed"]]
            tally: Counter[str] = Counter()
            for c in blocked:
                for k in c["codes"]:
                    tally[k] += 1
            absent_only = [c for c in blocked if c["codes"]
                           and not (set(c["codes"]) & CONFLICT_CODES)]
            per[f"{fam}/{shape_name}"] = {
                "cells": len(sel), "blocked": len(blocked),
                "blocked_absent_evidence_only": len(absent_only),
                "codes": dict(tally),
                # A family whose phrasing produced no constraint row never reached
                # the gate; "0 blocked" for it means "not exercised", not "passed".
                "exercised": vocab[fam]["constraint_rows"] > 0,
            }

    family_rollup: dict[str, dict] = {}
    for fam in FAMILIES:
        shape_blocked = {k.split("/")[1]: v["blocked"]
                         for k, v in per.items() if k.split("/")[0] == fam}
        distinct = sorted(set(shape_blocked.values()))
        family_rollup[fam] = {
            "exercised": vocab[fam]["constraint_rows"] > 0,
            "why_not_exercised": vocab[fam]["why_no_rows"],
            "fixture_limited": fam in FIXTURE_LIMITED,
            "reached_gate": any(v > 0 for v in shape_blocked.values()),
            "evidence_dependent": len(distinct) > 1,
            "blocked_by_shape": shape_blocked,
        }

    # Control axis: the SAME hard step-free need, but the activity is scheduled
    # outside the place's opening hours.  Accessibility evidence is supplied so
    # that gate PASSES first - otherwise the accessibility failure short-circuits
    # the row and the closure code can never be observed.
    control: dict = {"family": "out_of_hours_control", "note": "", "codes": {}}
    fam = "step_free_wheelchair"
    caps = extract_capabilities_from_text(FAMILIES[fam]["phrasing"])
    constraints = capability_constraints(caps)
    control_codes: Counter[str] = Counter()
    blocked_control = 0
    for pid, pname, city, meta, status, hours in places:
        real_hours = hours or {"open": "08:00", "close": "18:00"}
        close = close_time(real_hours, time(18, 0))
        late_start = START.replace(hour=close.hour, minute=close.minute) + timedelta(hours=2)
        ctx = FeasibilityContext(
            journey_id="gate-journey", city_code=city or "CNX-DEMO",
            journey_start=START, journey_end=START + timedelta(hours=23),
            budget_amount_minor=200_000, budget_currency="CNY",
            constraints=tuple(constraints),
            places={pid: {"id": pid, "city_code": city, "status": status,
                          "opening_hours_json": real_hours,
                          "metadata_json": {"step_free": True}}},
            services={}, mobility_provider=MockMobilityProvider(), plan_currency="CNY",
        )
        acts = [FeasibilityActivity(key="a1", start_at=late_start,
                                    end_at=late_start + timedelta(hours=1),
                                    cost_minor=5_000, place_id=pid)]
        res = evaluate_feasibility(ctx, acts)
        if not res.passed:
            blocked_control += 1
        for f in res.failures:
            control_codes[str(f).split(":")[0]] += 1
    control["blocked"] = blocked_control
    control["cells"] = len(places)
    control["codes"] = dict(control_codes)
    per["out_of_hours_control/all_shapes"] = {
        "cells": len(places), "blocked": blocked_control,
        "blocked_absent_evidence_only": 0, "codes": dict(control_codes),
        "exercised": True,
    }
    print(f"\ncontrol (step-free need, activity outside 08:00-10:00 window): "
          f"blocked {blocked_control}/{len(places)} codes={dict(control_codes)}")

    # ------------------------------------------------------------------
    # Promotion guard (ORD-0160 ③): the mapping layer C is about to land must
    # never turn a *partial* or *subject-scoped* provider fact into a
    # place-level "verified, step-free" verdict.  These cases pin exactly that:
    # `accepted` here means the gate let a HARD step-free traveller plan through.
    # Any case flipping `accepted` on a later HEAD is the regression to catch.
    # ------------------------------------------------------------------
    PROMOTION_CASES = [
        ("wheelchair=limited", {"tags": {"wheelchair": "limited"}}, False),
        ("wheelchair=limited + ramp + elevator",
         {"tags": {"wheelchair": "limited", "ramp": "yes", "elevator": "yes"}}, False),
        ("toilets:wheelchair=yes only", {"tags": {"toilets:wheelchair": "yes"}}, False),
        ("entrance:wheelchair=yes only", {"tags": {"entrance:wheelchair": "yes"}}, False),
        ("wheelchair=no", {"tags": {"wheelchair": "no"}}, False),
        ("wheelchair=yes (bare provider fact)", {"tags": {"wheelchair": "yes"}}, None),
        ("wheelchair=yes + highway=steps",
         {"tags": {"wheelchair": "yes", "highway": "steps"}}, False),
    ]
    promotion = {}
    for label, meta, must_not_accept in PROMOTION_CASES:
        accepted = 0
        tally_p: Counter[str] = Counter()
        for pid, pname, city, meta_real, status, hours in places:
            ctx = FeasibilityContext(
                journey_id="gate-journey", city_code=city or "CNX-DEMO",
                journey_start=START, journey_end=START + timedelta(hours=10),
                budget_amount_minor=200_000, budget_currency="CNY",
                constraints=tuple(constraints),
                places={pid: {"id": pid, "city_code": city, "status": status,
                              "opening_hours_json": {"open": "00:00", "close": "23:59"},
                              "metadata_json": dict(meta)}},
                services={}, mobility_provider=MockMobilityProvider(), plan_currency="CNY",
            )
            acts = [FeasibilityActivity(key="a1", start_at=START + timedelta(hours=1),
                                        end_at=START + timedelta(hours=2),
                                        cost_minor=5_000, place_id=pid)]
            res = evaluate_feasibility(ctx, acts)
            accepted += 1 if res.passed else 0
            for f in res.failures:
                tally_p[str(f).split(":")[0]] += 1
        states = {str(accessibility_state(dict(meta).get("tags", {})))}
        violation = bool(must_not_accept is False and accepted > 0)
        promotion[label] = {
            "accepted_places": accepted, "places": len(places),
            "must_not_accept": must_not_accept, "violation": violation,
            "codes": dict(tally_p),
            "accessibility_state_of_raw_tags": sorted(states),
        }
        print(f"  {'VIOLATION' if violation else ('FORBID-OK ' if must_not_accept is False else 'WATCHING ')}"
              f"{label:<38} accepted={accepted}/{len(places)} codes={dict(tally_p)}")

    summary = {
        "head": args.head, "places": len(places), "families": len(FAMILIES),
        "cells_total": len(cells), "cells_blocked": sum(1 for c in cells if not c["passed"]),
        "vocabulary": vocab, "per_family_shape": per,
        "family_rollup": family_rollup, "control_out_of_hours": control,
        "promotion_guard": promotion,
        "promotion_violations": sorted(k for k, v in promotion.items() if v["violation"]),
    }
    out = LAB / "evidence" / f"evidence_gate_{args.head}{suffix}.json"
    out.write_text(json.dumps({"summary": summary, "cells": cells}, ensure_ascii=False,
                              indent=1), encoding="utf-8")

    print("\n=== per family (detail per shape lives in the JSON) ===")
    for fam, r in family_rollup.items():
        if not r["exercised"]:
            status = f"NOT_EXERCISED:{r['why_not_exercised']}"
        elif r["fixture_limited"]:
            status = "FIXTURE_LIMITED (schedule need, 1-activity plan cannot satisfy it)"
        elif r["evidence_dependent"]:
            status = "evidence-DEPENDENT"
        else:
            status = "evidence-invariant"
        print(f"  {fam:<26} {status:<62} by_shape={r['blocked_by_shape']}")
    print(f"\ntotal {summary['cells_blocked']}/{summary['cells_total']} blocked   wrote {out}")

    if args.check and args.baseline:
        base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))["summary"]
        sections = ("per_family_shape", "family_rollup", "promotion_guard")
        diffs = []
        for sec in sections:
            b_all = base.get(sec, {}) or {}
            n_all = summary.get(sec, {}) or {}
            for key in sorted(set(b_all) | set(n_all)):
                b, n = b_all.get(key), n_all.get(key)
                if sec == "family_rollup" and isinstance(b, dict) and isinstance(n, dict):
                    # `head`-independent bookkeeping fields must not mask a real move
                    b = {k: v for k, v in b.items() if k != "head"}
                    n = {k: v for k, v in n.items() if k != "head"}
                if b != n:
                    diffs.append((f"{sec}:{key}", b, n))
        for key in ("cells_total", "cells_blocked"):
            if base.get(key) != summary.get(key):
                diffs.append((key, base.get(key), summary.get(key)))
        print(f"\n=== baseline check vs {Path(args.baseline).name} "
              f"(head {base['head']}) ===")
        if not diffs:
            print("IDENTICAL — gate green")
        for key, b, n in diffs:
            print(f"  DIFF {key}: baseline={b} now={n}")
        if summary["promotion_violations"]:
            print("  PROMOTION VIOLATIONS: " + ", ".join(summary["promotion_violations"]))
        print(f"{len(diffs)} changed item(s) -> RC={'3' if diffs else '0'}")
        return 3 if diffs else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## `digest_teeth_check.py`  (3924 B)

```python
"""Teeth-test the self-streak digest, and fix its `blocked` reading.

Two mistakes this closes:
  * `totals()` counted `cell["blocked"]`, which the gate never writes (cells carry `passed`),
    so every run would have reported blocked=0 next to a summary saying 320 - a vacuous column.
  * the content digest returned the *same* value for four different exports.  That is consistent
    with the gate's own IDENTICAL readings, but a hash that cannot tell two tables apart proves
    nothing, so it gets a positive and a negative control before it is trusted.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys

LAB = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from harness_gate_streak_selftest import canon, totals  # noqa: E402

# --- fix the vacuous column in the instrument itself -----------------------------------------
P = LAB / "tools" / "harness_gate_streak_selftest.py"
s = P.read_text(encoding="utf-8")
old = '''    cells = doc.get("cells") or []
    summary = doc.get("summary") or {}
    blocked = sum(1 for c in cells if c.get("blocked"))'''
new = '''    cells = doc.get("cells") or []
    summary = doc.get("summary") or {}
    # the gate writes `passed`, not `blocked`: counting the wrong key reads a silent 0
    blocked = sum(1 for c in cells if c.get("passed") is False)'''
assert s.count(old) == 1, "blocked anchor"
s = s.replace(old, new, 1)
old2 = '''            "summary_keys": len(summary),'''
new2 = '''            "summary_cells_blocked": summary.get("cells_blocked"),
            "summary_cells_total": summary.get("cells_total"),
            "blocked_column_matches_summary": blocked == summary.get("cells_blocked"),
            "promotion_violations": summary.get("promotion_violations"),'''
assert s.count(old2) == 1, "summary anchor"
s = s.replace(old2, new2, 1)
P.write_text(s, encoding="utf-8", newline="\n")
import ast
ast.parse(s)
print("instrument fixed: blocked now counts cell['passed'] is False")

# --- digest teeth controls --------------------------------------------------------------------
def digest(doc) -> str:
    return hashlib.sha256(json.dumps(canon(doc), ensure_ascii=False,
                                     sort_keys=True).encode("utf-8")).hexdigest()[:16]

new_doc = json.loads((LAB / "evidence" / "evidence_gate_522c414_t0.json").read_text(encoding="utf-8"))
base = digest(new_doc)
print(f"\nbaseline digest (522c414): {base}")
print("fixed totals():", json.dumps(totals(new_doc), ensure_ascii=False)[:220])

flipped = copy.deepcopy(new_doc)
flipped["cells"][7]["passed"] = not flipped["cells"][7]["passed"]
print(f"CONTROL-A  flip one cell's `passed`   -> {digest(flipped)}  differs={digest(flipped) != base}")

renamed = copy.deepcopy(new_doc)
renamed["cells"][9]["codes"] = ["SOMETHING_ELSE"]
print(f"CONTROL-B  change one cell's codes    -> {digest(renamed)}  differs={digest(renamed) != base}")

dropped = copy.deepcopy(new_doc)
dropped["cells"] = dropped["cells"][:-1]
print(f"CONTROL-C  drop one cell (1151)       -> {digest(dropped)}  differs={digest(dropped) != base}")

rolled = copy.deepcopy(new_doc)
rolled["summary"]["per_family_shape"]["step_free_wheelchair"]["osm_native"] = 99
print(f"CONTROL-D  change a rollup number     -> {digest(rolled)}  differs={digest(rolled) != base}")

for name in ("evidence_gate_e0fc697.json", "evidence_gate_66cad62.json",
             "evidence_gate_366cba6.json", "evidence_gate_snapshot_a_sep15.json"):
    p = LAB / "evidence" / name
    if not p.exists():
        print(f"           {name}: absent")
        continue
    doc = json.loads(p.read_text(encoding="utf-8"))
    d = digest(doc)
    print(f"           {name:<42} {d}  blocked={doc['summary'].get('cells_blocked')}/"
          f"{doc['summary'].get('cells_total')}  differs_from_new_run={d != base}")
```

## `harness_ord0210_repro.py`  (11580 B)

```python
"""ORD-0210 independent reproduction: does one node id give the same verdict on a clean vs dirty DB?

F delivered a gate for this on its own unpushed branch (`2dc3fa2`) and reported it bites 2/4 runs.
This is a **separate instrument**: it does not import, read or reuse F's test file - it runs the
named target (`backend/tests/test_qoder_anywhere_gates.py::test_g3_five_concurrent_hydrations_…`)
in **my own export of the tip** and measures the flip itself.

Shape per the order:
  * pass 1 deletes only this export tree's own test database, pass 2 inherits whatever pass 1 left;
  * the *resolved absolute* DB path and the row counts after each pass are receipted;
  * verdicts, both directions, named:
      clean PASS / dirty FAIL -> DIRTY_DB_FALSE_RED  (a green that only holds while the DB is empty)
      clean PASS / dirty PASS -> CONSISTENT_GREEN
      clean FAIL / dirty PASS -> DIRTY_DB_FALSE_GREEN
      clean FAIL / dirty FAIL -> CONSISTENT_RED  (a real red, not an instrument problem)
  * `_live.db` / `_preview.db` may never be touched or deleted; only `<this tree>/citynexus.db*`.

Env: `CITYNEXUS_AI_ENABLED` is left at its default (config.py:18 says false) and both key vars are
blanked, so no run here can reach a provider.  No ports, no HTTP server.

Usage:  python lab/tools/harness_ord0210_repro.py [--rounds 4]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
TARGET_FILE = "tests/test_qoder_anywhere_gates.py"
TARGET_NODE = "test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation"
BANNED = ("_live.db", "_preview.db")


def run(cmd: list[str], cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)


def parse_summary(out: str) -> dict:
    counts = {}
    for pat, name in ((r"(\d+) passed", "passed"), (r"(\d+) failed", "failed"),
                      (r"(\d+) skipped", "skipped"), (r"(\d+) error", "error")):
        m = re.search(pat, out)
        counts[name] = int(m.group(1)) if m else 0
    counts["node_ids_failed"] = sorted({ln.split("::")[-1].split(" ")[0]
                                        for ln in out.splitlines() if ln.startswith("FAILED")})
    # The receipt has to say *which* predicate moved, not just that something did.
    counts["assertion_lines"] = [ln.strip()[:300] for ln in out.splitlines()
                                 if ln.startswith(("FAILED", "E  ")) or "assert" in ln[:12]]
    counts["summary_tail"] = [ln for ln in out.splitlines() if ln.strip()][-2:]
    # ORD-0211 changed which database the process actually opens; the suite's own receipt line is
    # the only honest way to know, since a bare config probe no longer reflects the run.
    counts["db_headers"] = [ln.strip()[:220] for ln in out.splitlines()
                            if "ORD-0211 test database" in ln]
    return counts


def db_from_header(lines):
    for ln in lines or []:
        start = ln.find("resolved=")
        if start < 0:
            continue
        rest = ln[start + len("resolved="):]
        end = rest.find(" | exists=")
        if end > 0:
            return Path(rest[:end])
    return None


def db_rows(db: Path) -> dict:
    if not db.exists():
        return {"<no file>": True}
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=5)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        hints = ("hydration", "journey", "traveler", "place", "canonical")
        out = {}
        for t in tables:
            if any(h in t for h in hints):
                try:
                    out[t] = conn.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
                except sqlite3.Error:
                    out[t] = -1
        return out
    finally:
        conn.close()


def wipe_own_tree_db(tree: Path) -> list[str]:
    """Delete only this export's own test DB, refusing anything resembling a shared file."""
    removed = []
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = tree / (f"citynexus.db{suffix}")
        if any(b in p.name for b in BANNED):
            raise SystemExit(f"refusing to touch {p}")
        if not str(p.resolve()).startswith(str(LAB.resolve())):
            raise SystemExit(f"refusing: {p} is outside my lab")
        if p.exists():
            p.unlink()
            removed.append(p.name)
    return removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--head", default="0cd697b")
    ap.add_argument("--tag", default="", help="suffix for the receipt filename")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    tree = LAB / f"snap_{args.head}" / "backend"
    if not (tree / TARGET_FILE).exists():
        print(f"missing {tree / TARGET_FILE}")
        return 2

    env = dict(os.environ)
    # Mirrors the command F receipted (bare `pytest`, no env strategy), with two extra
    # guarantees: no bytecode written into the export, and no AI key reachable at all.
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "DEEPSEEK_API_KEY": "",
                "CITYNEXUS_AI_API_KEY": ""})
    env.pop("CITYNEXUS_DATABASE_URL", None)  # the whole point: let the app resolve its own
    env.pop("CITYNEXUS_AI_ENABLED", None)     # default is false (config.py:18)

    resolved = run([str(PY), "-c",
                    "from app.core.config import settings; "
                    "print(settings.database_url); import os; "
                    "print(os.path.abspath('citynexus.db')); print('ai_enabled', settings.ai_enabled)"],
                   tree, env)
    print(f"[resolved db] {resolved.stdout.strip().replace(chr(10), ' | ')}")
    lines = resolved.stdout.strip().splitlines()
    db = Path(lines[1]) if len(lines) > 1 else tree / "citynexus.db"
    for b in BANNED:
        if b in str(db):
            raise SystemExit(f"refusing: resolved path names a shared file {db}")

    collected = run([str(PY), "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                     "tests"], tree, env)
    tail = [l for l in collected.stdout.splitlines() if l.strip()][-1:]
    print(f"[collect-only whole suite] rc={collected.returncode} tail: {tail}")

    import tempfile
    tmp_root = Path(tempfile.gettempdir())
    temp_before = len(list(tmp_root.glob("cnx_pytest_*")))
    leftover = len(list(tree.glob("citynexus.db*")))
    print(f"[pre-run] suite temp dirs already present={temp_before} "
          f"working-tree db files={leftover}")

    rounds = []
    for n in range(1, args.rounds + 1):
        removed = wipe_own_tree_db(tree)
        # no `-q`: it suppresses the header line that receipts the resolved database
        p1 = run([str(PY), "-m", "pytest", TARGET_FILE, "--tb=line",
                  "-p", "no:cacheprovider"], tree, env)
        s1 = parse_summary(p1.stdout)
        db1 = db_from_header(s1["db_headers"]) or db
        rows1 = db_rows(db1) if db1.exists() else {"<no file at resolved path>": str(db1)}
        p2 = run([str(PY), "-m", "pytest", TARGET_FILE, "--tb=line",
                  "-p", "no:cacheprovider"], tree, env)
        s2 = parse_summary(p2.stdout)
        db2 = db_from_header(s2["db_headers"]) or db
        rows2 = db_rows(db2) if db2.exists() else {"<no file at resolved path>": str(db2)}
        g1 = TARGET_NODE not in s1["node_ids_failed"]
        g2 = TARGET_NODE not in s2["node_ids_failed"]
        shared_db = bool(db1) and bool(db2) and Path(db1).resolve() == Path(db2).resolve()
        flip = (g1 != g2)
        verdict = ("CONSISTENT_GREEN" if g1 and g2 else
                   "DIRTY_DB_FALSE_GREEN" if (not g1) and g2 else
                   "DIRTY_DB_FALSE_RED" if g1 and (not g2) else "CONSISTENT_RED")
        if flip and not shared_db:
            # the passes did not share a database, so nothing was "fed" - call it what it is
            verdict = "FLIP_WITHOUT_SHARED_STATE(" + verdict + ")"
        row = {"round": n, "deleted_before_pass1": removed, "shared_db": shared_db,
               "pass1_clean": {"rc": p1.returncode, **s1, "g3_passed": g1, "db_rows": rows1},
               "pass2_dirty": {"rc": p2.returncode, **s2, "g3_passed": g2, "db_rows": rows2},
               "verdict": verdict}
        rounds.append(row)
        print(f"round {n}: clean rc={p1.returncode} {s1['passed']}p/{s1['failed']}f/{s1['skipped']}s "
              f"g3={'PASS' if g1 else 'FAIL'} | dirty rc={p2.returncode} {s2['passed']}p/{s2['failed']}f/"
              f"{s2['skipped']}s g3={'PASS' if g2 else 'FAIL'} -> {verdict}")
        row["db_paths"] = {"pass1": str(db1), "pass2": str(db2),
                           "leftover_in_tree_after": str((tree / "citynexus.db").exists())}
        print(f"         db receipt pass1: {(s1['db_headers'] or ['-'])[0][:120]}")
        print(f"         db receipt pass2: {(s2['db_headers'] or ['-'])[0][:120]}")
        grew = {k: (rows1.get(k), rows2.get(k)) for k in set(rows1) | set(rows2)
                if rows1.get(k) != rows2.get(k)}
        print(f"         rows that moved between passes: {grew or 'none'}")
        for tag, st in (("clean", s1), ("dirty", s2)):
            for line in st["assertion_lines"][:3]:
                print(f"           [{tag}] {line[:150]}")

    flips = [r for r in rounds if "FLIP" in r["verdict"] or "FALSE" in r["verdict"]]
    receipt = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "order": "ORD-0210 independent reproduction",
        "head": args.head, "worktree": str(tree), "interpreter": str(PY),
        "interpreter_version": run([str(PY), "--version"], tree, env).stdout.strip(),
        "command": f"pytest {TARGET_FILE} -q --tb=line -p no:cacheprovider   (twice per round)",
        "collect_only_whole_suite": {"rc": collected.returncode, "tail": tail},
        "db_abs_path": str(db), "ban_check": "no _live.db/_preview.db in path or deletion list",
        "rounds": rounds,
        "suite_temp_dirs": {"before": temp_before,
                            "after": len(list(tmp_root.glob("cnx_pytest_*")))},
        "working_tree_db_files_after": len(list(tree.glob("citynexus.db*"))),
        "verdict_counts": {v: sum(1 for r in rounds if r["verdict"] == v)
                           for v in ("CONSISTENT_GREEN", "CONSISTENT_RED",
                                     "DIRTY_DB_FALSE_GREEN", "DIRTY_DB_FALSE_RED")},
        "target_node": f"{TARGET_FILE}::{TARGET_NODE}",
    }
    # A second invocation must not clobber a first receipt: the file names its own round count
    # and wall-clock minute.
    out = LAB / "evidence" / (f"ord0210_repro_{args.head}_{args.rounds}r"
                              f"_{time.strftime('%H%M')}{('_' + args.tag) if args.tag else ''}.json")
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nrounds={len(rounds)} flips_detected={len(flips)} "
          f"({'+'.join(sorted({r['verdict'] for r in flips}) or ['none'])})")
    print(f"verdict counts: {receipt['verdict_counts']}")
    print(f"receipt: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
