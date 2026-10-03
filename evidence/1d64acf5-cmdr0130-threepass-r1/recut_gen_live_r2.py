# -*- coding: utf-8 -*-
"""Ruling 1, applied to whatever the authoritative line reads at the moment this runs.

The line has been moving every few minutes tonight, so a hand that pins one sha in its own source aborts
before it can measure anything (that is how r1 died, and aborting was right).  This version reads the tip from
`git ls-remote`, hands it to the probes through `CNX_PROBE_TIP`, and fails closed on the thing that actually
matters: the preimage bytes.  If the line still carries the same blob for every path this hand changes, the
cell is the same cell no matter which commit it sits on; if any preimage moved, the run stops rather than
reporting a pair that is not a pair.

Order:
  1. read the tip, prove that sha is a local commit, audit the preimages (the arm blob, that the exemption
     still being granted by base name, that the replacement needle is still unique, the two product anchors);
  2. cut the G4 cell there, run its 8-state pair here, generate this generation's shape artifact, commit;
  3. cut the ORD-0476 cell there, run its 6 states here, commit;
  4. re-read the tip; if it moved, re-attach the *same blobs* onto the newest one (git only, no re-measure),
     then run each cell's own node once on that newest base so "green here" is a reading and not an inference;
  5. predict the landing read-only, push both review/* branches, read the shas back off the server.

Landing and the authoritative line stay the sequencer's move; 0 product bytes.
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

G4_NEW = "refs/heads/review/1d64acf5-ord0296-g4-floor-r6"
G4_ARM = "backend/tests/test_qoder_ord0296_write_deadline.py"
G4_ARM_BLOB = "032777990661c5220794a91c2a00a8ed1ea97fe7"
G4_PRE_BLOB = "d3e21e9084a3589678d08f7b50afe5119b2b85b8"
G4_ART = "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r5.json"
G4_NODE = ("tests/test_qoder_ord0296_write_deadline.py::"
           "test_G4_the_lock_wait_is_written_in_exactly_one_place")

D7_NEW = "refs/heads/review/1d64acf5-ord0476-response-set-r5"
D7_TEST = "backend/tests/test_qoder_ord0476_checkins.py"
D7_TIP_BLOB = "853e9a67a7c33f4ac33b36dc49f53fd806265442"
D7_FINAL_BLOB = "534b673b749adfd7548066cca770e0c52d105306"
D7_NODE = ("tests/test_qoder_ord0476_checkins.py::"
           "test_the_contract_declares_both_doors_and_no_control_they_lack")

OLD_LINE = '    assert sorted(listed["responses"]) == ["200", "409"], sorted(listed["responses"])'
MAIN = "backend/app/main.py"
STAY = "backend/app/stay_generation_operations.py"
DEADLINE = "backend/app/db/write_deadline.py"
YAML = "contracts/openapi.yaml"
G4_LOCAL = G4_NEW[len("refs/heads/"):]
D7_LOCAL = D7_NEW[len("refs/heads/"):]
OWN = {G4_ARM, G4_ART, D7_TEST}

STATE = {"tip_start": None, "tip_end": None, "preimage_audit_start": None, "preimage_audit_end": None,
         "cells": {}, "final_node_runs": {}, "note": []}


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
    io.open(os.path.join(HERE, "recut_gen_live_r2_aborted.json"), "w", encoding="utf-8").write(
        json.dumps(STATE, ensure_ascii=False, indent=1))
    raise SystemExit(8)


def read_tip():
    rc, ls, err = repo("ls-remote", "--refs", "origin", BRANCH)
    tip = ls.split()[0] if ls else None
    if not tip:
        abort("no tip from the server: %s" % err[:160])
    if repo("cat-file", "-e", "%s^{commit}" % tip)[0] != 0:
        repo("fetch", "origin", "+%s:%s" % (BRANCH, TRACK))
    if repo("cat-file", "-e", "%s^{commit}" % tip)[0] != 0 or repo("rev-parse", TRACK)[1] != tip:
        abort("tip %s is not openable locally (tracking ref reads %s)" % (tip, repo("rev-parse", TRACK)[1]))
    return tip


def audit(tip):
    a = {"tip": tip, "tip_arm_blob": blob(tip, G4_ARM), "tip_d76_blob": blob(tip, D7_TEST),
         "tip_yaml_blob": blob(tip, YAML), "tip_deadline_blob": blob(tip, DEADLINE)}
    arm_src = show(tip, G4_ARM)
    d7_src = show(tip, D7_TEST)
    a["pre_exemption_is_still_by_basename"] = 'Path(rel).name == "write_deadline.py"' in arm_src
    a["pre_arm_has_no_whitelist"] = "SINGLE_SOURCE_FILES" not in arm_src
    a["needle_count_on_tip"] = d7_src.count(OLD_LINE)
    a["main_anchor_present"] = ("PLAN_CLAIM_LEASE_MS = int(settings.write_deadline_ms) + "
                                "int(settings.write_busy_timeout_ms)") in show(tip, MAIN)
    a["stay_anchor_present"] = 'session.execute(text("PRAGMA busy_timeout = 1500"))' in show(tip, STAY)
    a["yaml_checkin_section_present"] = "/journeys/{journey_id}/checkins:" in show(tip, YAML)
    bad = []
    if a["tip_arm_blob"] != G4_PRE_BLOB:
        bad.append("g4 arm preimage %s != %s" % (a["tip_arm_blob"], G4_PRE_BLOB))
    if a["tip_d76_blob"] != D7_TIP_BLOB:
        bad.append("ord0476 test preimage %s != %s" % (a["tip_d76_blob"], D7_TIP_BLOB))
    for k in ("pre_exemption_is_still_by_basename", "pre_arm_has_no_whitelist", "main_anchor_present",
              "stay_anchor_present", "yaml_checkin_section_present"):
        if not a[k]:
            bad.append(k)
    if a["needle_count_on_tip"] != 1:
        bad.append("needle not unique (%s)" % a["needle_count_on_tip"])
    if bad:
        abort("preimage audit failed on %s: %s" % (tip, "; ".join(bad)))
    return a


def run_probe(name, tip):
    env = dict(ENV, CNX_PROBE_TIP=tip)
    r = subprocess.run([sys.executable, os.path.join(HERE, name)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=3600, cwd=HERE)
    out = (r.stdout or "") + (r.stderr or "")
    lines = [l for l in out.splitlines() if l.strip()]
    step("probe", script=name, rc=r.returncode, last=lines[-1][:400] if lines else "")
    if r.returncode != 0:
        abort("%s exited %d: %s" % (name, r.returncode, out[-1200:]))
    return out


def commit_only(paths, message, on_branch):
    """Stage exactly this hand's paths and commit them onto the named branch.

    Two guards, both earned tonight.  The staged set must equal this hand's paths and must not be
    empty (an `git add` that staged nothing once sailed through a "nothing foreign is staged" check
    and produced a false green).  And HEAD must be *on* the branch: the ORD-0476 probe opens with
    `checkout --detach`, so a commit made after it lands on no branch at all, and the push then
    ships the stale branch pointer instead of the work - which is exactly what the read-back
    refused a moment later.
    """
    rc, here, err = git("symbolic-ref", "--short", "HEAD")
    if rc != 0 or here != on_branch:
        abort("HEAD is %s, not on %s - refusing to commit onto a detached head"
                    % (here or "DETACHED", on_branch))
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
    if git("rev-parse", on_branch)[1] != sha:
        abort("committed %s but the branch %s now reads %s"
              % (sha, on_branch, git("rev-parse", on_branch)[1]))
    return sha


def carry_from(source, paths):
    for p in paths:
        rc, _o, err = git("checkout", source, "--", p)
        want = git("ls-tree", "-r", source, "--", p)[1].split()[2]
        if local_blob(p) != want:
            abort("carrying %s from %s gave %s, expected %s" % (p, source[:12], local_blob(p), want))


def run_node(label, node):
    r = subprocess.run([PY, "-m", "pytest", node, "-p", "no:cacheprovider", "-q", "--tb=short"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    res = {"rc": r.returncode, "verdict": "green" if r.returncode == 0 else "red",
           "summary": (tail[-1] if tail else out[-160:])[:150]}
    step("node_on_live_tip", label=label, **res)
    return res


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


def push_and_readback(ref, sha):
    rc, out, err = repo("push", "origin", "%s:%s" % (ref, ref))
    if rc != 0:
        abort("push of %s rc %d: %s | %s" % (ref, rc, out[-300:], err[-300:]))
    rc, ls, _ = repo("ls-remote", "--refs", "origin", ref)
    parts = ls.split()
    server = parts[0] if parts else None
    if server != sha:
        abort("pushed %s as %s but the server reads %s" % (ref, sha, server))
    return server


def main():
    tip_start = read_tip()
    STATE["tip_start"] = tip_start
    STATE["preimage_audit_start"] = audit(tip_start)
    step("tip_start", sha=tip_start)

    # cell 1 - the G4 single-source exemption
    git("checkout", "-q", "-B", G4_LOCAL, tip_start)
    git("checkout", "3f7cda327038ac02c94ffe5a439048f21bee0a8a", "--", G4_ARM)
    if local_blob(G4_ARM) != G4_ARM_BLOB:
        abort("carried arm is %s not the measured %s" % (local_blob(G4_ARM), G4_ARM_BLOB))
    h_arm = commit_only([G4_ARM], on_branch=G4_LOCAL, message= "S4-ast-taint CMDR ruling 1 re-cut onto %s (read back by ls-remote in this "
                                  "run): the single-source exemption as a named path whitelist with its "
                                  "anti-rot guard, arm blob carried byte-identical (%s).  Ruler only, "
                                  "0 product bytes." % (tip_start, G4_ARM_BLOB))
    run_probe("g4_shape_probe_r5.py", tip_start)
    run_probe("g4_shape_artifact_r5.py", tip_start)
    art_blob = local_blob(G4_ART)
    h_g4 = commit_only([G4_ART], on_branch=G4_LOCAL, message= "S4-ast-taint this generation's machine-readable shape artifact (%s): "
                                 "both arm generations over the same injections on %s, every reverted file "
                                 "re-hashed. r1-r3 stay where they were published; nothing is overwritten."
                         % (art_blob, tip_start))
    STATE["cells"]["g4"] = {"base": tip_start, "arm_commit": h_arm, "head": h_g4, "artifact_blob": art_blob}
    step("g4_cut", head=h_g4, artifact_blob=art_blob)

    # cell 2 - the ORD-0476 read door's response set
    git("checkout", "-q", "-B", D7_LOCAL, tip_start)
    run_probe("ord0476_gate_probe_r5.py", tip_start)
    # the probe ran from a detached HEAD, so put the branch back under this commit before writing it
    src = io.open(os.path.join(WT, D7_TEST.replace("/", os.sep)), encoding="utf-8").read()
    git("checkout", "-q", "-B", D7_LOCAL, tip_start)
    io.open(os.path.join(WT, D7_TEST.replace("/", os.sep)), "w", encoding="utf-8",
            newline="\n").write(src)
    if OLD_LINE in src or local_blob(D7_TEST) != D7_FINAL_BLOB:
        abort("the ord0476 cell is not the measured bytes: needle still present=%s blob=%s"
              % (OLD_LINE in src, local_blob(D7_TEST)))
    h_d7 = commit_only([D7_TEST], on_branch=D7_LOCAL, message="S4-ast-taint CMDR 01:24 ruling 1 on the read door, re-cut onto %s: "
                                  "promised codes by name plus a named-expansion whitelist and the "
                                  "named-but-undocumented arm, blob %s byte-identical to the cell delivered "
                                  "at 01:53. 0 product bytes." % (tip_start, D7_FINAL_BLOB))
    STATE["cells"]["ord0476"] = {"base": tip_start, "head": h_d7}
    step("d76_cut", head=h_d7)

    tip_end = read_tip()
    STATE["tip_end"] = tip_end
    moved = tip_end != tip_start
    step("tip_recheck", sha=tip_end, moved_during_hand=moved)
    if moved:
        STATE["preimage_audit_end"] = audit(tip_end)
        git("checkout", "-q", "-B", G4_LOCAL, tip_end)
        carry_from(h_g4, [G4_ARM, G4_ART])
        h_g4 = commit_only([G4_ARM, G4_ART], on_branch=G4_LOCAL, message= "S4-ast-taint re-attached to %s, read from the server after the "
                                             "line moved again mid-hand: the same two blobs (%s, %s), carried "
                                             "from %s, so the eight-state pair measured there is this cell. "
                                             "0 product bytes." % (tip_end, local_blob(G4_ARM),
                                                                   local_blob(G4_ART), h_g4[:12]))
        STATE["cells"]["g4"].update({"base": tip_end, "head": h_g4, "re_attached": True})
        git("checkout", "-q", "-B", D7_LOCAL, tip_end)
        carry_from(h_d7, [D7_TEST])
        h_d7 = commit_only([D7_TEST], on_branch=D7_LOCAL, message="S4-ast-taint re-attached to %s: the same blob %s from %s, measured "
                                      "with six states on %s and re-run green here. 0 product bytes."
                           % (tip_end, local_blob(D7_TEST), h_d7[:12], tip_start))
        STATE["cells"]["ord0476"].update({"base": tip_end, "head": h_d7, "re_attached": True})
        STATE["final_node_runs"]["g4"] = run_node("g4", G4_NODE)
        STATE["final_node_runs"]["ord0476"] = run_node("d76", D7_NODE)
        STATE["final_node_runs"]["g4_family"] = run_node(
            "g4_family", "tests/test_qoder_ord0296_write_deadline.py")

    preds = []
    for ref, sha in ((G4_NEW, h_g4), (D7_NEW, h_d7)):
        p = prediction(tip_end, ref, sha)
        p["server_sha_after_push"] = push_and_readback(ref, sha)
        preds.append(p)
        step("pushed", ref=ref, sha=sha, readback=p["server_sha_after_push"],
             root_is_tip=p["chain_root_is_tip"], conflicts=p["merge_tree"]["conflict_names"],
             foreign=len(p["foreign_paths"]))
    STATE["candidates"] = preds
    STATE["g4_probe"] = json.load(io.open(os.path.join(HERE, "g4_shape_probe_r5.json"), encoding="utf-8"))
    STATE["d76_probe"] = json.load(io.open(os.path.join(HERE, "ord0476_gate_probe_r5.json"), encoding="utf-8"))
    STATE["all_clean"] = all(p["chain_root_is_tip"] and p["merge_tree"]["clean"] and not p["foreign_paths"]
                             and not any(x["already_on_the_line"] for x in p["preimage"]) for p in preds)
    io.open(os.path.join(HERE, "recut_gen_live_r2.json"), "w", encoding="utf-8").write(
        json.dumps(STATE, ensure_ascii=False, indent=1))
    print(json.dumps({"json": "recut_gen_live_r2.json", "tip_start": tip_start, "tip_end": tip_end,
                      "moved_during_hand": moved, "all_clean": STATE["all_clean"],
                      "g4_all_met": STATE["g4_probe"]["all_met"], "d76_all_met": STATE["d76_probe"]["all_met"],
                      "final_nodes": {k: v["verdict"] for k, v in STATE["final_node_runs"].items()},
                      "per": [{"ref": p["ref"].split("/")[-1], "sha": p["sha"], "root_is_tip": p["chain_root_is_tip"],
                               "conflicts": p["merge_tree"]["conflict_names"],
                               "tree": p["merge_tree"]["tree"], "own": len(p["own_paths"]),
                               "foreign": len(p["foreign_paths"])} for p in preds]}, ensure_ascii=False))
    return 0 if STATE["all_clean"] else 7


raise SystemExit(main())
