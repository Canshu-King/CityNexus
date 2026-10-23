#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mutant legs for simulation_stage_copy_arm_r1.py: the arm must go RED, naming the cause.

Two mutations, each on a throwaway commit built with plumbing in a temp index:
  M1 flip one English arm inside the dictionary            -> byte-equality claim breaks
  M2 put one pair back inline in the component             -> "no inline pair left" breaks
Neither is pushed; neither touches a published ref.
"""
import io, os, subprocess, sys, tempfile

REPO = "D:/moodle/_qoder_1d64acf5_evtgloss_1018"
CAND = "bab04cb03b6444ff4e2a08deeeec519df8408c6e"
PARENT = "8d990d469873212c490a6a25369993097886ea21"
COMP = "frontend/src/features/simulation/SimulationPanel.tsx"
MOD = "frontend/src/i18n/simulationStageCopy.ts"
ARM = "D:/moodle/_qoder_lane_S4_0926/work/simulation_stage_copy_arm_r1.py"


def git(*a, **kw):
    env = dict(os.environ)
    env.update(kw.get("env", {}))
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, env=env)
    if p.returncode != 0:
        raise SystemExit("git failed %s :: %s" % (a[:2], (p.stderr or b"")[-300:]))
    return (p.stdout or b"").decode("utf-8", "replace").strip()


def blob_of(ref, path):
    return git("show", "%s:%s" % (ref, path))


def mutant_commit(edits):
    """edits: list of (path, new_text).  Returns a commit sha whose parent is PARENT."""
    idx = tempfile.mktemp(prefix="mut_idx_")
    env = {"GIT_INDEX_FILE": idx}
    git("read-tree", CAND, env=env)
    for path, text in edits:
        nb = subprocess.run(
            ["git", "-C", REPO, "hash-object", "-w", "--stdin"],
            input=text.encode("utf-8"), capture_output=True, env=dict(os.environ, **env)
        ).stdout.decode().strip()
        git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (nb, path), env=env)
    tree = git("write-tree", env=env)
    os.remove(idx)
    return git("commit-tree", tree, "-p", PARENT, "-m", "mutant (never pushed)")


def run_arm(ref):
    p = subprocess.run([sys.executable, ARM, REPO, PARENT, ref], capture_output=True)
    out = (p.stdout or b"").decode("utf-8", "replace")
    return p.returncode, out


results = []

# M1: flip one English arm in the dictionary
src = blob_of(CAND, MOD)
needle = 'previousActionStillRunning: { zh: "'
i = src.index(needle)
j = src.index('en: "', i) + 5
m1 = src[:j] + "THE PREVIOUS ACTION IS STILL RUNNING" + src[j + len("The previous action is still running."):]
ref1 = mutant_commit([(MOD, m1)])
rc1, out1 = run_arm(ref1)
bite1 = rc1 == 9 and "previousActionStillRunning" in out1
results.append(("M1 dictionary arm flipped", rc1, bite1, [l for l in out1.split("\n") if "BROKE" in l or "FAIL" in l]))

# M2: put one pair back inline in the component (the dictionary still has it)
csrc = blob_of(CAND, COMP)
line = '      ...simulationStagePair("rowReset"),'
if line not in csrc:
    raise SystemExit("M2 anchor missing; refusing to claim a mutant")
m2 = csrc.replace(line, '      zh: "\u91cd\u7f6e\u5230\u573a\u666f\u8d77\u70b9",\n      en: "Re-seed the scenario",', 1)
ref2 = mutant_commit([(COMP, m2)])
rc2, out2 = run_arm(ref2)
bite2 = rc2 == 9 and any("BROKE" in l for l in out2.split("\n"))
results.append(("M2 pair put back inline", rc2, bite2, [l for l in out2.split("\n") if "BROKE" in l or "FAIL" in l]))

ok = all(b for _, _, b, _ in results)
for name, rc, bite, lines in results:
    print("%s -> rc=%s bit=%s" % (name, rc, bite))
    for l in lines:
        print("   ", l)
print("MUTANTS_BITE=%s" % ok)
sys.exit(0 if ok else 1)
