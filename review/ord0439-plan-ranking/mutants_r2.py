"""ORD-0439 mutant pass r2: does each of P1..P4 actually bite?

Same discipline as the ORD-0386 pass: every mutation lands on the *export* copy of the product source
(never the worktree), the bundle is rebuilt, only the aimed arm runs, and the file is restored from the
worktree and byte-compared.  A mutant that leaves its arm green means the arm was judging a stub rather
than the product, so this table is part of the evidence, not a bonus.

r2 exists because the spec header was rewritten after the first single-mutant try; every number here
therefore corresponds to the bytes that were committed.
"""
import json
import os
import shutil
import subprocess
import sys
import time

WK = r"D:/moodle/_qoder_q_ord0369_wk"
TREE = r"D:/moodle/_qoder_q_ord0439"
EXPORT = os.path.join(WK, "build", "frontend")
DIST = os.path.join(WK, "dist_cand")
NODE = "node"
BACKEND_PORT = 8713
FRONT_PORT = 4192

RANK = "src/features/planning/planRanking.ts"
PANEL = "src/features/planning/PlanRankingPanel.tsx"
COPY = "src/features/planning/planRankingCopy.ts"

MUTANTS = [
    {
        "id": "N1-ranked-by-names-uncomparable-dims",
        "file": PANEL,
        "from": 'say("rank.rankedBy", { dims: usedDims.map((d) => say(DIM_KEYS[d]))',
        "to": 'say("rank.rankedBy", { dims: RANK_DIMS.map((d) => say(DIM_KEYS[d]))',
        "arm": "P1",
        "why": "the sentence claims the ranking used every dimension, including the ones that never differ",
    },
    {
        "id": "N2-walk-absent-rendered-as-zero",
        "file": RANK,
        "from": 'if (measured.length === 0) return { kind: "absent", reason: "walkNotMeasured" };',
        "to": 'if (measured.length === 0) return { kind: "value", number: 0 };',
        "arm": "P2",
        "why": "a field the payload does not carry becomes 0, i.e. the cheapest walk in the comparison",
    },
    {
        "id": "N3-synthetic-called-provider-result",
        "file": COPY,
        "from": "其余是 {quality}。",
        "to": "其余是供应商给的结果（{quality}）。",
        "arm": "P3",
        "why": "a SYNTHETIC_DEFAULT leg is presented as something a provider answered",
    },
    {
        "id": "N4-empty-state-ranks-nothing-but-still-speaks",
        "file": PANEL,
        "from": "  if (rows.length === 0) {",
        "to": "  if (rows.length < 0) {",
        "arm": "P4",
        "why": "with no candidate the guard is skipped, so the panel keeps its ranking furniture",
    },
]


def env():
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        e.pop(k, None)
    e["NO_PROXY"] = "*"
    e["PYTHONIOENCODING"] = "utf-8"
    e["CITYNEXUS_BACKEND_PORT"] = str(BACKEND_PORT)
    e["CITYNEXUS_ORD0386_PORT"] = str(FRONT_PORT)
    return e


def build():
    return subprocess.run(
        [NODE, os.path.join(EXPORT, "node_modules/vite/bin/vite.js"), "build",
         "--outDir", DIST, "--emptyOutDir"],
        cwd=EXPORT, env=env(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    ).returncode


def run_arm(arm, report):
    e = env()
    e["CITYNEXUS_ORD0386_MATCH"] = "qoder-ord0439"
    e["CITYNEXUS_ORD0386_REPORT"] = report
    rc = subprocess.run(
        [NODE, os.path.join(EXPORT, "node_modules/@playwright/test/cli.js"), "test",
         "--config", "playwright.ord0386-Q.config.ts", "--workers=1", "-g", arm],
        cwd=EXPORT, env=e, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    ).returncode
    d = json.load(open(report, encoding="utf-8"))
    stats = d.get("stats", {})
    msgs = []
    for suite in d.get("suites", []):
        for spec in suite.get("specs", []):
            for t in spec.get("tests", []):
                for r in t.get("results", []):
                    if r.get("status") != "expected":
                        msgs.append(str((r.get("error") or {}).get("message", "")).splitlines()[0])
    return {
        "rc": rc,
        "expected": stats.get("expected"),
        "unexpected": stats.get("unexpected"),
        "first_error": (msgs[0][:260] if msgs else ""),
    }


def main():
    rows = []
    for m in MUTANTS:
        tgt = os.path.join(EXPORT, m["file"])
        src = os.path.join(TREE, "frontend", m["file"])
        before = open(tgt, encoding="utf-8", newline="").read()
        if before.count(m["from"]) != 1:
            rows.append({"id": m["id"], "status": "SKIPPED-NOT-ANCHORED",
                         "occurrences": before.count(m["from"]), "arm": m["arm"]})
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
            continue
        if open(src, encoding="utf-8", newline="").read() != before:
            rows.append({"id": m["id"], "status": "SKIPPED-EXPORT-DIFFERS-FROM-TREE", "arm": m["arm"]})
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
            continue
        shutil.copy2(tgt, tgt + ".orig")
        open(tgt, "w", encoding="utf-8", newline="").write(before.replace(m["from"], m["to"], 1))
        brc = build()
        report = os.path.join(WK, f"mutant-0439-{m['id']}-{int(time.time())}.json")
        res = (run_arm(m["arm"], report) if brc == 0
               else {"rc": -1, "unexpected": None, "expected": None, "first_error": "build failed"})
        shutil.copy2(tgt + ".orig", tgt)
        os.remove(tgt + ".orig")
        restored = open(tgt, encoding="utf-8", newline="").read() == before
        killed = (res["rc"] != 0) and (res["unexpected"] or 0) >= 1
        rows.append({
            "id": m["id"], "arm": m["arm"], "build_rc": brc, "playwright_rc": res["rc"],
            "expected": res["expected"], "unexpected": res["unexpected"],
            "killed": killed, "restored_byte_identical": restored,
            "report": os.path.basename(report), "first_error": res["first_error"], "why": m["why"],
        })
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)

    brc = build()
    print("final clean rebuild rc=", brc, flush=True)
    out = os.path.join(WK, "mutants_0439_r2.json")
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", out, flush=True)
    bad = [r for r in rows if not r.get("killed")]
    print("not killed:", [r.get("id") or r.get("status") for r in bad], flush=True)
    sys.exit(0 if not bad and brc == 0 else 1)


main()
