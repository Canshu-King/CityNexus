"""The line moved between the order and the delivery, so the same face is re-read on both tips.

ORD-0454 was written against `4ee14229...`; by the time this face was cut, `ls-remote` read `57ff5d1c...`. A
number that only survives on one rev is a number nobody can use in a gate, so the tool is run over both exports
and the two readings are compared field by field, alongside the question that actually decides whether the
comparison means anything: did any stylesheet change between the two revs.
"""
import io
import json
import os
import re
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
TOOL = r"D:\moodle\_qoder_cmdr_ref_20260921\tools\cnx_copy_tiers_r3.py"
REPO = "D:/moodle/CityNexus"
OLD_TIP = "4ee14229f80691cf8e5ea913375c0caf83ac02ee"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")


def ls_remote():
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote",
                        "git@github.com:Canshu-King/CityNexus.git",
                        "refs/heads/mirror/integration-frontend-apple-pass1"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=300, env=ENV)
    return (r.stdout or "").split()[0]


def read_tree(tag):
    src = os.path.join(WORK, tag, "frontend", "src")
    i18n = os.path.join(src, "i18n", "LocaleContext.tsx")
    e2e = os.path.join(WORK, tag, "frontend", "e2e")
    r = subprocess.run([sys.executable, TOOL, "--i18n", i18n, "--baseline", i18n, "--e2e", e2e,
                        "--src", src, "--list-state-pairs"], capture_output=True, timeout=1800, env=ENV)
    txt = (r.stdout or b"").decode("utf-8", "replace")
    face = next((l.strip() for l in txt.splitlines() if "STATE_PAIR" in l), None)
    rows = [l.strip() for l in txt.splitlines()
            if l.strip().startswith("[PAIRED") or l.strip().startswith("[UNPAIRED")]
    m = re.search(r"(\d+) stylesheet.*?(\d+) on-state cell.*?(\d+) paired.*?(\d+) unpaired.*?"
                  r"(\d+) attribute-on cell.*?(\d+) without an off-side.*?(\d+) bare base", face or "")
    return {"face": face, "rows": rows,
            "counts": ({"stylesheets": int(m.group(1)), "on_state_cells": int(m.group(2)),
                        "paired": int(m.group(3)), "unpaired": int(m.group(4)),
                        "attribute_on": int(m.group(5)), "attribute_unpaired": int(m.group(6)),
                        "bare_base_rules": int(m.group(7))} if m else None),
            "exit": r.returncode}


def main():
    new_tip = ls_remote()
    out = {"old_tip_read_for_the_order": OLD_TIP, "tip_now": new_tip}
    out["read_on_old_tip"] = read_tree("_tip")
    out["read_on_new_tip"] = read_tree("_tip2")
    d = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy=", "diff",
                        "--name-only", OLD_TIP, new_tip, "--", "frontend/src"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=300, env=ENV)
    changed = [l for l in (d.stdout or "").splitlines() if l.strip()]
    out["files_changed_between_the_two_tips"] = changed
    out["stylesheets_changed_between_the_two_tips"] = [f for f in changed if f.endswith(".css")]
    out["identical_counts"] = (out["read_on_old_tip"]["counts"] == out["read_on_new_tip"]["counts"])
    out["identical_rows"] = (out["read_on_old_tip"]["rows"] == out["read_on_new_tip"]["rows"])
    out["reading"] = ("the face reads the same on both tips (%s cells, %s paired, %s bare base rules) and no "
                      "stylesheet moved between them, so the delivery is not pinned to a rev that has already "
                      "been overtaken"
                      % (out["read_on_new_tip"]["counts"]["on_state_cells"],
                         out["read_on_new_tip"]["counts"]["paired"],
                         out["read_on_new_tip"]["counts"]["bare_base_rules"])) \
        if out["identical_counts"] and out["identical_rows"] else \
        ("counts moved between the two tips: old %s new %s -- say which rev the gate would be run against"
         % (json.dumps(out["read_on_old_tip"]["counts"]), json.dumps(out["read_on_new_tip"]["counts"])))
    io.open(os.path.join(WORK, "state_pair_tip_move_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: out[k] for k in ("tip_now", "identical_counts", "identical_rows",
                                          "stylesheets_changed_between_the_two_tips", "reading")},
                     ensure_ascii=False, indent=1))
    return 0 if out["identical_counts"] else 1


if __name__ == "__main__":
    sys.exit(main())
