# -*- coding: utf-8 -*-
"""Build, prove and ship the cadence hook (the missing half of 常设化): lint, import from a foreign cwd,
run every arm against the production trail, commit exactly one path, push a NEW ref, read it back."""
import ast
import io
import json
import os
import subprocess
import sys
import time

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
NEW_REL = "tools/cnx_ledger_mirror_sync_hook_r1.py"
BRANCH = "refs/heads/review/1d64acf5-mirror-sync-hook-r1"
LOCAL = BRANCH[len("refs/heads/"):]
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
TOKEN = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
TRAIL = r"D:\moodle\_mirror_sync\trail.jsonl"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8",
           CITYNEXUS_API_TOKEN_FILE=TOKEN, CITYNEXUS_MIRROR_SYNC_TRAIL=TRAIL)
for _k in ("http_proxy", "https_proxy"):
    ENV[_k] = ""
R = {"started_local": time.strftime("%Y-%m-%d %H:%M:%S")}


def git(*a, cwd=REPO):
    r = subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=3600)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def step(name, **kw):
    R[name] = kw
    print(json.dumps(dict({"step": name}, **kw), ensure_ascii=False)[:900], flush=True)


def abort(why):
    R["aborted"] = str(why)[:900]
    io.open(os.path.join(HERE, "hook_build_r1.json"), "w", encoding="utf-8").write(
        json.dumps(R, ensure_ascii=False, indent=1))
    print("ABORT:", str(why)[:600])
    raise SystemExit(8)


