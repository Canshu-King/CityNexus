# -*- coding: utf-8 -*-
"""Cell 2 only, because cell 1 is already published and must not be rewritten.

What happened on the previous run, stated plainly: the ORD-0476 probe opens with `git checkout --detach`, so the
commit I made after it landed on a detached HEAD, `refs/heads/review/...-r5` still pointed at the tip, and the
push shipped that pointer.  The read-back refused it (`the server reads 4fdd6345...`), the stray remote ref was
deleted in the same hour, and this script is the corrected hand: re-attach the branch *under* the measured text
before committing, and refuse to commit at all while HEAD is detached.

Cell 1 (`review/1d64acf5-ord0296-g4-floor-r6` = c23cb0a302c42ab2dc832743441b3d7da7461308) is left exactly as the
server holds it; this run only reads it back and predicts its landing.
"""
import io
import json
import os
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
BACKEND = os.path.join(WT, "backend")
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")
for _k in ("http_proxy", "https_proxy"):
    ENV[_k] = ""
TRACK = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
BRANCH = "refs/heads/mirror/integration-frontend-apple-pass1"

D7_NEW = "refs/heads/review/1d64acf5-ord0476-response-set-r6"
D7_LOCAL = "review/1d64acf5-ord0476-response-set-r6"
D7_TEST = "backend/tests/test_qoder_ord0476_checkins.py"
D7_TIP_BLOB = "853e9a67a7c33f4ac33b36dc49f53fd806265442"
D7_FINAL_BLOB = "534b673b749adfd7548066cca770e0c52d105306"
D7_NODE = ("tests/test_qoder_ord0476_checkins.py::"
           "test_the_contract_declares_both_doors_and_no_control_they_lack")
OLD_LINE = '    assert sorted(listed["responses"]) == ["200", "409"], sorted(listed["responses"])'

G4_PUBLISHED = "refs/heads/review/1d64acf5-ord0296-g4-floor-r6"
G4_ARM = "backend/tests/test_qoder_ord0296_write_deadline.py"
G4_ART = "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r5.json"
G4_NODE = ("tests/test_qoder_ord0296_write_deadline.py::"
           "test_G4_the_lock_wait_is_written_in_exactly_one_place")
OWN = {D7_TEST, G4_ARM, G4_ART}


def git(*a, cwd=WT):
    r = subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=1800)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


repo = git


def blob(rev, path):
    rc, out, _ = repo("rev-parse", "%s:%s" % (rev, path))
    return out if rc == 0 else None


def local_blob(rel):
    return git("hash-object", os.path.join(WT, rel.replace("/", os.sep)))[1]


def show(rev, path):
    return git("show", "%s:%s" % (rev, path))[1]


def step(name, **kw):
    print(json.dumps(dict({"step": name}, **kw), ensure_ascii=False), flush=True)


def abort(why):
    step("ABORT", reason=why[:600])
    raise SystemExit(8)


def read_tip():
    rc, ls, err = repo("ls-remote", "--refs", "origin", BRANCH)
    tip = ls.split()[0] if ls else None
    if not tip:
        abort("no tip from the server: %s" % err[:160])
    if repo("cat-file", "-e", "%s^{commit}" % tip)[0] != 0:
        repo("fetch", "origin", "+%s:%s" % (BRANCH, TRACK))
    if repo("cat-file", "-e", "%s^{commit}" % tip)[0] != 0 or repo("rev-parse", TRACK)[1] != tip:
        abort("tip %s is not openable locally" % tip)
    return tip


def audit(tip):
    a = {"tip": tip, "tip_d76_blob": blob(tip, D7_TEST), "tip_arm_blob": blob(tip, G4_ARM),
         "tip_yaml_blob": blob(tip, "contracts/openapi.yaml")}
    arm_src = show(tip, G4_ARM)
    if a["tip_d76_blob"] != D7_TIP_BLOB:
        abort("the ord0476 preimage moved: %s != %s" % (a["tip_d76_blob"], D7_TIP_BLOB))
    if a["tip_arm_blob"] != "d3e21e9084a3589678d08f7b50afe5119b2b85b8":
        abort("the g4 preimage moved: %s" % a["tip_arm_blob"])
    if show(tip, D7_TEST).count(OLD_LINE) != 1:
        abort("the replacement needle is not unique on this tip")
    if 'Path(rel).name == "write_deadline.py"' not in arm_src or "consumer_writes" in arm_src:
        abort("the line's arm is not the shape the pair was measured against")
    return a


def on_branch(name):
    rc, here, _ = git("symbolic-ref", "--short", "HEAD")
    if rc != 0 or here != name:
        abort("HEAD reads %s, not on %s - refusing to commit onto a detached head" % (here or "DETACHED", name))


