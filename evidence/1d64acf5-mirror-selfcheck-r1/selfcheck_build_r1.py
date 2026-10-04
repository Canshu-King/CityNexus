# -*- coding: utf-8 -*-
"""Build, prove and ship the standing mirror self-check (approved self-declaration item ①).

Sequence, each step refusing rather than assuming: read the live tip and require the branch base to equal it;
lint the new tool; run its own self-test (one honest pass plus the two counter-arms); run the two ruler nodes that
just landed so "green on the line" is a reading from this base and not a memory; commit exactly one path onto the
named branch; push a NEW ref name; read the sha back off the server; predict the landing read-only.
"""
import ast
import io
import json
import os
import subprocess
import sys
import time

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
REPO = "D:/moodle/CityNexus"
BACKEND = os.path.join(WT, "backend")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
NEW_REL = "tools/cnx_ledger_mirror_sync_check_r1.py"
BRANCH = "refs/heads/review/1d64acf5-mirror-sync-selfcheck-r1"
LOCAL = BRANCH[len("refs/heads/"):]
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
EXPECTED_BASE = "f3ba478caaecdbdf7254786b2bf0d03d323897d0"
TOKEN = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8",
           CITYNEXUS_API_TOKEN_FILE=TOKEN)
for _k in ("http_proxy", "https_proxy"):
    ENV[_k] = ""
G4_NODE = ("tests/test_qoder_ord0296_write_deadline.py::"
           "test_G4_the_lock_wait_is_written_in_exactly_one_place")
D7_NODE = ("tests/test_qoder_ord0476_checkins.py::"
           "test_the_contract_declares_both_doors_and_no_control_they_lack")
G4_LANDED = "032777990661c5220794a91c2a00a8ed1ea97fe7"
D7_LANDED = "534b673b749adfd7548066cca770e0c52d105306"
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
    io.open(os.path.join(HERE, "selfcheck_build_r1.json"), "w", encoding="utf-8").write(
        json.dumps(R, ensure_ascii=False, indent=1))
    print("ABORT:", str(why)[:600])
    raise SystemExit(8)


