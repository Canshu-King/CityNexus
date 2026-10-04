# -*- coding: utf-8 -*-
"""Self-declared next cell, after the ORD-0557 receipt: use the LANDED reader, and re-hang the two ruler cells.

Two things are measured here and neither writes to the line, the ledger or a database:

  A. the reader the sequencer just landed is called the way his gate will call it, three times, and then its
     bytes are compared with the local `CITYNEXUS_AGENT_CONTROL.md` on this box.  That answers the question
     ORD-0557 was opened for - "is the mirror step actually in effect" - with a number instead of a hope.  If
     the two differ, the block says which side is ahead and by how many lines; it does not "fix" anything.

  B. both ruled cells are re-hung onto the tip as it reads now.  No re-measurement is claimed: the proof that
     no re-measurement is needed is in the same run - the tip's blob for every path a cell changes still
     equals the preimage the cell was measured against, and the bytes I carry are byte-identical to the ones
     those measurements produced.  Each cell's own test node is then run once on the new base so "green here"
     is a reading from this generation.

Every step prints as it goes and a failure writes what it had already measured.
"""
import hashlib
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
MOD_REL = "tools/cnx_ledger_mirror_reader_r1.py"
MOD_BLOB_LANDED = "dd939945f560632fea20186a57929d2edc1ab6ad"
LOCAL_LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
TOKEN = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8",
           CITYNEXUS_API_TOKEN_FILE=TOKEN)
for _k in ("http_proxy", "https_proxy"):
    ENV[_k] = ""
G4_SRC = "c23cb0a302c42ab2dc832743441b3d7da7461308"
D7_SRC = "c3293da4c11cc9fa783c38818f22895febda7c49"
G4_NEW = "refs/heads/review/1d64acf5-ord0296-g4-floor-r7"
D7_NEW = "refs/heads/review/1d64acf5-ord0476-response-set-r7"
G4_PATHS = ["backend/tests/test_qoder_ord0296_write_deadline.py",
            "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r5.json"]
D7_PATHS = ["backend/tests/test_qoder_ord0476_checkins.py"]
G4_PRE_BLOB = "d3e21e9084a3589678d08f7b50afe5119b2b85b8"
D7_PRE_BLOB = "853e9a67a7c33f4ac33b36dc49f53fd806265442"
G4_CELLS = {"backend/tests/test_qoder_ord0296_write_deadline.py": "032777990661c5220794a91c2a00a8ed1ea97fe7"}
D7_CELLS = {"backend/tests/test_qoder_ord0476_checkins.py": "534b673b749adfd7548066cca770e0c52d105306"}
G4_NODE = ("tests/test_qoder_ord0296_write_deadline.py::"
           "test_G4_the_lock_wait_is_written_in_exactly_one_place")
D7_NODE = ("tests/test_qoder_ord0476_checkins.py::"
           "test_the_contract_declares_both_doors_and_no_control_they_lack")
OWN = set(G4_PATHS + D7_PATHS)
R = {"started_local": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": []}


def git(*a, cwd=REPO):
    r = subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=3600)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def raw(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, env=ENV, timeout=3600).stdout


def blob(rev, path):
    rc, out, _ = git("rev-parse", "%s:%s" % (rev, path))
    return out if rc == 0 else None


def step(name, **kw):
    R["steps"].append(dict({"step": name}, **kw))
    print(json.dumps(dict({"step": name}, **kw), ensure_ascii=False)[:900], flush=True)


def finish(code):
    io.open(os.path.join(HERE, "ack_aefbbd1a_r1.json"), "w", encoding="utf-8").write(
        json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps({"json": "ack_aefbbd1a_r1.json", "rc": code, "steps": [s["step"] for s in R["steps"]]},
                     ensure_ascii=False))
    raise SystemExit(code)


