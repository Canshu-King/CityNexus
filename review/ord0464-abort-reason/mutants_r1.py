"""ORD-0464 mutant pass: does each arm actually bite?

Same discipline as the ORD-0386 / ORD-0439 passes: every mutation lands on the *export* copy of the
product source, the bundle is rebuilt, only the aimed arm runs, and the file is restored from the
worktree and byte-compared afterwards.  A mutant that leaves its arm green means the arm was judging a
stub rather than the product.
"""
import json
import os
import shutil
import subprocess
import sys
import time

WK = r"D:/moodle/_qoder_q_ord0369_wk"
TREE = r"D:/moodle/_qoder_q_ord0464"
EXPORT = os.path.join(WK, "build", "frontend")
DIST = os.path.join(WK, "dist_cand")
NODE = "node"
BACKEND_PORT = 8713
FRONT_PORT = 4192

DOOR = "src/features/abort/journeyAbort.ts"
PANEL = "src/features/abort/JourneyAbortPanel.tsx"
COPY = "src/features/abort/journeyAbortCopy.ts"

MUTANTS = [
    {
        "id": "P1-never-asked-collapsed-into-declined",
        "file": DOOR,
        "from": '      latest = { state: "NOT_ASKED" };',
        "to": '      latest = { state: "SKIPPED_BY_TRAVELER" };',
        "arm": "A8",
        "why": "the question never arrived is rendered as the traveller choosing not to answer -- the exact fabrication this order was cut to stop",
    },
    {
        "id": "P2-skip-rendered-as-a-declaration",
        "file": PANEL,
        "from": '        case "SKIPPED_BY_TRAVELER":\n          return say("abort.doneSkipped");',
        "to": '        case "SKIPPED_BY_TRAVELER":\n          return say("abort.doneDeclared", { codes: [] });',
        "arm": "A3",
        "why": "a declined survey is presented as a recorded reason set",
    },
    {
        "id": "P3-named-refusal-dropped",
        "file": DOOR,
        "from": "    if (Array.isArray(errors) && errors.length > 0) {",
        "to": "    if (false) {",
        "arm": "A6",
        "why": "the refusal this server names is read as no name, so the screen falls back to its generic sentence",
    },
    {
        "id": "P4-vocabulary-grows-a-nine",
        "file": COPY,
        "from": '  OTHER: "abort.code.other",\n} as const;',
        "to": '  OTHER: "abort.code.other",\n  SUPPLIER_WAS_RUDE: "abort.code.supplierWasRude",\n} as const;',
        "arm": "A1",
        "why": "the screen offers a reason the contract does not carry, and echoes its key as the label",
    },
    {
        "id": "P5-travellers-order-replaced-by-sort",
        "file": PANEL,
        "from": "      const codes = picked.filter((code) => code);",
        "to": "      const codes = picked.filter((code) => code).sort();",
        "arm": "A2",
        "why": "the server stores an alphabetical order this screen invented instead of the order the traveller ticked",
    },
    {
        "id": "P6-note-limit-is-a-decoration",
        "file": DOOR,
        "from": "export const ABORT_NOTE_MAX_LENGTH = 200;",
        "to": "export const ABORT_NOTE_MAX_LENGTH = 500;",
        "arm": "A4",
        "why": "the box promises a longer note than the door accepts, so the traveller learns the cap by being refused",
    },
]

MULTILINE = {m["id"] for m in MUTANTS if "\n" in m["from"]}


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
    e["CITYNEXUS_ORD0386_MATCH"] = "qoder-ord0464"
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
        "first_error": (msgs[0][:300] if msgs else ""),
    }


def main():
    rows = []
    for m in MUTANTS:
        tgt = os.path.join(EXPORT, m["file"])
        src = os.path.join(TREE, "frontend", m["file"])
        before = open(tgt, encoding="utf-8", newline="").read()
        tree = open(src, encoding="utf-8", newline="").read()
        pairs = [(m["from"], m["to"])]
        if m["id"] in MULTILINE:
            pairs = [
                (m["from"].replace("\n", "\r\n"), m["to"].replace("\n", "\r\n")),
                (m["from"], m["to"]),
            ]
        anchored = next(((f, t) for f, t in pairs if before.count(f) == 1), None)
        if anchored is None:
            rows.append({"id": m["id"], "arm": m["arm"], "status": "SKIPPED-NOT-ANCHORED",
                         "occurrences": [before.count(f) for f, _ in pairs]})
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
            continue
        if tree != before:
            rows.append({"id": m["id"], "arm": m["arm"], "status": "SKIPPED-EXPORT-DIFFERS-FROM-TREE"})
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
            continue
        frm, to = anchored
        shutil.copy2(tgt, tgt + ".orig")
        open(tgt, "w", encoding="utf-8", newline="").write(before.replace(frm, to, 1))
        brc = build()
        report = os.path.join(WK, f"mutant-0464-{m['id']}-{int(time.time())}.json")
        res = (run_arm(m["arm"], report) if brc == 0
               else {"rc": -1, "unexpected": None, "expected": None, "first_error": "build failed"})
        shutil.copy2(tgt + ".orig", tgt)
        os.remove(tgt + ".orig")
        restored = open(tgt, encoding="utf-8", newline="").read() == before
        killed = (res["rc"] != 0) and (res["unexpected"] or 0) >= 1
        rows.append({
            "id": m["id"], "arm": m["arm"], "file": m["file"], "build_rc": brc,
            "playwright_rc": res["rc"], "expected": res["expected"], "unexpected": res["unexpected"],
            "killed": killed, "restored_byte_identical": restored,
            "report": os.path.basename(report), "first_error": res["first_error"], "why": m["why"],
            "mutation_from": m["from"], "mutation_to": m["to"],
        })
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)

    brc = build()
    print("final clean rebuild rc=", brc, flush=True)
    out = os.path.join(WK, "mutants_0464_r1.json")
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", out, flush=True)
    bad = [r for r in rows if not r.get("killed")]
    print("not killed:", [r.get("id") or r.get("status") for r in bad], flush=True)
    sys.exit(0 if not bad and brc == 0 else 1)


main()
