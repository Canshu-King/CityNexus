"""ORD-0323 arms, revision 2 -- the order grew from two cells to ten (commander 03:43), so the matrix grows
with it. `ord0323_run_arms.py` (r1, published blob 4b96bc3c8408b1159e31a2bbcb6579e04a7717c0) is left
byte-for-byte untouched; a published coordinate is never rewritten, and this file is a new path.

Arms now four: N1 the boundary panel, N2 the two mount-time reads, N3 the confirmation fold, N4 the eight
legs D numbered T06-T13 (plus T05's fold slot, which N2/N3/N4 all touch).

  fixed                     the candidate as committed            -> N1..N4 all green
  cell1_baseline_sink       boundary file = the tip's blob         -> the pre-fix screen, reproduced here
  cell1_leak_beside_fields  fields still render, prose re-added    -> only N1's negative direction
  cell1_fields_gone         prose stays away, fields deleted       -> only N1's positive direction
  cell2_baseline_throw      workbench file = the tip's blob        -> all nine upstream sentences on screen
  cell2_fields_blind        slot copy loses status and fields      -> only the positive assertions
  cell2_status_frozen       every machine slot prints 503          -> only the leg-attribution assertions

`cell2_status_frozen` is the one that shows the readings are attributed: with one hardcoded status in every
machine slot, the legs that asked 503 still pass and the ones that asked 509 fail -- a slot that could not
tell its own request from another's is not a measurement.
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
SHEET = FE / "src/features/planning/PlanWithAiSheet.tsx"
SHEET_PATH = "frontend/src/features/planning/PlanWithAiSheet.tsx"
WORKBENCH = FE / "src/features/inbox/JourneyInboxWorkbench.tsx"
BOUNDARY_PATH = "frontend/src/components/ProductErrorBoundary.tsx"
WORKBENCH_PATH = "frontend/src/features/inbox/JourneyInboxWorkbench.tsx"
SPEC = "e2e/qoder-ord0323-two-exposure-cells.spec.ts"
BRANCH_NAME = subprocess.run(["git", "-C", str(LANE), "rev-parse", "--abbrev-ref", "HEAD"],
                                 capture_output=True, text=True).stdout.strip()
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0323_20260926")
BASE = "9a669c8bec863fadf31d5158f4a1be66aec49f23"
LEGS = ("T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13")
ARMS = ("N1", "N2", "N3") + LEGS + ("Q68a", "Q68b")
ALL_GREEN = {a: "passed" for a in ARMS}
SHORT = {"fixed": "fix", "cell1_baseline_sink": "c1b", "cell1_leak_beside_fields": "c1l",
         "cell1_fields_gone": "c1f", "cell2_baseline_throw": "c2b",
         "cell2_fields_blind": "c2f", "cell2_status_frozen": "c2s",
         "cell3_code_slot_back": "c3b"}
BASE_PORT = int(os.environ.get("CNX_0323_BASE_PORT", "4480"))


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def show(ref: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(LANE), "show", f"{ref}:{path}"],
                          capture_output=True, check=True).stdout


# the pre-fix bytes are taken from the candidate's own parent, not from the tip the order named: the
# branch was re-cut onto the live line, and those two blobs are identical there (proved in the receipt).
# the pre-fix bytes come from where this branch forked from the authority line -- not from HEAD^, which is
# one of my own commits and therefore already carries the fix (measured: "changes no bytes").
_first = subprocess.run(["git", "-C", str(LANE), "rev-list", "--max-count=1", "--tail-parents=0",
                         f"{BASE}..HEAD"], capture_output=True, text=True)
_mine = [l for l in subprocess.run(["git", "-C", str(LANE), "rev-list", f"{BASE}..HEAD"],
                                    capture_output=True, text=True).stdout.split() if l]
PARENT = subprocess.run(["git", "-C", str(LANE), "rev-parse", f"{_mine[-1]}^"],
                        capture_output=True, text=True).stdout.strip()
if subprocess.run(["git", "-C", str(LANE), "diff", "--quiet", PARENT, "HEAD", "--", BOUNDARY_PATH],
                  capture_output=True).returncode == 0:
    raise SystemExit(f"the declared baseline blob at {PARENT[:12]} equals HEAD's; that is not the pre-fix file")
BASELINE_SHEET = show(PARENT, SHEET_PATH)
BASELINE_BOUNDARY = show(PARENT, BOUNDARY_PATH)
BASELINE_WORKBENCH = show(PARENT, WORKBENCH_PATH)

C1_RENDER = "            {fieldsText(fields)}\n"
C1_LEAK = "            {fieldsText(fields)}\n            {String(error?.message || error)}\n"
C1_FIELDS_BLOCK = (
    '    `caught_at=${fields?.caught_at ?? ""}`,\n'
    '    `route=${fields?.route ?? ""}`,\n'
    '    `failures_caught_here=${fields ? fields.failures_caught_here : ""}`,\n'
    '    `online_at_this_device=${fields ? (fields.online_at_this_device ? "yes" : "no") : ""}`,\n'
)
C2_FIELDS_LINE = ('    return `http_status=${a.http_status ?? "none"} content_type=${ct || "none"} '
                  'evidence=${a.evidence_kind}`;\n')
C2_FIELDS_BLIND = '    return "http_status=none content_type=none evidence=none";\n'
C2_STATUS_FROZEN = '    return "http_status=503 content_type=application/json evidence=HTTP_RESPONSE";\n'
C2_COPY = "  const deviceCopy = (error: unknown): string => copyFor(classifyReadFailure(error), zh).body;\n"
C2_COPY_BLIND = "  const deviceCopy = (error: unknown): string => t(\"inbox.textFailed\");\n"
# Q68: the slot named 原因编号 may hold a code or nothing. Putting the deleted fallback back reddens only the
# leg that was shown prose, and leaves the leg that was shown a real server code green.
C3_NOW = (
    "  /* Q68 (CMDR 04:45): a slot named 原因编号 carries a code or it carries nothing. The reply's sentence\n"
    "     already has an attributed home in 技术详情 (Q67=①), and the caller's `|| PLACES_HTTP_n` /\n"
    "     `NO_PLANS_PRODUCED` fallbacks are this device's own readings. */\n"
    '  return "";\n}'
)
C3_WAS = (
    "  const detail = (body as { detail?: unknown } | null)?.detail;\n"
    '  return typeof detail === "string" ? detail.slice(0, 60).toUpperCase() : "";\n}'
)

RUNS = {
    "fixed": {"expect": dict(ALL_GREEN)},
    "cell1_baseline_sink": {"file": BOUNDARY, "bytes": BASELINE_BOUNDARY,
                            "expect": dict(ALL_GREEN, N1="failed")},
    "cell1_leak_beside_fields": {"patches": [(BOUNDARY, C1_RENDER, C1_LEAK)],
                                 "expect": dict(ALL_GREEN, N1="failed"), "intended": "negative_only"},
    "cell1_fields_gone": {"patches": [(BOUNDARY, C1_FIELDS_BLOCK, "")],
                          "expect": dict(ALL_GREEN, N1="failed"), "intended": "positive_only"},
    "cell2_baseline_throw": {"file": WORKBENCH, "bytes": BASELINE_WORKBENCH,
                             "expect": dict(ALL_GREEN, **{a: "failed" for a in ("N2", "N3") + LEGS})},
    "cell2_fields_blind": {"patches": [(WORKBENCH, C2_COPY, C2_COPY_BLIND), (WORKBENCH, C2_FIELDS_LINE, C2_FIELDS_BLIND)],
                           "expect": dict(ALL_GREEN, **{a: "failed" for a in ("N2", "N3") + LEGS}),
                           "intended": "positive_only"},
    "cell3_code_slot_back": {"patches": [(SHEET, C3_NOW, C3_WAS)],
                             "expect": dict(ALL_GREEN, Q68b="failed"),
                             "intended": "q68_only"},
    "cell2_status_frozen": {"patches": [(WORKBENCH, C2_FIELDS_LINE, C2_STATUS_FROZEN)],
                            "expect": dict(ALL_GREEN, T12="failed"),
                            "intended": "attribution_only"},
}
ORDER = [s for s in RUNS if not os.environ.get("CNX_0323_ONLY") or s in os.environ["CNX_0323_ONLY"].split(",")]
if not ORDER:
    raise SystemExit("CNX_0323_ONLY named no known shape")


def apply(cfg):
    if "bytes" in cfg:
        p = cfg["file"]
        pristine = p.read_bytes()
        if pristine == cfg["bytes"]:
            raise SystemExit(f"the declared baseline mutant changes no bytes in {p.name}")
        p.write_bytes(cfg["bytes"])
        return {p: pristine}
    touched = {p: p.read_bytes() for p, _n, _r in cfg.get("patches", [])}
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
                m = (re.match(r"^(N[123])_", sp.get("title", "")) or re.match(r"^N4_(T\d\d)_", sp.get("title", ""))
                     or re.match(r"^N6_(Q68[ab])_", sp.get("title", "")))
                if not m:
                    continue
                for tt in sp.get("tests") or []:
                    for res in tt.get("results") or []:
                        got.setdefault(m.group(1), res.get("status"))
        walk({"suites": rep.get("suites") or []})
    (WORK / f"ord0323_{run_id}.log").write_text((r.stdout or "") + (r.stderr or ""), "utf-8", newline="\n")
    return {"rc": r.returncode, "reporter_outcomes": got, "report": p.name, "log": f"ord0323_{run_id}.log"}


def main():
    tip = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"], capture_output=True,
                         text=True).stdout.strip()
    if subprocess.run(["git", "-C", str(LANE), "merge-base", "--is-ancestor", BASE, "HEAD"],
                      capture_output=True).returncode != 0:
        raise SystemExit(f"the order's baseline {BASE[:12]} is not an ancestor of HEAD; not measuring here")
    span = int(subprocess.run(["git", "-C", str(LANE), "rev-list", "--count", f"{BASE}..HEAD"],
                              capture_output=True, text=True).stdout.strip())
    print(f"measuring candidate {tip} ({span} commit(s) above baseline {BASE[:12]})")
    collect = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test",
                              "-c", "playwright.config.ts", SPEC, "--list"],
                             cwd=str(FE), env=env_for("0323collect" + time.strftime("%H%M%S"), BASE_PORT + 9),
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
            run_id = "0323" + SHORT[shape] + stamp[-4:]
            res = play(run_id, BASE_PORT + i)
            ev = WORK / f"e2e_{run_id}" / "ord0323"
            per = {}
            if ev.exists():
                for f in sorted(ev.glob("*.json")):
                    body = json.loads(f.read_text(encoding="utf-8"))
                    per[str(body.get("arm"))] = body
            res["run_id"] = run_id
            res["evidence_dir"] = str(ev)
            res["mutant_digests"] = {"boundary": sha(BOUNDARY)[:16], "workbench": sha(WORKBENCH)[:16]}
            res["per_arm"] = {a: b.get("test_status") for a, b in per.items()}
            res["readings"] = per
            res["expected"] = cfg["expect"]
            res["intended"] = cfg.get("intended")
            res["meets_expectation"] = all(
                res["per_arm"].get(a) == ("failed" if want == "failed" else want)
                for a, want in cfg["expect"].items())
            res["arms_without_a_reading"] = [a for a in cfg["expect"] if a not in res["readings"]]
            res["reporter_and_evidence_agree"] = all(
                res["per_arm"].get(a) == res["reporter_outcomes"].get(a) for a in cfg["expect"])
            results[shape] = res
            print(f"\n{shape}: rc={res['rc']} run={run_id} as_expected={res['meets_expectation']} "
                  f"agree={res['reporter_and_evidence_agree']}")
            for a in ARMS:
                rd = res["readings"].get(a) or {}
                own = rd.get("status_in_slot")
                found = rd.get("needles_found")
                print(f"   {a} want={cfg['expect'].get(a, '-'):7s} got={str(res['per_arm'].get(a)):7s} "
                      f"own_status={str(own):5s} needles={json.dumps(found, ensure_ascii=False)[:24] if found is not None else '-'} "
                      f"asked={rd.get('status_asked', '-')} err={str(rd.get('error_head'))[:46]}")
            if shape == "fixed" and not res["meets_expectation"]:
                raise SystemExit("the candidate itself is not green ("
                                 + json.dumps({a: res["per_arm"].get(a) for a in ARMS
                                               if res["per_arm"].get(a) != "passed"}, ensure_ascii=False)
                                 + "); the matrix would only measure a broken fix")
        finally:
            if pristine is not None:
                for p, b in pristine.items():
                    p.write_bytes(b)
            ok = sha(BOUNDARY) == hashlib.sha256(show(tip, BOUNDARY_PATH)).hexdigest()
            ok3 = sha(SHEET) == hashlib.sha256(show(tip, SHEET_PATH)).hexdigest()
            ok2 = sha(WORKBENCH) == hashlib.sha256(show(tip, WORKBENCH_PATH)).hexdigest()
            dirty = subprocess.run(["git", "-C", str(LANE), "status", "--porcelain", "frontend/src"],
                                   capture_output=True, text=True).stdout.strip()
            print(f"   restored boundary={ok} workbench={ok2} sheet={ok3} src dirty={dirty[:60]!r}")
            if not (ok and ok2 and ok3):
                raise SystemExit("the source did not come back byte-exact against the committed candidate; stopping")

    # merge any shapes this pass did not re-run (same candidate only), then judge the whole set
    merge_from = os.environ.get("CNX_0323_MERGE")
    passes, prior_reads = {}, {}
    if merge_from and (WORK / merge_from).exists():
        prior = json.loads((WORK / merge_from).read_text(encoding="utf-8"))
        if prior["measurement_scope"]["generation"]["candidate"] != tip:
            raise SystemExit("refusing to merge matrices measured on different candidates")
        passes = {s: r for s, r in prior["shapes"].items() if s not in results}
        prior_reads = {s: r for s, r in prior["per_arm_readings"].items() if s not in results}
    for s, r in passes.items():
        results.setdefault(s, r)
    green_fixed = all(results["fixed"]["per_arm"].get(a) == "passed" for a in ARMS)
    verdict = ("TEETH_AND_BASELINE"
               if green_fixed
               and all(r["meets_expectation"] for r in results.values())
               and all(r["arms_without_a_reading"] == [] for r in results.values())
               and all(r["reporter_and_evidence_agree"] for r in results.values())
               else "MATRIX_NOT_AS_EXPECTED")
    shapes_out = dict(passes)
    shapes_out.update(results)
    reads_out = dict(prior_reads)
    reads_out.update({s: r for s, r in
                      {k: v for k, v in {s: {a: row for a, row in (r["readings"] or {}).items()}
                                         for s, r in results.items()}.items()}.items()})
    ordered = {s: shapes_out[s] for s in ORDER if s in shapes_out}
    receipt = {
        "schema": "CNX_ORD0323_ARMS_R2",
        "order": "ORD-0323", "lane": "B c01d72a3",
        "revision_of": "ord0323_run_arms.py = 4b96bc3c8408b1159e31a2bbcb6579e04a7717c0 (bytes untouched; "
                       "that matrix measured the two-cell candidate and its workbench anchors no longer exist)",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "measurement_scope": {
            "generation": {"baseline_named_in_the_order": BASE, "candidate": tip,
                           "candidate_parent": PARENT, "commits_between": span,
                           "live_tip_provenance": "refs/heads/mirror/integration-frontend-apple-pass1 read with git ls-remote before the re-cut",
                           "branch": BRANCH_NAME},
            "tree": str(LANE), "spec": SPEC,
            "ports": {s: {"frontend": BASE_PORT + i, "backend": BASE_PORT + i + 38000} for i, s in enumerate(ORDER)},
            "database_per_run": "one sqlite file per run id, named by CITYNEXUS_DATABASE_URL",
            "mode": "CITYNEXUS_E2E_AUTHORITATIVE=1, AI disabled, both servers started by each invocation",
        },
        "files": {
            "PlanWithAiSheet.tsx": {"candidate_sha256": sha(SHEET),
                                    "baseline_sha256": hashlib.sha256(BASELINE_SHEET).hexdigest()},
            "ProductErrorBoundary.tsx": {"candidate_sha256": sha(BOUNDARY),
                                         "baseline_sha256": hashlib.sha256(BASELINE_BOUNDARY).hexdigest()},
            "JourneyInboxWorkbench.tsx": {"candidate_sha256": sha(WORKBENCH),
                                          "baseline_sha256": hashlib.sha256(BASELINE_WORKBENCH).hexdigest()},
        },
        "shapes": {s: {k: v for k, v in r.items() if k != "readings"} for s, r in ordered.items()},
        "assembled_from_passes": {"earlier_pass": merge_from or "(none)",
                                  "this_pass_shapes": list(results),
                                  "same_candidate": tip,
                                  "why": "two shapes were re-run after the Q68 stub was fixed; the matrix is one "
                                         "generation because every shape in it was measured against this commit"},
        "per_arm_readings": {s: {a: dict(r["readings"].get(a) or {}) for a in ARMS}
                             for s, r in results.items()},
        "verdict": verdict,
        "interpretation_limit": "each shape's own evidence files are the readings; this file only aggregates "
                                "them. derived_result stays null: signing a level belongs to the red team (B-1).",
        "claimed_result": None,
        "derived_result": None,
    }
    txt = json.dumps(receipt, ensure_ascii=False, indent=1)
    (WORK / "ord0323_arms_matrix_r2.json").write_text(txt, "utf-8", newline="\n")
    print("\nverdict:", verdict, "->", WORK / "ord0323_arms_matrix_r2.json")
    print("matrix bytes:", len(txt.encode("utf-8")))
    return 0 if verdict == "TEETH_AND_BASELINE" else 5


if __name__ == "__main__":
    sys.exit(main())
