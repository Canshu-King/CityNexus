"""The two counters this face needs before anyone trusts a green: a real gap must be RED, and a near-miss must not be.

K9o/K9p in the tool use invented stylesheets. Numbers about OUR tree need the same two directions on OUR bytes,
so this takes the tip export twice: once with `.family-chip`'s bare base rule deleted (a real defect: the
selected look survives, the unselected look falls back to whatever the browser defaults to), and once with the
tip as it is. Absolute mode and growth mode are both run, and the difference between the two trees is what the
door would see.

Growth mode's claim is checked in the direction that matters: a gap the tip already carries must NOT be blamed
on the candidate, and a gap the candidate introduces must be.
"""
import io
import json
import os
import re
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
TOOL = r"D:\moodle\_qoder_cmdr_ref_20260921\tools\cnx_copy_tiers_r3.py"
TIP_SRC = os.path.join(WORK, "_tip", "frontend", "src")
CAND_SRC = os.path.join(WORK, "_cand", "frontend", "src")
I18N = os.path.join(TIP_SRC, "i18n", "LocaleContext.tsx")
E2E = os.path.join(WORK, "_tip", "frontend", "e2e")
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")
BASE_RULE = re.compile(r"^\.family-chip \{")


def run(src, state_base=None, listing=False):
    cmd = [sys.executable, TOOL, "--i18n", I18N, "--baseline", I18N, "--e2e", E2E, "--src", src]
    if state_base:
        cmd += ["--state-base", state_base]
    if listing:
        cmd += ["--list-state-pairs"]
    r = subprocess.run(cmd, capture_output=True, timeout=1800, env=ENV)
    txt = (r.stdout or b"").decode("utf-8", "replace")
    line = [l for l in txt.splitlines() if "STATE_PAIR" in l]
    cells = [l for l in txt.splitlines() if "UNPAIRED" in l and ("state ." in l or '="' in l)]
    return {"exit": r.returncode, "finding": line[0].strip() if line else None,
            "unpaired_rows": cells, "tail": txt.strip().splitlines()[-1] if txt.strip() else None}


def build_candidate():
    import shutil
    root = os.path.join(WORK, "_cand")
    if os.path.isdir(root):
        shutil.rmtree(root)
    shutil.copytree(os.path.join(WORK, "_tip"), root)
    p = os.path.join(CAND_SRC, "styles.css")
    lines = io.open(p, encoding="utf-8").read().split("\n")
    hit = [i for i, l in enumerate(lines) if BASE_RULE.match(l)]
    assert len(hit) == 1, hit
    lines[hit[0]] = "/* ORD-0454 counter-example: this bare base rule was the unselected twin */"
    io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    return {"deleted_line": hit[0] + 1, "file": "styles.css",
            "removed_rule_starts": ".family-chip {",
            "selected_rule_still_present": any(".family-chip.selected" in l for l in lines)}


def main():
    out = {"tool_blob_note": "the tool is read from its working-tree path; its blob is published separately",
           "candidate_edit": build_candidate()}
    out["tip_absolute"] = run(TIP_SRC)
    out["cand_absolute"] = run(CAND_SRC)
    out["cand_growth_vs_tip"] = run(CAND_SRC, TIP_SRC)
    out["tip_growth_vs_itself"] = run(TIP_SRC, TIP_SRC)
    lst = run(CAND_SRC, listing=True)
    out["cand_listing_unpaired_rows"] = lst["unpaired_rows"]
    k = lambda d: (d["finding"] or "").split("]")[0].replace("[", "").strip()
    out["verdicts"] = {"tip_absolute": k(out["tip_absolute"]), "cand_absolute": k(out["cand_absolute"]),
                       "cand_growth_vs_tip": k(out["cand_growth_vs_tip"]),
                       "tip_growth_vs_itself": k(out["tip_growth_vs_itself"])}
    out["reading"] = {
        "a_real_gap_turns_the_face_red": out["verdicts"]["cand_absolute"] == "VIOLATION",
        "growth_mode_blames_the_candidate_for_it": out["verdicts"]["cand_growth_vs_tip"] == "VIOLATION",
        "the_tip_itself_adds_nothing_under_growth": "adds 0 new" in (out["tip_growth_vs_itself"]["finding"] or ""),
        "the_row_names_the_file_and_line": bool(out["cand_listing_unpaired_rows"])}
    io.open(os.path.join(WORK, "state_pair_probe_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"candidate_edit": out["candidate_edit"], "verdicts": out["verdicts"],
                      "reading": out["reading"],
                      "cand_row": out["cand_listing_unpaired_rows"][:3],
                      "tip_finding": out["tip_absolute"]["finding"]}, ensure_ascii=False, indent=1))
    return 0 if all(out["reading"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
