"""ORD-0323 arms: the two Q64 cells, judged from both directions, with each direction's own counter-example.

Six shapes around the candidate commit (which is HEAD while this runs; every mutant is applied to the
working tree and restored byte-exact in a finally):

  fixed                     the candidate as committed         -> N1/N2/N3 all green
  cell1_baseline_sink       boundary file = the tip's blob      -> the pre-fix screen, reproduced on this tree
  cell1_leak_beside_fields  fields still render, prose added    -> only the NEGATIVE assertion may go red
  cell1_fields_gone         prose stays away, fields deleted    -> only the POSITIVE assertion may go red
  cell2_baseline_throw      workbench file = the tip's blob     -> the pre-fix screen, reproduced on this tree
  cell2_leak_beside_fields  device sentence + the reply's words -> only the NEGATIVE assertion may go red
  cell2_fields_blind        sentence without status/type        -> only the POSITIVE assertion may go red

The two one-sided shapes per cell are the point: `*_leak_*` reddens the leak assertion while the
reading assertion stays green, and `*_fields_*` does the opposite. If one arm could not tell them
apart, the pair would be a single claim written twice -- which is what the commander's 两个观测量不许互替
forbids. Per-arm outcomes come from Playwright's own JSON reporter; the rendered readings come from the
spec's own per-arm evidence file, so nothing here paraphrases a console tail.
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
BOUNDARY = FE / "src/components/ProductErrorBoundary.tsx"
WORKBENCH = FE / "src/features/inbox/JourneyInboxWorkbench.tsx"
BOUNDARY_PATH = "frontend/src/components/ProductErrorBoundary.tsx"
WORKBENCH_PATH = "frontend/src/features/inbox/JourneyInboxWorkbench.tsx"
SPEC = "e2e/qoder-ord0323-two-exposure-cells.spec.ts"
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0323_20260926")
WORK.mkdir(exist_ok=True)
BASE = "9a669c8bec863fadf31d5158f4a1be66aec49f23"
ARMS = ("N1", "N2", "N3")
ALL_GREEN = {a: "passed" for a in ARMS}
SHORT = {"fixed": "fix", "cell1_baseline_sink": "c1b", "cell1_leak_beside_fields": "c1l",
         "cell1_fields_gone": "c1f", "cell2_baseline_throw": "c2b",
         "cell2_leak_beside_fields": "c2l", "cell2_fields_blind": "c2f"}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def show(ref: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(LANE), "show", f"{ref}:{path}"],
                          capture_output=True, check=True).stdout


BASELINE_BOUNDARY = show(BASE, BOUNDARY_PATH)
BASELINE_WORKBENCH = show(BASE, WORKBENCH_PATH)

# anchors taken from the committed candidate; each must occur exactly once in its own file
C1_RENDER = "            {fieldsText(fields)}\n"
C1_LEAK = "            {fieldsText(fields)}\n            {String(error?.message || error)}\n"
C1_FIELDS_BLOCK = (
    '    `caught_at=${fields?.caught_at ?? ""}`,\n'
    '    `route=${fields?.route ?? ""}`,\n'
    '    `failures_caught_here=${fields ? fields.failures_caught_here : ""}`,\n'
    '    `online_at_this_device=${fields ? (fields.online_at_this_device ? "yes" : "no") : ""}`,\n'
)
C2_THROW = ('    throw new Error(deviceSentenceForRejected(response.status, '
            'response.headers.get("content-type") ?? ""));\n')
C2_LEAK = (
    '    const leaked = (payload as { detail?: string; error?: { message?: string } }).detail\n'
    '      ?? (payload as { error?: { message?: string } }).error?.message\n'
    '      ?? "";\n'
    '    throw new Error(deviceSentenceForRejected(response.status, '
    'response.headers.get("content-type") ?? "") + " " + leaked);\n'
)
C2_FIELD_A = "（HTTP ${status}，内容类型 ${type}）"
C2_FIELD_B = "(HTTP ${status}, content type ${type})"

RUNS = {
    "fixed": {"expect": dict(ALL_GREEN)},
    "cell1_baseline_sink": {"file": BOUNDARY, "bytes": BASELINE_BOUNDARY,
                            "expect": dict(ALL_GREEN, N1="failed")},
    "cell1_leak_beside_fields": {"patches": [(BOUNDARY, C1_RENDER, C1_LEAK)],
                                 "expect": dict(ALL_GREEN, N1="failed"), "intended": "negative_only"},
    "cell1_fields_gone": {"patches": [(BOUNDARY, C1_FIELDS_BLOCK, "")],
                          "expect": dict(ALL_GREEN, N1="failed"), "intended": "positive_only"},
    "cell2_baseline_throw": {"file": WORKBENCH, "bytes": BASELINE_WORKBENCH,
                             "expect": dict(ALL_GREEN, N2="failed", N3="failed")},
    "cell2_leak_beside_fields": {"patches": [(WORKBENCH, C2_THROW, C2_LEAK)],
                                 "expect": dict(ALL_GREEN, N2="failed", N3="failed"),
                                 "intended": "negative_only"},
    "cell2_fields_blind": {"patches": [(WORKBENCH, C2_FIELD_A, "，请再看一次"), (WORKBENCH, C2_FIELD_B, ", look again")],
                           "expect": dict(ALL_GREEN, N2="failed", N3="failed"), "intended": "positive_only"},
}
ORDER = list(RUNS)


def apply(cfg):
    """Either a whole-file revert to the tip's blob, or exact unique-string patches."""
    if "bytes" in cfg:
        p = cfg["file"]
        pristine = p.read_bytes()
        if pristine == cfg["bytes"]:
            raise SystemExit(f"the declared baseline mutant changes no bytes in {p.name}")
        p.write_bytes(cfg["bytes"])
        return {p: pristine}
    touched = {}
    for p, _needle, _repl in cfg.get("patches", []):
        touched[p] = p.read_bytes()
    text = {p: b.decode("utf-8") for p, b in touched.items()}
    for p, needle, repl in cfg.get("patches", []):
        hits = text[p].count(needle)
        if hits != 1:
            raise SystemExit(f"anchor occurs {hits} times, expected exactly 1 in {p.name}: {needle[:70]!r}")
        text[p] = text[p].replace(needle, repl, 1)
    for p, new in text.items():
        if new.encode("utf-8") == touched[p]:
            raise SystemExit(f"the declared mutant changes no bytes in {p.name}")
        p.write_bytes(new.encode("utf-8"))
    return touched


