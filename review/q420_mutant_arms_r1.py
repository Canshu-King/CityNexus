#!/usr/bin/env python3
"""ORD-0420 counter-controls: three arms that each have to go RED, for three different reasons.

K0 puts the two render sites back to the pre-fix expression. If the acceptance criterion really bites
the reported defect, this must be RED with four Latin-only headings on the zh arm.
K1 changes one Chinese dictionary value. If the heading is dictionary-fed the screen must move with it;
if the screen were still reading the registry's literal, this arm would stay GREEN - which is the whole
point of the arm.
K2 changes one English dictionary value, and answers the question the order asks: the English arm looks
correct today, so does it look correct because of t() or because the code's literal happens to match?

Each run patches the worktree, runs the commander's runner through this lane's wrapper, restores with
`git checkout --`, and refuses to continue unless the restored bytes match the committed blob.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

WT = r"D:/moodle/_qoder_lane_q0420"
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SPEC = "e2e/qoder-ord0420-drawer-group-headings.spec.ts"
LC = "frontend/src/i18n/LocaleContext.tsx"
V8 = "frontend/src/app/V8Experience.tsx"
LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
bad = []


def sh(*a, cwd=WT):
    r = subprocess.run(a, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def committed_blob(rel):
    return sh("git", "rev-parse", "HEAD:" + rel)[1]


def wt_blob(rel):
    data = open(os.path.join(WT, rel), "rb").read()
    return hashlib.sha1(("blob %d\0" % len(data)).encode() + data).hexdigest()


def patch(rel, old, new, want=1):
    p = os.path.join(WT, rel)
    txt = open(p, encoding="utf-8", newline="").read()
    n = txt.count(old)
    if n != want:
        raise SystemExit("PATCH ANCHOR %s matched %d times, wanted %d -- %r" % (rel, n, want, old[:60]))
    open(p, "w", encoding="utf-8", newline="").write(txt.replace(old, new))


def restore(rel):
    sh("git", "checkout", "--", rel)
    if wt_blob(rel) != committed_blob(rel):
        bad.append("%s did not restore byte-identically" % rel)
    rc, out, _ = sh("git", "status", "--porcelain", "-uno")
    if out:
        bad.append("a tracked file is still dirty after restore: %r" % out[:200])


def run(tag):
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    r = subprocess.run([VENV, "-X", "utf-8", os.path.join(WT, "review", "e4f_e2e_r1.py"),
                        "--wt", WT, "--target", SPEC, "--tag", tag],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    out = r.stdout + r.stderr
    m = re.search(r'"verdict":\s*"(\w+)"', out) or re.search(r"verdict=(\w+)", out)
    logs = sorted([f for f in os.listdir(os.path.join(LIVE, "e2e_logs"))
                   if f.startswith(tag + "_") and f.endswith(".json")])
    j = json.load(open(os.path.join(LIVE, "e2e_logs", logs[-1]), encoding="utf-8")) if logs else {}
    txt = ""
    if logs:
        lf = logs[-1].replace(".json", ".log")
        txt = open(os.path.join(LIVE, "e2e_logs", lf), encoding="utf-8", errors="replace").read()
    return {"tag": tag, "receipt": os.path.basename(logs[-1]) if logs else None,
            "log": os.path.basename(logs[-1]).replace(".json", ".log") if logs else None,
            "tree": j.get("tree"), "run_id": j.get("run_id"), "verdict": j.get("verdict"),
            "counts": j.get("counts"), "ports": j.get("ports"), "db": j.get("db"),
            "readings": [l.strip() for l in txt.split("\n") if l.strip().startswith("Q420")],
            "failing": sorted(set(re.findall(r"spec\.ts:(\d+):\d", txt)))}


HEADS = {"K0": [(V8, '<span className="v8-nav-group">{t(navGroupKey(item.group))}</span>',
                 '<span className="v8-nav-group">{item.group}</span>'),
                (V8, '{"group" in item ? t(navGroupKey(item.group)) : t("nav.groupOther")}',
                 '{"group" in item ? item.group : "MORE"}')],
         "K1": [(LC, '"nav.groupPlan": "规划",', '"nav.groupPlan": "PLX-SENTINEL",')],
         "K2": [(LC, '"nav.groupSystem": "SYSTEM",', '"nav.groupSystem": "SYS-SENTINEL",')]}
EXPECT = {"K0": ("RED", "zh", "TODAY"), "K1": ("RED", "zh", "PLX-SENTINEL"),
          "K2": ("RED", "en", "SYS-SENTINEL")}

results = {}
for key, edits in HEADS.items():
    touched = set()
    for rel, old, new in edits:
        patch(rel, old, new)
        touched.add(rel)
    res = run("e4f" + key.lower())
    for rel in sorted(touched):
        restore(rel)
    want_verdict, want_arm, want_token = EXPECT[key]
    arm_lines = [l for l in res["readings"] if (" " + want_arm + " ") in l]
    moved = any(want_token in l for l in arm_lines)
    res.update({"want": want_verdict, "met": res["verdict"] == want_verdict,
                "arm_lines": arm_lines, "screen_moved_to_token": moved, "token": want_token})
    if res["verdict"] != want_verdict:
        bad.append("%s expected %s, got %s" % (key, want_verdict, res["verdict"]))
    if not moved:
        bad.append("%s: the %s arm never showed %s, so the heading is not dictionary-fed" % (key, want_arm, want_token))
    results[key] = res

print(json.dumps(results, ensure_ascii=False, indent=1))
open(os.path.join(r"D:/moodle/_qoder_lane_q0420", "review", "q420_mutant_arms.json"), "w",
     encoding="utf-8", newline="\n").write(json.dumps(results, ensure_ascii=False, indent=1) + "\n")
if bad:
    print("REFUSING -- " + "; ".join(bad))
    sys.exit(1)
rc, out, _ = sh("git", "status", "--porcelain", "-uno")
rc2, out2, _ = sh("git", "status", "--porcelain")
print("RESTORE_TRACKED_DIRTY=%d untracked_entries=%d" % (
    len([l for l in out.split("\n") if l.strip()]), len([l for l in out2.split("\n") if l.strip()]) - len(
        [l for l in out.split("\n") if l.strip()])))
print("HEAD %s" % sh("git", "rev-parse", "HEAD")[1])
for rel in (LC, V8):
    print("  blob %s %s" % (rel, wt_blob(rel)))