def main():
    tip = (git("ls-remote", "--refs", "origin", TIP_REF)[1].split() or [None])[0]
    if not tip or git("cat-file", "-e", "%s^{commit}" % tip)[0] != 0:
        abort("no openable authoritative tip (read %r)" % tip)
    if git("cat-file", "-e", "%s:%s" % (tip, NEW_REL))[0] == 0:
        abort("%s is already on the line - this hand must not rewrite a landed path" % NEW_REL)
    git("checkout", "-q", "-B", LOCAL, tip, cwd=WT)
    here = git("symbolic-ref", "--short", "HEAD", cwd=WT)[1]
    if here != LOCAL:
        abort("HEAD reads %s not %s" % (here, LOCAL))
    src = io.open(os.path.join(WT, NEW_REL), encoding="utf-8").read()
    ast.parse(src)
    step("base_and_lint", tip=tip, branch=here, bytes=len(src.encode("utf-8")),
         blob_if_committed=git("hash-object", os.path.join(WT, NEW_REL), cwd=WT)[1], ast="ok")

    # import the way the inserter will: different working directory, repo root on sys.path
    probe = ("import sys, os\n"
             "sys.path.insert(0, '@@WT@@')\n"
             "os.chdir('@@HERE@@')\n"
             "from tools.cnx_ledger_mirror_sync_hook_r1 import run_after_insert, history_tail, HookGuard\n"
             "print('IMPORT_OK from', os.getcwd())\n"
             "print('history_before', history_tail('@@TRAIL@@')['lines'])\n")
    p = subprocess.run([sys.executable, "-c", probe.replace("@@WT@@", WT).replace("@@HERE@@", HERE)
                        .replace("@@TRAIL@@", TRAIL)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=1800)
    step("import_from_outside", rc=p.returncode, out=(p.stdout or "").strip()[-400:],
         err=(p.stderr or "").strip()[-260:])
    if p.returncode != 0:
        abort("the inserter's import shape does not work: %s" % (p.stderr or "")[-400:])

    out_path = os.path.join(HERE, "hook_selftest_r1.json")
    r = subprocess.run([sys.executable, os.path.join(WT, NEW_REL), "--self-test", "--out", out_path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=HERE, timeout=3600)
    lines = [l for l in ((r.stdout or "") + (r.stderr or "")).splitlines() if l.strip()]
    step("self_test", rc=r.returncode, last=lines[-1][:400] if lines else "")
    if r.returncode != 0:
        abort("hook self-test rc %d: %s" % (r.returncode, json.dumps(lines[-8:])[:700]))
    doc = json.load(io.open(out_path, encoding="utf-8"))
    arms = {a["arm"]: a for a in doc["arms"]}
    base = doc["base_reading"]
    if not doc["arms_all_correct"]:
        abort("an arm did not fail closed: %s" % json.dumps(arms, ensure_ascii=False)[:700])
    step("readings", verdict=base["verdict"], local=base["local_blob"], remote=base["remote_blob"],
         points=base["points"], appended=base["appended"], trail_lines=base.get("trail_lines_after"),
         flip=arms["flip_a_byte"]["verdict"], flip_scratch_only=arms["flip_a_byte"]["wrote_only_to_scratch"],
         empty_trail_ok=arms["empty_trail"]["refuses_to_imply_ok"],
         unwritable=arms["unwritable_trail"]["leg"],
         reading_kept=arms["unwritable_trail"]["reading_kept"],
         history_after=arms["history_after_a_run"]["lines"])
    tl = subprocess.run([sys.executable, os.path.join(WT, NEW_REL), "--last", "2"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        env=ENV, cwd=HERE, timeout=1800)
    step("trail_tail", rc=tl.returncode, out=(tl.stdout or "").strip()[:600])

    git("reset", "-q", cwd=WT)
    rc, _o, err = git("add", "--", NEW_REL, cwd=WT)
    staged = [l.strip() for l in git("diff", "--cached", "--name-only", cwd=WT)[1].splitlines() if l.strip()]
    if rc or not staged or staged != [NEW_REL]:
        abort("staged %s rc %d (%s) expected exactly [%s]" % (staged, rc, err[:160], NEW_REL))
    rc, _o, err = git("commit", "-m",
                      "S4-ast-taint cadence hook for the mirror self-check, as ruled: the inserter calls "
                      "run_after_insert() once per applied block and gets one verdict (CURRENT/LAGGING/"
                      "DIVERGED), one exit code (0/7/8/9/6) and one appended audit line - no daemon, no new loop. "
                      "It delegates the measurement to the tool already on this line and the remote read to the "
                      "reader, so exactly one place decides whether a body is complete. Three arms ship with it "
                      "and were run before this commit: flipping one byte in memory stops it reporting CURRENT and "
                      "writes only to a scratch trail; an empty trail is answered as 'no previous line', never as "
                      "an implied ok; a trail path that cannot be written raises the guard naming it while the "
                      "reading is still returned. The audit line lives outside the human inbox so it can never be "
                      "globbed as a candidate block. 0 product bytes, no gate file touched.", cwd=WT)
    if rc != 0:
        abort("commit rc %d: %s" % (rc, err[:300]))
    sha = git("rev-parse", "HEAD", cwd=WT)[1]
    if git("rev-parse", LOCAL, cwd=WT)[1] != sha:
        abort("committed %s but the branch reads %s" % (sha, git("rev-parse", LOCAL, cwd=WT)[1]))
    changed = [l.split("\t")[-1] for l in git("diff", "--name-status", tip, sha, cwd=WT)[1].splitlines() if l.strip()]
    chain = int(git("rev-list", "--count", "%s..%s" % (tip, sha), cwd=WT)[1] or "0")
    root = git("rev-parse", "%s~%d" % (sha, chain), cwd=WT)[1]
    rc, mt, _e = git("merge-tree", "--write-tree", "--name-only", tip, sha, cwd=WT)
    mtl = [l for l in mt.splitlines() if l.strip()]
    if git("ls-remote", "--refs", "origin", BRANCH)[1].strip():
        abort("%s already exists on the server" % BRANCH)
    rc, _o, err = git("push", "origin", "%s:%s" % (BRANCH, BRANCH))
    server = (git("ls-remote", "--refs", "origin", BRANCH)[1].split() or [None])[0]
    if rc or server != sha:
        abort("push rc %d server reads %s (%s)" % (rc, server, err[:200]))
    R["tool"] = {"path": NEW_REL, "head": sha, "branch": BRANCH, "tip": tip, "server": server,
                 "blob": git("ls-tree", "-r", sha, "--", NEW_REL, cwd=WT)[1].split()[2],
                 "commits_on_tip": chain, "chain_root_is_tip": root == tip,
                 "own_paths": [p for p in changed if p == NEW_REL],
                 "foreign_paths": [p for p in changed if p != NEW_REL],
                 "merge_tree": {"tree": (mtl[0] if mtl else None), "conflict_names": len(mtl) - 1, "rc": rc}}
    R["base_reading"] = base
    R["arms"] = arms
    R["trail_file"] = {"path": TRAIL, "lines_after": base.get("trail_lines_after")}
    R["all_clean"] = bool(base["verdict"] == "CURRENT" and doc["arms_all_correct"]
                          and not R["tool"]["foreign_paths"] and len(mtl) == 1 and root == tip)
    io.open(os.path.join(HERE, "hook_build_r1.json"), "w", encoding="utf-8").write(
        json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps({"json": "hook_build_r1.json", "verdict": base["verdict"], "head": sha,
                      "blob": R["tool"]["blob"], "server": server, "conflicts": len(mtl) - 1,
                      "foreign": len(R["tool"]["foreign_paths"]), "trail_lines": base.get("trail_lines_after"),
                      "all_clean": R["all_clean"]}, ensure_ascii=False))
    return 0 if R["all_clean"] else 7


raise SystemExit(main())
