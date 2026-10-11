# -*- coding: utf-8 -*-
"""Mount the ORD-0568 codes-on-screen arm into the landing door (lane 加闸工).

The door (`live_checks/preflight_and_land_r7.py`) is the file the landing loop runs every ten minutes,
so this mounter never touches it in place: it copies the door, applies two insertions with hard
anchor assertions, byte-compiles the result and writes the patched copy next to it.  Applying it to
the live door is the commander's call -- one copy-in move away, and `--apply` does it with a timestamped
backup of the original.

Two axes of the arm itself are recorded in the receipt, not just a verdict word:

  run["codes_on_screen"] = {mode, files_judged, problems:[{file,line,entry_line,token,named_by,position,text}]}
  problems.append("codes on screen: <file:line token ...>") -- only when mode == refuse
"""

import argparse
import io
import os
import py_compile
import re
import shutil
import subprocess
import sys
import time

DOOR = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\preflight_and_land_r7.py"
MODULE = "codes_on_screen_gate_r3.py"

ARG_ANCHOR = '    ap.add_argument("--land", action="store_true", help="actually move the authoritative line (default: dry run)")'

ARG_BLOCK = '''    ap.add_argument("--codes-on-screen", default="report", choices=["report", "refuse", "off"],
                    help="ORD-0568 arm: internal code names in a position the traveller reads. "
                    "report = measure and record, refuse = also block the landing, off = do not run it.")
'''

ARM_ANCHOR = '    verdict = "READY_TO_LAND" if not problems else "REFUSED"'

ARM_BLOCK = '''    # ORD-0568 arm (加闸工): internal code names that reach the traveller's eyes.  The arm judges only
    # positions whose string becomes a spoken word, and only tokens something actually names with
    # (quoted in backend/ or contracts/, or used in a non-rendered slot of the same file).  Default
    # mode measures and records; "refuse" is what turns a finding into a blocked landing.  The reason
    # goes into problems verbatim so the outbox receipt carries it instead of one bare verdict word.
    if a.codes_on_screen != "off":
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import codes_on_screen_gate_r3 as codes_gate
            codes_gate.REPO = REPO
            cand_src = [p for p in cand_files if p.startswith("frontend/src/") and (p.endswith(".ts") or p.endswith(".tsx"))]
            added_map = codes_gate.added_lines(base, cand)
            codes_findings = []
            for path in cand_src:
                body = codes_gate.git_show(cand, path)
                if body is None:
                    continue
                codes_findings.extend(codes_gate.judge(path, body,
                                                      codes_gate.machine_names(cand),
                                                      added_map.get(path)))
            codes_problems = [f for f in codes_findings if f["class"] == "refuse"]
            run["codes_on_screen"] = {
                "mode": a.codes_on_screen,
                "files_judged": len(cand_src),
                "refusal_count": len(codes_problems),
                "informational_count": len(codes_findings) - len(codes_problems),
                "problems": codes_problems,
            }
            if codes_problems and a.codes_on_screen == "refuse":
                problems.append("codes on screen (ORD-0568 arm): %s" % "; ".join(
                    "%s:%s token=%s named_by=%s" % (f["file"], f["line"], f["token"], f["named_by"])
                    for f in codes_problems[:6]))
        except Exception as exc:  # never let the new arm take the whole door down with it
            run["codes_on_screen"] = {"mode": a.codes_on_screen, "arm_error": repr(exc)[:300]}
            if a.codes_on_screen == "refuse":
                problems.append("codes on screen arm did not run: %s" % repr(exc)[:200])

'''


def build(out_path, apply_live=False):
    src = io.open(DOOR, encoding="utf-8", newline="").read()
    for anchor, label in ((ARG_ANCHOR, "arg"), (ARM_ANCHOR, "arm")):
        hits = src.count(anchor)
        if hits != 1:
            print("ABORT anchor %s matched %d times - the door moved, re-read it before mounting" % (label, hits))
            return 2
    patched = src.replace(ARG_ANCHOR, ARG_BLOCK.rstrip("\n") + "\n" + ARG_ANCHOR, 1)
    patched = patched.replace(ARM_ANCHOR, ARM_BLOCK + ARM_ANCHOR, 1)
    io.open(out_path, "w", encoding="utf-8", newline="").write(patched)
    py_compile.compile(out_path, doraise=True)
    print("mounted copy written: %s (%d B, +%d B over the door) -- py_compile OK" % (
        out_path, os.path.getsize(out_path), len(patched) - len(src)))
    diff_lines = [l for l in re.findall(r"^\+.*$", patched, re.M)]
    print("added lines: %d" % len(diff_lines))
    if apply_live:
        stamp = time.strftime("%H%M%S")
        backup = DOOR + ".before_codes_arm_r1." + stamp
        shutil.copy2(DOOR, backup)
        io.open(DOOR, "w", encoding="utf-8", newline="").write(patched)
        py_compile.compile(DOOR, doraise=True)
        print("APPLIED to the live door; original backed up at %s" % backup)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"D:\moodle\_qoder_jiazagong_0568\preflight_and_land_r7_with_codes_arm_r1.py")
    ap.add_argument("--apply", action="store_true", help="write the mounted door into the live path (needs the commander's word)")
    opts = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(build(opts.out, opts.apply))