def restore(pristine):
    for p, b in pristine.items():
        p.write_bytes(b)


def env_for(run_id, port):
    e = dict(os.environ)
    e.update({
        "CITYNEXUS_E2E_AUTHORITATIVE": "1",
        "CITYNEXUS_E2E_PORT": str(port),
        "CITYNEXUS_BACKEND_PORT": str(int(port) + 38000),
        "CITYNEXUS_PYTHON": r"D:\moodle\CityNexus\.venv\Scripts\python.exe",
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{(LANE / 'backend' / ('_' + run_id + '.db')).as_posix()}",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_EVIDENCE_DIR": str(WORK / f"e2e_{run_id}"),
        "PLAYWRIGHT_JSON_OUTPUT_NAME": str(WORK / f"ord0323_{run_id}.json"),
    })
    for k in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
        e.pop(k, None)
    return e


def play(run_id, port):
    r = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test",
                        "-c", "playwright.config.ts", SPEC, "--reporter=json"],
                       cwd=str(FE), env=env_for(run_id, port),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=2400)
    got = {}
    p = WORK / f"ord0323_{run_id}.json"
    if p.exists():
        rep = json.loads(p.read_text(encoding="utf-8"))

        def walk(n):
            for s in n.get("suites", []) or []:
                walk(s)
            for sp in n.get("specs", []) or []:
                m = re.match(r"^(N[123])_", sp.get("title", ""))
                if not m:
                    continue
                for tt in sp.get("tests") or []:
                    for res in tt.get("results") or []:
                        got.setdefault(m.group(1), res.get("status"))
        walk({"suites": rep.get("suites") or []})
    (WORK / f"ord0323_{run_id}.log").write_text((r.stdout or "") + (r.stderr or ""), "utf-8", newline="\n")
    return {"rc": r.returncode, "reporter_outcomes": got, "report": p.name, "log": f"ord0323_{run_id}.log"}


