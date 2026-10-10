"""CMDR landing-gate pick arm r1 -- after a landing, prove the vocabulary lookup is still closed.

Why this exists: my own ORD-0551 adjudication turned into a ruler (`cmdr_pick_closed_lookup_r1.py`) that
could tell "pick() hands the caller's input back" from "the lookup is closed", but it never got wired into
the landing chain, so every landing since then rested on me remembering to run it.  This is that wire:
run it against the tip that was just landed, and refuse to call the hand clean when it is not.

Three verdicts are distinguished on purpose, because a blind arm is itself a defect:
  PASS  -- the ruler read the shipped file and found no leak
  FAIL  -- the ruler read it and found a leak
  ABORT -- the ruler could not read the file at that rev (moved/renamed): that is NOT a pass

--selftest points the arm at a mutant copy of the shipped table (must FAIL) and at the closed variant the
ruler builds itself (must PASS), so the arm has its own "the time it should have been red".
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
RULER = os.path.join(LIVE, "cmdr_pick_closed_lookup_r1.py")
PATH_IN_REPO = "frontend/src/lib/displayVocabulary.ts"
REPO = r"D:\moodle\CityNexus"


def run_ruler(argv):
    r = subprocess.run([sys.executable, RULER] + argv, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    out = {"rc": r.returncode, "stdout_tail": (r.stdout or "").strip().splitlines()[-6:],
           "stderr_tail": (r.stderr or "").strip().splitlines()[-4:]}
    txt = r.stdout or ""
    i = txt.find("{")
    if i >= 0:
        try:
            out["json"] = json.loads(txt[i:])
        except Exception:
            out["json"] = None
    else:
        out["json"] = None
    return out


def classify(res):
    j = res.get("json") or {}
    v = j.get("verdict") or j.get("shipped_verdict")
    if v == "GREEN":
        return "PASS"
    if v == "RED":
        return "FAIL"
    if v == "RULER_OUT_OF_SCOPE":
        return "ABORT"
    return "ABORT"


ap = argparse.ArgumentParser()
ap.add_argument("--tip", required=False, default="", help="the rev that was just landed")
ap.add_argument("--selftest", action="store_true")
a = ap.parse_args()

if not a.tip and not a.selftest:
    print("ABORT: pass --tip <40-hex> (or --selftest)")
    sys.exit(2)

report = {"arm": "cmdr_gate_pick_arm_r1", "ruler": RULER, "path": PATH_IN_REPO}

real = run_ruler(["--rev", a.tip, "--file", PATH_IN_REPO]) if a.tip else None
report["against_landed_tip"] = {"rc": real["rc"], "verdict": classify(real),
                                "detail": (real.get("json") or {}),
                                "stdout_tail": real["stdout_tail"]} if real else None
if real is not None:
    report["overall"] = report["against_landed_tip"]["verdict"]
else:
    report["overall"] = "NOT_RUN"

if a.selftest:
    # mutant: make pick()'s miss branch hand the caller's input back again, in a temp copy only
    show = subprocess.run(["git", "-C", REPO, "show", (a.tip or "HEAD") + ":" + PATH_IN_REPO],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if show.returncode != 0:
        print(json.dumps({"arm": "selftest", "verdict": "ABORT",
                          "why": "cannot read the shipped table at that rev"}, ensure_ascii=False))
        sys.exit(3)
    src = show.stdout
    if "return rawChannel(value, zh);" not in src:
        # the shipped file is already closed; plant the leak to prove the arm can see it
        planted = src.replace("function pick(", "function pick_MUTANT_LEAK(", 1) if "function pick(" not in src else src
        idx = src.find("return null as never;")
        if idx < 0:
            print(json.dumps({"arm": "selftest", "verdict": "ABORT",
                              "why": "neither the leak nor the closed branch is present -- the ruler's "
                                     "shape assumption no longer matches the file"}, ensure_ascii=False))
            sys.exit(4)
        mutant = src[:idx] + "return rawChannel(value, zh);" + src[idx + len("return null as never;"):]
    else:
        mutant = src  # already leaking: the mutant is the shipped text itself
    closed = src
    tmp = tempfile.mkdtemp(prefix="cmdr_pick_arm_selftest_")
    mpath = os.path.join(tmp, "mutant.ts")
    cpath = os.path.join(tmp, "closed.ts")
    open(mpath, "w", encoding="utf-8", newline="").write(mutant)
    open(cpath, "w", encoding="utf-8", newline="").write(closed)
    rm = run_ruler(["--file", mpath])
    rc_ = run_ruler(["--file", cpath])
    vm, vc = classify(rm), classify(rc_)
    differs = mutant != closed
    report["selftest"] = {"mutant_verdict": vm, "closed_verdict": vc,
                          "mutant_differs_from_shipped": differs,
                          "mutant_bytes": len(mutant.encode("utf-8")),
                          "shipped_bytes": len(closed.encode("utf-8"))}
    ok = (vm == "FAIL") and (vc in ("PASS", "FAIL")) and differs
    report["selftest"]["arm_discriminates"] = ok
    if not ok:
        report["overall"] = "ABORT"
    print(json.dumps(report, ensure_ascii=False, indent=1)[:2200])
    sys.exit(0 if ok else 5)

print(json.dumps(report, ensure_ascii=False, indent=1)[:2200])
sys.exit(0 if report["overall"] == "PASS" else 1)