def commit_only(paths, message, branch):
    on_branch(branch)
    git("reset", "-q")
    rc, out, err = git("add", "--", *paths)
    if rc != 0:
        abort("git add rc %d: %s | %s" % (rc, out[:200], err[:300]))
    staged = [l.strip() for l in git("diff", "--cached", "--name-only")[1].splitlines() if l.strip()]
    if not staged or sorted(staged) != sorted(paths):
        abort("the staged set is %s but this hand means to commit exactly %s" % (staged, paths))
    rc, out, err = git("commit", "-m", message)
    if rc != 0:
        abort("commit rc %d: %s" % (rc, err[:300]))
    sha = git("rev-parse", "HEAD")[1]
    if git("rev-parse", branch)[1] != sha:
        abort("committed %s but the branch reads %s" % (sha, git("rev-parse", branch)[1]))
    return sha


def prediction(tip, ref, sha):
    changed = [(l.split("\t")[0][0], l.split("\t")[-1])
               for l in git("diff", "--name-status", tip, sha)[1].splitlines() if l.strip()]
    chain = int(git("rev-list", "--count", "%s..%s" % (tip, sha))[1] or "0")
    root = git("rev-parse", "%s~%d" % (sha, chain))[1]
    rc, mt, _ = repo("merge-tree", "--write-tree", "--name-only", tip, sha)
    lines = [l for l in mt.splitlines() if l.strip()]
    own = [p for _s, p in changed if p in OWN]
    pre = []
    for p in own:
        cb = git("ls-tree", "-r", sha, "--", p)[1].split()[2]
        tb = blob(tip, p)
        pre.append({"path": p, "candidate_blob": cb, "tip_blob": tb, "already_on_the_line": cb == tb})
    return {"ref": ref, "sha": sha, "commits_on_tip": chain, "chain_root": root,
            "chain_root_is_tip": root == tip, "own_paths": own,
            "foreign_paths": [p for _s, p in changed if p not in OWN], "preimage": pre,
            "merge_tree": {"rc": rc, "tree": lines[0] if lines else None,
                           "conflict_names": len(lines) - 1, "clean": rc == 0 and len(lines) == 1}}


def push_new(ref, sha):
    rc, ls, err = repo("ls-remote", "--refs", "origin", ref)
    if ls.strip():
        abort("%s already exists on the server at %s - this hand must not rewrite a published ref"
              % (ref, ls.split()[0]))
    rc, out, err = repo("push", "origin", "%s:%s" % (ref, ref))
    if rc != 0:
        abort("push rc %d: %s | %s" % (rc, out[-300:], err[-300:]))
    rc, ls, _ = repo("ls-remote", "--refs", "origin", ref)
    server = ls.split()[0] if ls else None
    if server != sha:
        abort("pushed %s as %s but the server reads %s" % (ref, sha, server))
    return server


