"""ORD-0500 r5 -- re-measure the generation after one shipped comment was corrected.

The comment in `frontend/src/features/checkin/footprint.css` asserted "all six stops answer a centre
hit" while this lane's own census measures 5 of 6 at 390x844.  The comment was fixed to the reading,
which changed the candidate's bytes, so every receipt that names those bytes is taken again in one
window: the faces' screen census, the door probes, both counter-examples, the carrier arms, and the
Q64 exposure ruler on both sides.  Each step is bounded; a step that fails stops the pipeline rather
than leaving a half-filled sheet.
"""
import json
import os
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = os.environ.get("CNX_PHONE_NODE", r"C:/Program Files/nodejs/node.exe")
RULER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ui_exposure_taint_ast_r7b.cjs"
RC_DIR = os.path.join(LANE, "wt22/review/ord0500-checkin/receipts")
LOG = os.path.join(LANE, "run", "remeasure_gen9_r1.txt")

STEPS = [
    ("stack", [PY, "-X", "utf8", os.path.join(LANE, "tools", "gen9_stack_r1.py")], 900),
    ("doors", [PY, "-X", "utf8", os.path.join(LANE, "tools", "gen9_doors_r1.py"),
               "wt23", "wt22", "mutgen9"], 900),
    ("ce1", [PY, "-X", "utf8", os.path.join(LANE, "tools", "gen9_ce1_r1.py")], 900),
    ("ce1_proof", [PY, "-X", "utf8", os.path.join(LANE, "tools", "gen9_ce1_proof_r1.py")], 300),
    ("carrier", [PY, "-X", "utf8", os.path.join(LANE, "tools", "gen9_carrier_r1.py")], 1200),
    ("carrier_arms", [PY, "-X", "utf8", os.path.join(LANE, "tools", "gen9_carrier_arms_r1.py")], 900),
]
EXPOSURE = [("tip", os.path.join(LANE, "wt23/frontend"), "exposure_tip_b604f50d_r1.json"),
            ("candidate", os.path.join(LANE, "wt22/frontend"), "exposure_r5_candidate_r1.json")]


def env_clean():
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "DEEPSEEK_API_KEY"):
        e.pop(k, None)
    return e


def main():
    rec = {"tool": "remeasure_gen9_r1", "started_local": datetime.now().astimezone().isoformat(),
           "steps": []}
    for name, cmd, timeout in STEPS:
        log = os.path.join(LANE, "run", "remeasure_%s_r1.txt" % name)
        began = datetime.now().astimezone().isoformat()
        try:
            p = subprocess.run(cmd, cwd=LANE, env=env_clean(), stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=timeout)
            rc, text = p.returncode, p.stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            rc, text = 124, "TIMEOUT_%sS" % timeout
        open(log, "w", encoding="utf-8").write(text)
        rec["steps"].append({"step": name, "began": began, "rc": rc, "exit_local":
                             datetime.now().astimezone().isoformat(), "log": os.path.basename(log),
                             "tail": text.strip().splitlines()[-1][:220] if text.strip() else ""})
        print("%-14s rc=%s %s" % (name, rc, rec["steps"][-1]["tail"][:150]), flush=True)
        if rc != 0:
            rec["aborted_at"] = name
            break
    if not rec.get("aborted_at"):
        for label, tree, outname in EXPOSURE:
            out = os.path.join(RC_DIR, outname)
            p = subprocess.run([NODE, RULER, "--tree", tree, "--out", out], cwd=LANE,
                               env=env_clean(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=900)
            text = p.stdout.decode("utf-8", "replace")
            open(os.path.join(LANE, "run", "remeasure_exposure_%s_r1.txt" % label), "w",
                 encoding="utf-8").write(text)
            row = {"step": "exposure_" + label, "rc": p.returncode, "out": outname,
                   "tail": text.strip().splitlines()[-1][:220] if text.strip() else ""}
            rec["steps"].append(row)
            print("%-14s rc=%s %s" % (row["step"], p.returncode, row["tail"][:150]), flush=True)
            if p.returncode != 0:
                rec["aborted_at"] = row["step"]
                break
    rec["finished_local"] = datetime.now().astimezone().isoformat()
    open(LOG, "w", encoding="utf-8").write(json.dumps(rec, indent=2, ensure_ascii=False))
    print("WROTE", LOG)
    return 0 if not rec.get("aborted_at") else 1


if __name__ == "__main__":
    sys.exit(main())