def run_node(label, node):
    r = subprocess.run([PY, "-m", "pytest", node, "-p", "no:cacheprovider", "-q", "--tb=short"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    res = {"label": label, "rc": r.returncode, "verdict": "green" if r.returncode == 0 else "red",
           "summary": (tail[-1] if tail else out[-160:])[:150]}
    step("node_" + label, **res)
    return res


def main():
    tip = (git("ls-remote", "--refs", "origin", TIP_REF)[1].split() or [None])[0]
    if tip != EXPECTED_BASE:
        abort("the line moved to %s since the landing receipt named %s - re-cut the branch onto the new tip "
              "before shipping this tool" % (tip, EXPECTED_BASE))
    head = git("rev-parse", "HEAD", cwd=WT)[1]
    if head != tip:
        git("checkout", "-q", "-B", LOCAL, tip, cwd=WT)
    here = git("symbolic-ref", "--short", "HEAD", cwd=WT)[1]
    if here != LOCAL:
        abort("HEAD reads %s not %s" % (here, LOCAL))
    step("base", tip=tip, on_branch=here)

    src = io.open(os.path.join(WT, NEW_REL), encoding="utf-8").read()
    ast.parse(src)
    step("lint", path=NEW_REL, bytes=len(src.encode("utf-8")), ast="ok")

    # the tool proves itself: one honest pass plus the arms
    out_path = os.path.join(HERE, "selfcheck_r1.json")
    r = subprocess.run([sys.executable, os.path.join(WT, NEW_REL), "--self-test", "--out", out_path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=HERE, timeout=3600)
    lines = [l for l in ((r.stdout or "") + (r.stderr or "")).splitlines() if l.strip()]
    step("self_test", rc=r.returncode, tail=lines[-1][:500] if lines else "")
    if r.returncode != 0:
        abort("self-test rc %d: %s" % (r.returncode, json.dumps(lines[-6:])[:600]))
    doc = json.load(io.open(out_path, encoding="utf-8"))
    st = doc["state"]
    arms = {a["arm"]: a for a in doc["arms"]}
    if not doc["arms_all_correct"]:
        abort("an arm did not behave: %s" % json.dumps(arms, ensure_ascii=False)[:600])
    if not st["remote_self_proved"]:
        abort("the remote read was not self-proved: %s" % json.dumps(st)[:400])
    step("readings", verdict=st["verdict"], local_blob=st["local_blob"], remote_blob=st["remote_blob"],
         points=[st["points_compared"], st["points_matched"]], local_bytes=st["local_bytes"],
         remote_bytes=st["remote_bytes"], lines=[st["local_lines"], st["remote_lines"]],
         flip_caught=arms["flip_a_byte"]["refused_to_call_it_current"],
         flip_blob_differs=arms["flip_a_byte"]["local_blob_flipped"],
         no_token_refused=arms["no_token"]["refused"], no_token_leg=arms["no_token"].get("leg"))

    # the two cells that just landed, run green on this base
    nodes = [run_node("g4", G4_NODE), run_node("ord0476", D7_NODE)]
    if any(n["verdict"] != "green" for n in nodes):
        abort("a landed cell is not green on its own base: %s" % json.dumps(nodes))

    git("reset", "-q", cwd=WT)
    rc, o, err = git("add", "--", NEW_REL, cwd=WT)
    staged = [l.strip() for l in git("diff", "--cached", "--name-only", cwd=WT)[1].splitlines() if l.strip()]
    if rc or not staged or staged != [NEW_REL]:
        abort("staged %s (rc %d) expected exactly [%s]" % (staged, rc, NEW_REL))
    rc, o, err = git("commit", "-m",
                    "S4-ast-taint ruling 1 (self-declared item ①): a standing self-check for the ledger mirror, "
                    "built on the reader that is already on this line. It samples local-remote-local-remote-local "
                    "and classifies CURRENT / LAGGING / DIVERGED with exit codes 0 / 7 / 8, because a single "
                    "local-vs-remote hash comparison reports a false lag while the inserter is writing. Two "
                    "counter-arms ship with it and both were run before this commit: flipping one byte of the "
                    "local bytes IN MEMORY must stop it calling the mirror current (the real ledger is never "
                    "touched), and with no API token the second channel must refuse by name. Nothing here posts, "
                    "writes a ledger, or moves a ref. 0 product bytes.", cwd=WT)
    if rc != 0:
        abort("commit rc %d: %s" % (rc, err[:300]))
    sha = git("rev-parse", "HEAD", cwd=WT)[1]
    if git("rev-parse", LOCAL, cwd=WT)[1] != sha:
        abort("committed %s but the branch reads %s" % (sha, git("rev-parse", LOCAL, cwd=WT)[1]))
    blob = git("ls-tree", "-r", sha, "--", NEW_REL, cwd=WT)[1].split()[2]
    step("committed", head=sha, blob=blob)

    changed = [l.split("\t")[-1] for l in git("diff", "--name-status", tip, sha, cwd=WT)[1].splitlines() if l.strip()]
    chain = int(git("rev-list", "--count", "%s..%s" % (tip, sha), cwd=WT)[1] or "0")
    root = git("rev-parse", "%s~%d" % (sha, chain), cwd=WT)[1]
    rc, mt, _e = git("merge-tree", "--write-tree", "--name-only", tip, sha, cwd=WT)
    mtl = [l for l in mt.splitlines() if l.strip()]
    if git("ls-remote", "--refs", "origin", BRANCH)[1].strip():
        abort("%s already exists on the server; this hand must add a new name, not rewrite one" % BRANCH)
    rc, o, err = git("push", "origin", "%s:%s" % (BRANCH, BRANCH))
    server = (git("ls-remote", "--refs", "origin", BRANCH)[1].split() or [None])[0]
    if rc or server != sha:
        abort("push rc %d, server reads %s (%s)" % (rc, server, err[:200]))
    step("pushed", ref=BRANCH, head=sha, readback=server, foreign=[p for p in changed if p != NEW_REL],
         conflicts=len(mtl) - 1, tree=(mtl[0] if mtl else None), chain_root_is_tip=root == tip)
    R["self_check_state"] = st
    R["self_check_arms"] = arms
    R["nodes"] = nodes
    R["tool"] = {"path": NEW_REL, "blob": blob, "head": sha, "branch": BRANCH, "tip": tip,
                 "own_paths": [p for p in changed if p == NEW_REL],
                 "foreign_paths": [p for p in changed if p != NEW_REL],
                 "merge_tree": {"tree": mtl[0] if mtl else None, "conflict_names": len(mtl) - 1, "rc": rc}}
    R["landed_cells_reverified"] = {"g4_expected_blob": G4_LANDED, "ord0476_expected_blob": D7_LANDED,
                                    "tip_blobs": {"g4": git("rev-parse", "%s:backend/tests/"
                                                             "test_qoder_ord0296_write_deadline.py" % tip)[1],
                                                  "ord0476": git("rev-parse", "%s:backend/tests/"
                                                                  "test_qoder_ord0476_checkins.py" % tip)[1]}}
    ok = (st["verdict"] == "CURRENT" and doc["arms_all_correct"] and not R["tool"]["foreign_paths"]
          and len(mtl) == 1 and all(n["verdict"] == "green" for n in nodes)
          and all(v == R["landed_cells_reverified"]["tip_blobs"][k] for k, v in
                  (("g4", G4_LANDED), ("ord0476", D7_LANDED))))
    R["all_clean"] = bool(ok)
    io.open(os.path.join(HERE, "selfcheck_build_r1.json"), "w", encoding="utf-8").write(
        json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps({"json": "selfcheck_build_r1.json", "verdict": st["verdict"],
                      "blob": blob, "head": sha, "readback": server,
                      "landed_blob_check": R["landed_cells_reverified"]["tip_blobs"],
                      "all_clean": R["all_clean"]}, ensure_ascii=False))
    return 0 if R["all_clean"] else 7


raise SystemExit(main())
