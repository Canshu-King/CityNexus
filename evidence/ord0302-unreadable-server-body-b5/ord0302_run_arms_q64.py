"""ORD-0302 arms: three shapes, each mutant proven to have landed, everything restored byte-exact.

  fixed            the candidate as written              -> N1 / N2 / N3 must all hold
  ca_unsafe_read   put the two `body.detail` reads back  -> N1 must go red. N2 must STAY green: a body that
                 without the optional chain                 does carry `error.message` returns before the
                                                          detail read, so a run where both go red would prove
                                                          nothing about which line carries the defect.
  ca_null_on_network  write `failureReason: null` again   -> N3 must go red (the block leaves the DOM) while
                                                          N1 stays green.

Per-arm outcome comes from Playwright's own JSON reporter; the rendered readings come from the spec's own
evidence file, one per run id, so nothing here is a paraphrase of a console tail.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
FE = LANE / "frontend"
SHEET = FE / "src/features/planning/PlanWithAiSheet.tsx"
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
SPEC = "e2e/qoder-ord0302-unreadable-server-body.spec.ts"
BASE = os.environ.get("CNX_0302_BASE", "dc964086c9d412573ac19d70b24b30e6c3ee6168")
SAFE = "  const detail = (body as { detail?: unknown } | null)?.detail;"
UNSAFE = "  const detail = (body as { detail?: unknown }).detail;"
TAIL_CODE = "  return typeof detail === \"string\" ? detail.slice(0, 60).toUpperCase() : \"\";"
TAIL_SENT = "  if (typeof detail === \"string\" && detail.trim()) return detail;"
NOTE = "          failureReason: failureNote(null, \"no readable answer reached this device (network or origin)\"),"
X5_GATE = "            {(result?.failureReason || result?.summary || result?.rawReading) && ("
X5_PROMISE = "；原因原文在“技术详情”里，"
# Q64=① needs its own killer: put the forbidden shape back exactly as b4 had it.  If the two-directional
# assertion in X1 cannot see this, the assertion is theatre, so this mutant is the proof of its teeth.
TYPE_BYTES = "  bytes: number | null;\n};"
TYPE_BYTES_BACK = "  bytes: number | null;\n  body_head: string;\n};"
CAP_BYTES = "        bytes: raw === null ? null : new TextEncoder().encode(raw).length,\n"
CAP_BACK = CAP_BYTES + '        body_head: raw === null ? "" : raw.slice(0, 240),\n'
RENDER_BYTES = '                      {`bytes=${result.rawReading.bytes ?? ""}\\n`}\n'
RENDER_BACK = RENDER_BYTES + '                      {`body=${result.rawReading.body_head}`}\n'
ALL_PASS = {"N1": "passed", "N2": "passed", "N3": "passed", "X1": "passed", "X2": "passed"}

RUNS = {
    "fixed": {"patches": [], "expect": dict(ALL_PASS)},
    "ca_unsafe_read": {"patches": [(SAFE + "\n" + TAIL_CODE, UNSAFE + "\n" + TAIL_CODE),
                                   (SAFE + "\n" + TAIL_SENT, UNSAFE + "\n" + TAIL_SENT)],
                       "intended": "N1",
                       "expect": dict(ALL_PASS, N1="failed")},
    "ca_null_on_network": {"patches": [(NOTE, "          failureReason: null,")],
                           "intended": "N3", "expect": dict(ALL_PASS, N3="failed")},
    # the two directions X-5's requirement ② names: take away the rendered block, or take away the pointer.
    # Either may not pass quietly, and neither may turn the other four arms red.
    "ca_x5_no_block": {"patches": [(X5_GATE, "            {(result?.failureReason || result?.summary) && (")],
                       "intended": "X1", "expect": dict(ALL_PASS, X1="failed")},
    "ca_x5_soft_promise": {"patches": [(X5_PROMISE, "；")],
                           "intended": "X1", "expect": dict(ALL_PASS, X1="failed")},
    # Q64=① : reverting the whitelist change must redden X1 (the leak direction) and nothing else
    "ca_q64_body_back": {"patches": [(TYPE_BYTES, TYPE_BYTES_BACK), (CAP_BYTES, CAP_BACK),
                                     (RENDER_BYTES, RENDER_BACK)],
                         "intended": "X1", "expect": dict(ALL_PASS, X1="failed")},
}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def apply_patches(patches):
    pristine = SHEET.read_bytes()
    text = pristine.decode("utf-8")
    for needle, repl in patches:
        # counted over the whole text, not line by line: the anchors here span two lines on purpose (the same
        # one-line statement appears twice in this file, and the following line is what tells them apart).
        hits = text.count(needle)
        if hits != 1:
            raise SystemExit(f"anchor occurs {hits} times, expected exactly 1: {needle[:70]!r}")
        text = text.replace(needle, repl, 1)
    if text.encode("utf-8") == pristine and patches:
        raise SystemExit("the declared mutant would change no bytes")
    if patches:
        SHEET.write_bytes(text.encode("utf-8"))
    return pristine


def env_for(run_id, port):
    e = dict(os.environ)
    e.update({
        "CITYNEXUS_E2E_AUTHORITATIVE": "1",
        "CITYNEXUS_E2E_PORT": port,
        "CITYNEXUS_BACKEND_PORT": str(int(port) + 38000),
        "CITYNEXUS_PYTHON": r"D:\moodle\CityNexus\.venv\Scripts\python.exe",
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{(LANE / 'backend' / ('_' + run_id + '.db')).as_posix()}",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_EVIDENCE_DIR": str(WORK / f"e2e_ord0302_{run_id}"),
        "PLAYWRIGHT_JSON_OUTPUT_NAME": str(WORK / f"ord0302_{run_id}.json"),
    })
    for k in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
        e.pop(k, None)
    return e


def play(run_id, port):
    # a fresh run id per shape: the suite's own guard refuses to reuse a run id whose database still exists,
    # and reusing one would be the wrong thing to work around
    rid = run_id + time.strftime("%H%M%S")[-4:]
    res = _play(rid, port)
    res["run_id"] = rid
    return res


def _play(run_id, port):
    r = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test",
                        "-c", "playwright.config.ts", SPEC, "--reporter=json"],
                       cwd=str(FE), env=env_for(run_id, port),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    out = {}
    p = WORK / f"ord0302_{run_id}.json"
    if p.exists():
        rep = json.loads(p.read_text(encoding="utf-8"))

        def walk(n):
            for s in n.get("suites", []) or []:
                walk(s)
            for sp in n.get("specs", []) or []:
                m = re.match(r"ord0302-(N[123]|X[12])", sp.get("title", ""))
                if not m:
                    continue
                for tt in sp.get("tests") or []:
                    for res in tt.get("results") or []:
                        out.setdefault(m.group(1), res.get("status"))
        walk({"suites": rep.get("suites") or []})
    (WORK / f"ord0302_{run_id}.log").write_text((r.stdout or "") + (r.stderr or ""), "utf-8", newline="\n")
    return {"rc": r.returncode, "outcomes": out, "report": p.name, "log": f"ord0302_{run_id}.log"}


RUNS_ORDER = list(RUNS)
tip = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
parent = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD^"], capture_output=True,
                        text=True).stdout.strip()
if subprocess.run(["git", "-C", str(LANE), "merge-base", "--is-ancestor", BASE, tip],
                  capture_output=True).returncode != 0:
    raise SystemExit(f"the order's tip {BASE[:12]} is not an ancestor of {tip[:12]}; not measuring here")
# A spec that cannot be collected produces a matrix of nulls, which reads like an inconclusive measurement
# and is really a broken instrument: the typecheck configs only cover src/**, so `tsc` passes a broken spec.
collect = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test", "-c", "playwright.config.ts",
                          SPEC, "--list"], cwd=str(FE), env=env_for("0302collect" + time.strftime("%H%M%S"),
                                                                    "4499"),
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
if collect.returncode != 0:
    raise SystemExit("the spec does not even collect; refusing to run a matrix that would read as nulls: "
                     + ((collect.stdout or "") + (collect.stderr or ""))[-700:])
total = [l for l in (collect.stdout or "").splitlines() if l.startswith("Total:")]
print("collect gate ok:", total[-1:] or "(no Total line)")
stamp = time.strftime("%H%M%S")
results, digests = {}, {}
for shape, cfg in RUNS.items():
    # A stranded mutant is the one outcome worse than no measurement: an earlier pass raised between
    # apply_patches() and the restore, and the next run then "proved" the fix broken. Everything after the
    # patch therefore sits in a try, and the restore is a finally.
    pristine = SHEET.read_bytes()
    try:
        apply_patches(cfg["patches"])
        digests[shape] = {"before": hashlib.sha256(pristine).hexdigest()[:16], "running": sha(SHEET)[:16]}
        run_id = ("0302" + {"fixed": "fix", "ca_unsafe_read": "unr", "ca_null_on_network": "nul",
                            "ca_x5_no_block": "xnb", "ca_x5_soft_promise": "xsp",
                            "ca_q64_body_back": "q64b"}[shape] + stamp[-4:])
        res = play(run_id, str(4490 + RUNS_ORDER.index(shape)))
        # the run id lives inside `res` (play() appends its own time suffix so no two shapes share a database)
        ev_dir = WORK / f"e2e_ord0302_{res['run_id']}" / "ord0302"
        per = {}
        for f in sorted(ev_dir.glob("arm_*.json")) if ev_dir.exists() else []:
            body = json.loads(f.read_text(encoding="utf-8"))
            per[str(body.get("arm"))] = body
        res["evidence_dir"] = str(ev_dir)
        # the per-arm file carries its own status, which is what the expectation is compared against: a shared
        # merged evidence file lost an arm's reading to a second worker last time this suite ran
        res["per_arm"] = {a: {"status": v.get("status"), "expectation": v.get("expectation")}
                          for a, v in per.items()}
        res["readings"] = {a: (v.get("reading") or {}) for a, v in per.items()}
        res["expected"] = cfg["expect"]
        res["intended"] = cfg.get("intended")
        res["meets_expectation"] = all(
            ((res["per_arm"].get(a) or {}).get("status") in ("failed", "timedOut")) if want == "failed"
            else (res["per_arm"].get(a) or {}).get("status") == want for a, want in cfg["expect"].items())
        res["arms_without_a_reading"] = [a for a in cfg["expect"] if a not in res["readings"]]
        results[shape] = res
        print(f"\n{shape}: rc={res['rc']} run={run_id} as_expected={res['meets_expectation']} "
              f"digest {digests[shape]['before']} -> {digests[shape]['running']}")
        for a, want in cfg["expect"].items():
            rd = res["readings"].get(a) or {}
            print(f"   {a} want={want:7s} got={str((res['per_arm'].get(a) or {}).get('status')):7s} "
                  f"verdict={rd.get('verdict')} status={ (rd.get('read') or {}).get('status') } "
                  f"count={ (rd.get('read') or {}).get('details_count', (rd.get('read') or {})
                                                     .get('detail_block_attached')) } "
                  f"label={ str((rd.get('read') or {}).get('label'))[:14] } "
                  f"reason={ str((rd.get('read') or {}).get('reason'))[:34] }")
    finally:
        SHEET.write_bytes(pristine)
        digests.setdefault(shape, {})["restored"] = sha(SHEET) == hashlib.sha256(pristine).hexdigest()
        dirty = subprocess.run(["git", "-C", str(LANE), "status", "--porcelain", "frontend/src"],
                               capture_output=True, text=True).stdout.strip()
        print(f"   restored={digests[shape]['restored']} src dirty={dirty[:80]!r}")
        if not digests[shape]["restored"]:
            raise SystemExit("the source did not come back byte-exact; stopping before any verdict")

verdict = ("TEETH_AND_BASELINE"
           if (all(r["meets_expectation"] for r in results.values())
               and all(d["restored"] for d in digests.values())
               and all((results["fixed"]["per_arm"].get(a) or {}).get("status") == "passed"
                   for a in ("N1", "N2", "N3", "X1", "X2")))
           else "INCONCLUSIVE")
out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "order": "ORD-0302 · arms", "lane": "B c01d72a3",
       "base_tip": BASE, "candidate_tip": tip, "spec": SPEC, "runs": results, "digests": digests,
       "verdict": verdict, "derived_result": None}
(WORK / "ord0302_arms_run.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print(f"\nverdict={verdict} -> ord0302_arms_run.json")
sys.exit(0 if verdict == "TEETH_AND_BASELINE" else 1)
