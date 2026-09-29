"""Collect the ORD-0454 arm results and the tip listing into citable artifacts.

The tool prints its self-test to stdout; a ledger block cannot cite stdout, so every K9 arm's label, its
measured population and its verdict are parsed here into json, together with the tip's per-cell listing (the
seven on-state cells and the twin that answers for each). Both directions are required: a real gap must be red,
and the four legitimate twin spellings plus the out-of-scope shapes must stay quiet.
"""
import io
import json
import os
import re
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
TOOL = r"D:\moodle\_qoder_cmdr_ref_20260921\tools\cnx_copy_tiers_r3.py"
R2 = r"D:\moodle\_qoder_cmdr_ref_20260921\tools\cnx_copy_tiers_r2.py"
TIP = os.path.join(WORK, "_tip")
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")
ARM = re.compile(r"\[(MET|VIOLATION)\] (K9\w+)\s+(.*)$")
FACE = re.compile(r"\[(MET|VIOLATION|NOT_RUN)\s*\] (STATE_PAIR\w*)\s+(.*)$")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, timeout=1800, env=ENV)
    return (r.stdout or b"").decode("utf-8", "replace"), r.returncode


def main():
    i18n = os.path.join(TIP, "frontend", "src", "i18n", "LocaleContext.tsx")
    e2e = os.path.join(TIP, "frontend", "e2e")
    src = os.path.join(TIP, "frontend", "src")
    out = {"tool": TOOL, "arms": [], "faces": {}, "regression_check": {}}
    txt, rc = run([sys.executable, TOOL, "--i18n", i18n, "--baseline", i18n, "--e2e", e2e,
                   "--src", src, "--mutant"])
    for line in txt.splitlines():
        m = ARM.search(line.strip())
        if m:
            out["arms"].append({"arm": m.group(2), "verdict": m.group(1), "measured": m.group(3).strip()})
    for line in txt.splitlines():
        m = FACE.search(line.strip())
        if m:
            out["faces"][m.group(2)] = {"verdict": m.group(1), "measure": m.group(3).strip()}
    out["mutant_exit"] = rc
    out["arms_expected_red"] = sorted(a["arm"] for a in out["arms"]
                                      if "is_caught" in a["arm"] or "not_an_unselected_twin" in a["arm"])
    out["arms_all_met"] = all(a["verdict"] == "MET" for a in out["arms"])

    txt2, rc2 = run([sys.executable, TOOL, "--i18n", i18n, "--baseline", i18n, "--e2e", e2e,
                     "--src", src, "--list-state-pairs"])
    rows = [l.strip() for l in txt2.splitlines() if l.strip().startswith("[PAIRED")
            or l.strip().startswith("[UNPAIRED")]
    out["tip_cells_listing"] = rows
    out["tip_state_pair_face"] = next(({"verdict": m.group(1), "measure": m.group(3).strip()}
                                       for line in txt2.splitlines()
                                       for m in [FACE.search(line.strip())] if m), None)
    out["tip_exit"] = rc2

    # regression: the new tool must keep every face r2 had, with the same verdicts, and add only STATE_PAIR
    txt3, rc3 = run([sys.executable, R2, "--i18n", i18n, "--baseline", i18n, "--e2e", e2e, "--src", src])
    def faces(t):
        d = {}
        for line in t.splitlines():
            m = re.match(r"\[\s*([A-Z_]+)\s*\] ([A-Z_④⑥]+)\s", line.strip())
            if m:
                d[m.group(2)] = m.group(1)
        return d
    f2, f3 = faces(txt3), faces(txt2)
    out["regression_check"] = {"r2_faces": f2, "r3_faces": f3,
                               "faces_only_in_r3": sorted(set(f3) - set(f2)),
                               "verdict_changed": {k: (f2[k], f3[k]) for k in f2 if k in f3
                                                   and f2[k] != f3[k]}}
    io.open(os.path.join(WORK, "state_pair_arms_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"arms_total": len(out["arms"]), "arms_all_met": out["arms_all_met"],
                      "arms": [(a["arm"], a["verdict"]) for a in out["arms"]],
                      "tip_state_pair_face": out["tip_state_pair_face"],
                      "cells_listed": len(out["tip_cells_listing"]),
                      "regression_check": out["regression_check"]}, ensure_ascii=False, indent=1)[:2400])
    return 0 if out["arms_all_met"] and not out["regression_check"]["verdict_changed"] else 1


if __name__ == "__main__":
    sys.exit(main())