def run_node(label, node):
    r = subprocess.run([PY, "-m", "pytest", node, "-p", "no:cacheprovider", "-q", "--tb=short"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    res = {"rc": r.returncode, "verdict": "green" if r.returncode == 0 else "red",
           "summary": (tail[-1] if tail else out[-160:])[:150]}
    step("node", label=label, **res)
    return res


def main():
    tip = read_tip()
    aud = audit(tip)
    step("tip", sha=tip, **aud)

    # the published cell 1 branch is only read back, never moved
    rc, ls, _ = repo("ls-remote", "--refs", "origin", G4_PUBLISHED)
    g4_sha = ls.split()[0] if ls else None
    if g4_sha != "c23cb0a302c42ab2dc832743441b3d7da7461308":
        abort("cell 1 no longer reads what this hand pushed (%s); refusing to describe a ref I cannot pin"
              % g4_sha)
    if repo("cat-file", "-e", "%s^{commit}" % g4_sha)[0] != 0:
        git("fetch", "origin", "+%s:refs/remotes/origin/1d64acf5-ord0296-g4-floor-r6" % G4_PUBLISHED)

    git("checkout", "-q", "-B", D7_LOCAL, tip)
    r = subprocess.run([sys.executable, os.path.join(HERE, "ord0476_gate_probe_r5.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       env=dict(ENV, CNX_PROBE_TIP=tip), timeout=3600, cwd=HERE)
    out = (r.stdout or "") + (r.stderr or "")
    step("probe", script="ord0476_gate_probe_r5.py", rc=r.returncode,
         last=[l for l in out.splitlines() if l.strip()][-1][:400])
    if r.returncode != 0:
        abort("ord0476 probe rc %d: %s" % (r.returncode, out[-900:]))
    src = io.open(os.path.join(WT, D7_TEST.replace("/", os.sep)), encoding="utf-8").read()
    git("checkout", "-q", "-B", D7_LOCAL, tip)          # the probe detached HEAD; put the branch back
    io.open(os.path.join(WT, D7_TEST.replace("/", os.sep)), "w", encoding="utf-8", newline="\n").write(src)
    if OLD_LINE in src or local_blob(D7_TEST) != D7_FINAL_BLOB:
        abort("the cell is not the measured bytes: needle=%s blob=%s" % (OLD_LINE in src, local_blob(D7_TEST)))
    h_d7 = commit_only([D7_TEST], "S4-ast-taint CMDR 01:24 ruling 1 on the read door, re-cut onto %s read from "
                                  "the server in this run: promised codes by name, a named-expansion whitelist "
                                  "and the named-but-undocumented arm. Six states measured on this base, blob "
                                  "%s byte-identical to the cell delivered at 01:53. 0 product bytes."
                       % (tip, D7_FINAL_BLOB), D7_LOCAL)
    step("committed", head=h_d7, on_branch=D7_LOCAL)

    p_d7 = prediction(tip, D7_NEW, h_d7)
    p_g4 = prediction(tip, G4_PUBLISHED, g4_sha)
    for p in (p_d7, p_g4):
        step("predicted", ref=p["ref"].split("/")[-1], root_is_tip=p["chain_root_is_tip"],
             conflicts=p["merge_tree"]["conflict_names"], foreign=len(p["foreign_paths"]),
             own=len(p["own_paths"]), tree=p["merge_tree"]["tree"],
             on_line=[x["path"] for x in p["preimage"] if x["already_on_the_line"]])
    server = push_new(D7_NEW, h_d7)
    step("pushed", ref=D7_NEW, sha=h_d7, readback=server)

    git("checkout", "-q", "-B", D7_LOCAL, h_d7)
    runs = {"d76_node_on_the_newest_base": run_node("d76", D7_NODE)}
    git("checkout", "-q", "--detach", g4_sha)
    runs["g4_node_on_the_published_branch"] = run_node("g4", G4_NODE)
    runs["g4_whole_ruler_file"] = run_node("g4_file", "tests/test_qoder_ord0296_write_deadline.py")

    probe = json.load(io.open(os.path.join(HERE, "ord0476_gate_probe_r5.json"), encoding="utf-8"))
    g4probe = json.load(io.open(os.path.join(HERE, "g4_shape_probe_r5.json"), encoding="utf-8"))
    doc = {"generated_at_local": time.strftime("%Y-%m-%d %H:%M:%S"), "tip": tip,
           "tip_source": "git ls-remote --refs origin " + BRANCH, "audit": aud,
           "cell1_published": {"ref": G4_PUBLISHED, "sha": g4_sha, "prediction": p_g4,
                               "artifact_blob": git("ls-tree", "-r", g4_sha, "--", G4_ART)[1].split()[2]},
           "cell2": {"ref": D7_NEW, "sha": h_d7, "prediction": p_d7, "server_readback": server},
           "d76_probe": probe, "g4_probe_three_legs": g4probe, "node_runs": runs,
           "detached_head_incident": {"what": "the ORD-0476 probe's opening `checkout --detach` left the commit "
                                              "off any branch, so the push shipped the branch pointer (the tip) "
                                              "instead",
                                      "caught_by": "push_and_readback: the server read 4fdd6345c0bfef36f12468390baad50946aad2b6 "
                                                   "for a ref this hand pushed as f3e2e80acc3caed73576dc65e514fe698ebb2b64",
                                      "cleanup": "the stray refs/heads/review/1d64acf5-ord0476-response-set-r5 "
                                                 "was deleted by this lane; nothing else was deleted and no "
                                                 "line moved",
                                      "bolt": "commit_only now refuses while `symbolic-ref --short HEAD` is not "
                                              "the branch it is about to commit onto"}}
    all_clean = all(p["chain_root_is_tip"] and p["merge_tree"]["clean"] and not p["foreign_paths"]
                    and not any(x["already_on_the_line"] for x in p["preimage"])
                    for p in (p_d7, p_g4)) and probe["all_met"] and g4probe["all_met"] and all(
                        v["verdict"] == "green" for k, v in runs.items() if "node" in k or "file" in k)
    doc["all_clean"] = bool(all_clean)
    io.open(os.path.join(HERE, "recut_d76_only_r3.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"json": "recut_d76_only_r3.json", "tip": tip, "cell2": h_d7, "cell1": g4_sha,
                      "all_clean": doc["all_clean"],
                      "runs": {k: v["summary"] for k, v in runs.items()}}, ensure_ascii=False))
    return 0 if doc["all_clean"] else 7


raise SystemExit(main())