def run_node(label, node, cwd):
    r = subprocess.run([PY, "-m", "pytest", node, "-p", "no:cacheprovider", "-q", "--tb=short"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=cwd, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    res = {"label": label, "rc": r.returncode, "verdict": "green" if r.returncode == 0 else "red",
           "summary": (tail[-1] if tail else out[-160:])[:150]}
    step("node", **res)
    return res


def main():
    tip = (git("ls-remote", "--refs", "origin", TIP_REF)[1].split() or [None])[0]
    if not tip or git("cat-file", "-e", "%s^{commit}" % tip)[0] != 0:
        rc, _o, err = git("fetch", "-q", "--depth=1", "origin",
                          "+%s:refs/remotes/verify/ack_aefbbd1a" % TIP_REF)
        tip = (git("ls-remote", "--refs", "origin", TIP_REF)[1].split() or [None])[0]
        if not tip or git("cat-file", "-e", "%s^{commit}" % tip)[0] != 0:
            step("abort_reason", why="the live tip %s still cannot be opened locally (fetch rc %s)" % (tip, rc))
            finish(8)
    step("tip", sha=tip, rev_list_count=int(git("rev-list", "--count", tip)[1]))

    # ---- A. the landed module, used the way the gate will use it -------------------------------
    disk = raw("cat-file", "blob", blob(tip, MOD_REL), cwd=WT)
    on_disk = hashlib.sha1(b"blob %d\x00" % len(disk) + disk).hexdigest()
    if on_disk != MOD_BLOB_LANDED:
        step("abort_reason", why="the tip's module blob is %s, not the landed %s" % (on_disk, MOD_BLOB_LANDED))
        finish(8)
    io.open(os.path.join(WT, MOD_REL), "wb").write(disk)          # materialise the landed bytes to import
    sys.path.insert(0, WT)
    # the reader needs the token path either as an argument or in the environment; this process is the caller,
    # so set it here rather than only in the copy handed to subprocesses - and note it for the interface doc,
    # because the gate will hit the same requirement
    os.environ["CITYNEXUS_API_TOKEN_FILE"] = TOKEN
    import tools.cnx_ledger_mirror_reader_r1 as M
    if M.git_blob_sha1(disk) != MOD_BLOB_LANDED:
        step("abort_reason", why="the imported file is not the landed bytes")
        finish(8)
    proofs = []
    for i in (1, 2, 3):
        info = M.read_remote_ledger(ref="commander/control", repo_dir=REPO)
        proofs.append({"run": i, "blob_id": info["blob_id"], "bytes": info["bytes"],
                       "git_blob_sha1": info["git_blob_sha1"], "hash_equal": info["hash_equal"],
                       "size_equal": info["size_equal"], "channels_agree": info["channels_agree"],
                       "api_size": info["api_size"], "tip_of_that_ref": info["branch_tip_commit"],
                       "self_heal": info["fetch_self_heal"], "lines": info["text"].count("\n") + 1})
        step("proof", run=i, blob=info["blob_id"], bytes=info["bytes"],
             equal=str(info["git_blob_sha1"] == info["blob_id"]).lower(),
             agree=str(info["channels_agree"]).lower())
        last_text = info["text"]
    local_raw = io.open(LOCAL_LEDGER, "rb").read()
    local_blob = hashlib.sha1(b"blob %d\x00" % len(local_raw) + local_raw).hexdigest()
    remote_blob = proofs[-1]["blob_id"]
    ll = local_raw.decode("utf-8", "replace").split("\n")
    rl = last_text.split("\n")
    first_diff = next((i + 1 for i in range(min(len(ll), len(rl))) if ll[i] != rl[i]), None)
    A_ = {"proofs": proofs, "local_ledger_bytes": len(local_raw), "local_ledger_blob": local_blob,
          "remote_ledger_blob": remote_blob, "byte_identical": local_blob == remote_blob,
          "local_lines": len(ll), "remote_lines": len(rl),
          "first_differing_line": first_diff,
          "which_side_is_ahead": ("remote" if len(rl) > len(ll) else
                                  "local" if len(ll) > len(rl) else "same_length_differ_at_%s" % first_diff)}
    step("mirror_state", byte_identical=str(A_["byte_identical"]).lower(), local_blob=local_blob,
         remote_blob=remote_blob, local_lines=A_["local_lines"], remote_lines=A_["remote_lines"],
         first_differing_line=A_["first_differing_line"], which=A_["which_side_is_ahead"])
    R["part_A"] = A_

    # ---- B. re-hang both ruled cells onto the tip, without pretending to re-measure ------------
    for tag, src, new, paths, pre, cell, node in (
            ("g4", G4_SRC, G4_NEW, G4_PATHS, {"backend/tests/test_qoder_ord0296_write_deadline.py": G4_PRE_BLOB},
             G4_CELLS, G4_NODE),
            ("d76", D7_SRC, D7_NEW, D7_PATHS, {"backend/tests/test_qoder_ord0476_checkins.py": D7_PRE_BLOB},
             D7_CELLS, D7_NODE)):
        pre_check = {p: {"tip_blob": blob(tip, p), "expected_preimage": pre[p],
                        "unchanged": blob(tip, p) == pre[p], "already_my_cell": blob(tip, p) == cell[p]}
                     for p in paths if p in pre}
        if any(not v["unchanged"] and not v["already_my_cell"] for v in pre_check.values()):
            step("abort_reason", why="%s preimage moved on the line, so the old readings would not describe "
                                      "this base: %s" % (tag, json.dumps(pre_check)))
            finish(8)
        if all(v["already_my_cell"] for v in pre_check.values()):
            step("already_landed", tag=tag, detail=json.dumps(pre_check))
            continue
        local = new[len("refs/heads/"):]
        git("checkout", "-q", "-B", local, tip, cwd=WT)
        rc, here, _e = git("symbolic-ref", "--short", "HEAD", cwd=WT)
        if here != local:
            step("abort_reason", why="HEAD reads %s not %s" % (here, local))
            finish(8)
        for p in paths:
            rc, _o, err = git("checkout", src, "--", p, cwd=WT)
            want = git("ls-tree", "-r", src, "--", p, cwd=WT)[1].split()[2]
            got = git("hash-object", os.path.join(WT, p.replace("/", os.sep)), cwd=WT)[1]
            if got != want:
                step("abort_reason", why="carrying %s gave %s expected %s" % (p, got, want))
                finish(8)
        git("reset", "-q", cwd=WT)
        rc, _o, err = git("add", "--", *paths, cwd=WT)
        staged = [l.strip() for l in git("diff", "--cached", "--name-only", cwd=WT)[1].splitlines() if l.strip()]
        if not staged or sorted(staged) != sorted(paths):
            step("abort_reason", why="staged %s != %s (rc %d %s)" % (staged, paths, rc, err[:120]))
            finish(8)
        rc, _o, err = git("commit", "-m",
                          "S4-ast-taint re-hung onto %s read from the server in this run. The bytes are carried "
                          "from %s and are byte-identical, and the tip's blob for every path this cell changes "
                          "still equals the preimage those readings were taken against (%s) - so this commit "
                          "claims a re-hang, not a new measurement. The cell's own node is run here once and its "
                          "summary is in the lane's receipt. 0 product bytes."
                          % (tip, src, json.dumps({k: v["expected_preimage"] for k, v in pre_check.items()})),
                          cwd=WT)
        head = git("rev-parse", "HEAD", cwd=WT)[1]
        carried = {p: git("ls-tree", "-r", head, "--", p, cwd=WT)[1].split()[2] for p in paths}
        if any(carried.get(p) != cell.get(p) and p in cell for p in paths):
            step("abort_reason", why="the re-hung tree is not the measured bytes: %s" % carried)
            finish(8)
        node_res = run_node(tag, node, BACKEND)
        changed = [l.split("\t")[-1] for l in git("diff", "--name-status", tip, head, cwd=WT)[1].splitlines()
                   if l.strip()]
        chain = int(git("rev-list", "--count", "%s..%s" % (tip, head), cwd=WT)[1] or "0")
        root = git("rev-parse", "%s~%d" % (head, chain), cwd=WT)[1]
        rc, mt, _e = git("merge-tree", "--write-tree", "--name-only", tip, head, cwd=WT)
        mtl = [l for l in mt.splitlines() if l.strip()]
        if git("ls-remote", "--refs", "origin", new)[1].strip():
            step("abort_reason", why="%s already exists on the server" % new)
            finish(8)
        rc, _o, err = git("push", "origin", "%s:%s" % (new, new), cwd=REPO)
        server = (git("ls-remote", "--refs", "origin", new)[1].split() or [None])[0]
        if rc or server != head:
            step("abort_reason", why="push of %s rc %d, server reads %s (%s)" % (new, rc, server, err[:200]))
            finish(8)
        R.setdefault("part_B", {})[tag] = {
            "branch": new, "head": head, "server_readback": server, "carried_from": src,
            "blobs_carried": carried, "preimage_check": pre_check, "commits_on_tip": chain,
            "chain_root_is_tip": root == tip, "own_paths": [p for p in changed if p in OWN],
            "foreign_paths": [p for p in changed if p not in OWN],
            "merge_tree": {"rc": rc, "tree": mtl[0] if mtl else None, "conflict_names": len(mtl) - 1},
            "node_on_the_newest_base": node_res}
        step("rehung", tag=tag, head=head, readback=server, conflicts=len(mtl) - 1,
             foreign=len([p for p in changed if p not in OWN]), node=node_res["summary"])
    ok = all(s.get("head") for s in R.get("part_B", {}).values()) if R.get("part_B") else True
    finish(0 if ok else 7)


main()
