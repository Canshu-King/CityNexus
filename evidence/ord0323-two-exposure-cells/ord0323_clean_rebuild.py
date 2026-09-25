"""Clean the two scratch structures in ORD-0323's matrix rebuild, then run it."""
from __future__ import annotations

import ast
import pathlib
import re

P = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ord0323_matrix_from_disk.py")
t = P.read_text(encoding="utf-8")

old = '''    rows = {}
    for f in sorted(ev.glob("*.json")) if ev.exists() else []:
        body = json.loads(f.read_text(encoding="utf-8"))
        rows[str(body.get("arm"))] = {k: v for k, v in body.items() if k in A.__dict__.get("KEEP", body)} \\
            if False else body'''
new = '''    rows = {}
    for f in (sorted(ev.glob("*.json")) if ev.exists() else []):
        body = json.loads(f.read_text(encoding="utf-8"))
        rows[str(body.get("arm"))] = body'''
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new)

old2 = '''                     "rc": int(rep.get("stats", {}).get("suites") is not None and 1 or 1) if False else
                     (0 if all(v == "passed" for v in per_arm.values()) else 1),
                     "run_id": rid,'''
new2 = '''                     "rc": rc_of(rep, rid),
                     "run_id": rid,'''
assert t.count(old2) == 1, t.count(old2)
t = t.replace(old2, new2)

old3 = '''def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()'''
new3 = '''def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rc_of(reporter_json, rid):
    """The reporter file is the run's own answer; its stats decide rc, with the log only as a fallback.

    `stats.outcome` is a count of specs by outcome and may legitimately omit a bucket (no skipped spec
    exists), so a missing key is 0, never 1. If neither shape answers, the pass refuses to guess."""
    stats = (reporter_json or {}).get("stats") or {}
    outcome = stats.get("outcome")
    if isinstance(outcome, dict):
        bad = sum(int(v) for k, v in outcome.items() if k not in ("expected", "passed"))
        return 0 if bad == 0 else 1
    log = WORK / f"ord0323_{rid}.log"
    if log.exists():
        m = re.search(r"\\s(\\d+) failed", log.read_text(encoding="utf-8", errors="replace"))
        if m:
            return 0 if int(m.group(1)) == 0 else 1
    raise SystemExit(f"neither stats.outcome nor a summary line is readable for {rid}")'''
assert t.count(old3) == 1
t = t.replace(old3, new3)

old4 = '''    "measurement_scope": dict(A.__dict__.get("_", {}), **{
        "generation": {"baseline_named_in_the_order": A.BASE, "candidate": CAND,
                       "candidate_parent": A.PARENT, "pre_fix_blob_source": A.PARENT},
        "tree": str(LANE), "spec": A.SPEC,
        "mode": "CITYNEXUS_E2E_AUTHORITATIVE=1, AI disabled, both servers started by that pass's invocation",
        "database_per_run": "one sqlite file per run id, named by CITYNEXUS_DATABASE_URL"}),'''
new4 = '''    "measurement_scope": {
        "generation": {"baseline_named_in_the_order": A.BASE, "candidate": CAND,
                       "commits_between": int(subprocess.run(
                           ["git", "-C", str(LANE), "rev-list", "--count", f"{A.BASE}..{CAND}"],
                           capture_output=True, text=True).stdout.strip()),
                       "pre_fix_bytes_taken_from": A.PARENT},
        "tree": str(LANE), "spec": A.SPEC,
        "ports": {s: {"frontend": A.BASE_PORT + i, "backend": A.BASE_PORT + i + 38000}
                  for i, s in enumerate(A.ORDER)},
        "mode": "CITYNEXUS_E2E_AUTHORITATIVE=1, AI disabled, both servers started by that pass's invocation",
        "database_per_run": "one sqlite file per run id, named by CITYNEXUS_DATABASE_URL",
    },'''
assert t.count(old4) == 1
t = t.replace(old4, new4)
P.write_text(t, encoding="utf-8", newline="\n")
ast.parse(t)
print("rebuild script cleaned")