def main():
    tip = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    parent = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD^"],
                            capture_output=True, text=True).stdout.strip()
    if subprocess.run(["git", "-C", str(LANE), "merge-base", "--is-ancestor", BASE, "HEAD"],
                      capture_output=True).returncode != 0:
        raise SystemExit(f"the order's baseline {BASE[:12]} is not an ancestor of HEAD; not measuring here")
    span = int(subprocess.run(["git", "-C", str(LANE), "rev-list", "--count", f"{BASE}..HEAD"],
                              capture_output=True, text=True).stdout.strip())
    print(f"measuring candidate {tip} ({span} commit(s) above baseline {parent}={BASE[:12]})")
    # A spec that cannot be collected produces a matrix of nulls, which reads like an inconclusive
    # measurement and is really a broken instrument: tsc's configs cover src/**, so a broken spec typechecks.
    collect = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test",
                              "-c", "playwright.config.ts", SPEC, "--list"],
                             cwd=str(FE), env=env_for("0323collect" + time.strftime("%H%M%S"), 4469),
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if collect.returncode != 0:
        raise SystemExit("the spec does not even collect: "
                         + ((collect.stdout or "") + (collect.stderr or ""))[-900:])
    print("collect gate ok:", [l for l in (collect.stdout or "").splitlines() if l.startswith("Total:")][-1:])

    stamp = time.strftime("%H%M%S")
    results = {}
    for i, shape in enumerate(ORDER):
        cfg = RUNS[shape]
        pristine = None
        try:
            pristine = apply(cfg)
            digests = {"boundary": sha(BOUNDARY)[:16], "workbench": sha(WORKBENCH)[:16]}
            run_id = "0323" + SHORT[shape] + stamp[-4:]
            res = play(run_id, 4460 + i)
            ev = WORK / f"e2e_{run_id}" / "ord0323"
            per = {}
            if ev.exists():
                for f in sorted(ev.glob("*.json")):
                    body = json.loads(f.read_text(encoding="utf-8"))
                    per[str(body.get("arm"))] = body
            res["run_id"] = run_id
            res["evidence_dir"] = str(ev)
            res["mutant_digests"] = digests
            res["per_arm"] = {a: b.get("test_status") for a, b in per.items()}
            res["readings"] = per
            res["expected"] = cfg["expect"]
            res["intended"] = cfg.get("intended")
            res["meets_expectation"] = all(
                res["per_arm"].get(a) == ("failed" if want == "failed" else want)
                for a, want in cfg["expect"].items())
            res["arms_without_a_reading"] = [a for a in cfg["expect"] if a not in res["readings"]]
            # the reporter's own status and the spec's self-reported status must agree, or the instrument
            # and the evidence disagree about what ran
            res["reporter_and_evidence_agree"] = all(
                res["per_arm"].get(a) == res["reporter_outcomes"].get(a) for a in cfg["expect"])
            results[shape] = res
            print(f"\n{shape}: rc={res['rc']} run={run_id} as_expected={res['meets_expectation']} "
                  f"agree={res['reporter_and_evidence_agree']}")
            for a in ARMS:
                rd = res["readings"].get(a) or {}
                leaks = rd.get("leaked_needles_still_on_screen")
                print(f"   {a} want={cfg['expect'].get(a, '-'):7s} got={str(res['per_arm'].get(a)):7s} "
                      f"leaks={json.dumps(leaks, ensure_ascii=False)[:70] if leaks is not None else '-'} "
                      f"err={str(rd.get('error_head'))[:66]}")
            if shape == "fixed" and not res["meets_expectation"]:
                raise SystemExit("the candidate itself is not green; the matrix would only measure a broken fix")
        finally:
            if pristine is not None:
                restore(pristine)
            ok = sha(BOUNDARY) == hashlib.sha256(show(tip, BOUNDARY_PATH)).hexdigest()
            ok2 = sha(WORKBENCH) == hashlib.sha256(show(tip, WORKBENCH_PATH)).hexdigest()
            dirty = subprocess.run(["git", "-C", str(LANE), "status", "--porcelain", "frontend/src"],
                                   capture_output=True, text=True).stdout.strip()
            print(f"   restored boundary={ok} workbench={ok2} src dirty={dirty[:60]!r}")
            if not (ok and ok2):
                raise SystemExit("the source did not come back byte-exact against the committed candidate; stopping")

    green_fixed = all(results["fixed"]["per_arm"].get(a) == "passed" for a in ARMS)
    verdict = ("TEETH_AND_BASELINE"
               if green_fixed
               and all(r["meets_expectation"] for r in results.values())
               and all(r["arms_without_a_reading"] == [] for r in results.values())
               and all(r["reporter_and_evidence_agree"] for r in results.values())
               else "MATRIX_NOT_AS_EXPECTED")
    receipt = {
        "schema": "CNX_ORD0323_ARMS_R1",
        "order": "ORD-0323",
        "lane": "B c01d72a3",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "measurement_scope": {
            "generation": {"baseline_tip": BASE, "candidate": tip,
                           "commits_between": span,
                           "baseline_provenance": "the tip the commander named in ORD-0323 (9a669c8b), "
                                                  "re-read with git ls-remote before this run"},
            "tree": str(LANE), "spec": SPEC,
            "ports": {s: {"frontend": 4460 + i, "backend": 4460 + i + 38000} for i, s in enumerate(ORDER)},
            "database_per_run": "one sqlite file per run id, named by CITYNEXUS_DATABASE_URL",
            "mode": "CITYNEXUS_E2E_AUTHORITATIVE=1, AI disabled, both servers started by each invocation",
        },
        "files": {
            "ProductErrorBoundary.tsx": {"candidate_sha256": sha(BOUNDARY),
                                         "baseline_sha256": hashlib.sha256(BASELINE_BOUNDARY).hexdigest()},
            "JourneyInboxWorkbench.tsx": {"candidate_sha256": sha(WORKBENCH),
                                          "baseline_sha256": hashlib.sha256(BASELINE_WORKBENCH).hexdigest()},
        },
        "shapes": {s: {k: v for k, v in r.items() if k != "readings"} for s, r in results.items()},
        "per_arm_readings": {s: {a: {k: v for k, v in (r["readings"].get(a) or {}).items()
                                     if k in ("panel_copy", "error_detail_text", "console_error_count",
                                              "console_error_head", "overlay_hosts", "message_text",
                                              "pending_text", "fold_summary", "fold_text",
                                              "fold_code_visible", "status_line",
                                              "leaked_needles_still_on_screen", "test_status", "error_head")}
                                for a in ARMS}
                             for s, r in results.items()},
        "verdict": verdict,
        "interpretation_limit": "each shape's own evidence files are the readings; this file only aggregates "
                                "them. derived_result stays null: signing a level belongs to the red team (B-1).",
        "claimed_result": None,
        "derived_result": None,
    }
    txt = json.dumps(receipt, ensure_ascii=False, indent=1)
    (WORK / "ord0323_arms_matrix.json").write_text(txt, "utf-8", newline="\n")
    print("\nverdict:", verdict, "->", WORK / "ord0323_arms_matrix.json")
    print("matrix bytes:", len(txt.encode("utf-8")))
    return 0 if verdict == "TEETH_AND_BASELINE" else 5


if __name__ == "__main__":
    sys.exit(main())
