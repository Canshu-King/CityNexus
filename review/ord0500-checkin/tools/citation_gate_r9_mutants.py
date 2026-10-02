"""ORD-0500 r9: prove the citation gate reddens, one mutant per red class, on a scratch tree.

The gate is only worth shipping if each refusal actually fires -- a gate that cannot go red is prose.
Every mutant edits a COPY under `scratch_cit_r9/`, judged against the real tracked path list so the
scratch tree is not its own authority; the originals in `wt22` are never written, and the run ends by
restoring the copies and re-checking that their bytes came back.

M1  cited line beyond the file      -- the ordinary generation drift.
M2  cited line is blank             -- a number that shows a reader nothing (this is the shape 13
                                     other lanes' citations were found in during the r8 audit).
M3  cited file absent               -- the path named does not resolve (r8 audit found 2 of these).
C1  unmutated copy of the same tree -- control; if this is not GREEN the scratch replica is wrong and
                                     none of the three mutants above would mean anything.
"""
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import citation_gate_r9 as G

LANE = G.LANE
WT = G.WT
SCR = os.path.join(LANE, "scratch_cit_r9")
NL = chr(10)


def tracked_live():
    return [t for t in subprocess.run(["git", "-C", WT, "ls-files"], stdout=subprocess.PIPE,
                                      timeout=300).stdout.decode("utf-8", "replace").splitlines()
            if t.strip() and not t.startswith("review/")]


def cited_targets(live):
    """Every path the owned files cite, so the scratch tree carries what the gate will want to open."""
    want = set()
    for f in G.OWNED:
        p = os.path.join(WT, f)
        if not os.path.exists(p):
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        for m in G.PATH_CIT.finditer(text):
            r, _ = G.resolve(m.group(1), live)
            if r:
                want.add(r)
    return sorted(want)


def build_scratch(live):
    if os.path.isdir(SCR):
        shutil.rmtree(SCR)
    files = list(G.OWNED) + cited_targets(live)
    for rel in files:
        src = os.path.join(WT, rel)
        if not os.path.exists(src):
            continue
        dst = os.path.join(SCR, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    return files


def sha(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def patch(rel, old, new):
    p = os.path.join(SCR, rel)
    s = open(p, encoding="utf-8").read()
    if old not in s:
        raise SystemExit("ABORT_MUTANT_ANCHOR %s -- %r is not in the copy, so this mutant would not "
                         "have moved anything" % (rel, old[:40]))
    open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))


def main():
    live = tracked_live()
    copied = build_scratch(live)
    TEST = "backend/tests/test_qoder_ord0500_journey_refusal.py"
    MAIN = "backend/app/main.py"
    main_lines = len(open(os.path.join(SCR, MAIN), encoding="utf-8").read().splitlines())
    blank = next(i + 1 for i, l in enumerate(
        open(os.path.join(SCR, MAIN), encoding="utf-8").read().splitlines())
        if i > 50 and not l.strip())

    runs = []
    control = G.run_gate(root=SCR, live=live)
    runs.append({"id": "C1_control_copy", "verdict": control["verdict"],
                 "citations": control["citations_checked"], "red": control["red_total"],
                 "expect": "GREEN",
                 "bite": control["verdict"] == "GREEN"})

    cases = [
        ("M1_beyond_file", "backend/app/main.py:818", "backend/app/main.py:%d" % (main_lines + 1),
         "CITED_LINE_BEYOND_FILE"),
        ("M2_blank_line", "backend/app/main.py:818", "backend/app/main.py:%d" % blank,
         "CITED_LINE_IS_BLANK"),
        ("M3_absent_file", "backend/app/main.py:818", "backend/app/nowhere_gate_r9.py:818",
         "CITED_FILE_ABSENT"),
        # M4 is the defect this order was actually re-cut for three times: a number that is in range,
        # not blank, and simply no longer the line the sentence claims.  The r8-era comment cited 810
        # for the `require()` helper; on this tip line 810 is something else entirely.
        ("M4_wrong_but_in_range", "backend/app/main.py:818", "backend/app/main.py:810",
         "CITED_LINE_CONTENT_MISMATCH"),
    ]
    for mid, old, new, expect in cases:
        patch(TEST, old, new)
        res = G.run_gate(root=SCR, live=live)
        hit = [r for r in res["red_detail"] if r["verdict"] == expect]
        runs.append({"id": mid, "verdict": res["verdict"], "expect_red_class": expect,
                     "red_total": res["red_total"], "class_fired": bool(hit),
                     "co_firing_classes": sorted({r["verdict"] for r in res["red_detail"]}),
                     "fired_detail": hit[:1],
                     "citation_written": "`%s`" % new,
                     "bite": res["verdict"] == "RED" and bool(hit)})
        patch(TEST, new, old)   # revert before the next mutant, one variable at a time

    after = G.run_gate(root=SCR, live=live)
    runs.append({"id": "C2_after_revert", "verdict": after["verdict"], "red": after["red_total"],
                 "expect": "GREEN", "bite": after["verdict"] == "GREEN"})

    restored = {}
    for rel in copied:
        a, b = sha(os.path.join(WT, rel)), sha(os.path.join(SCR, rel))
        restored[rel] = {"wt": a, "scratch": b, "equal": a == b}
    untouched_wt = subprocess.run(["git", "-C", WT, "status", "--porcelain"],
                                  stdout=subprocess.PIPE, timeout=120).stdout.decode(
                                      "utf-8", "replace").strip()

    out = {"tool": "citation_gate_r9_mutants", "took_local": G.datetime.now().astimezone(
    ).isoformat(timespec="seconds"), "scratch": SCR, "files_copied": len(copied),
        "main_lines_in_scratch": main_lines, "blank_line_used": blank,
        "control_verdict": control["verdict"], "after_revert_verdict": after["verdict"],
        "runs": runs, "every_mutant_bit": all(r["bite"] for r in runs),
        "wt22_worktree_clean": untouched_wt == "", "wt22_dirty_lines": untouched_wt.splitlines(),
        "bytes_restored": restored,
        "all_bytes_restored": all(v["equal"] for v in restored.values())}
    dest = os.path.join(LANE, "evidence", "citation_gate_r9_mutants.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps({k: v for k, v in out.items() if k not in ("runs", "bytes_restored")},
                     ensure_ascii=False, indent=2))
    for r in runs:
        print("  %-18s verdict=%-6s bite=%s" % (r["id"], r["verdict"], r["bite"]))
    print("WROTE " + dest)
    return 0 if out["every_mutant_bit"] else 3


if __name__ == "__main__":
    sys.exit(main())
