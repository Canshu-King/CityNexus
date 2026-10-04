# -*- coding: utf-8 -*-
"""ORD-0557 build: prove the new tools/ reader from OUTSIDE the repo, then cut it onto the live tip and push.

Order of operations matters here and each step refuses rather than assuming:
  1. read the authoritative tip off the server and prove that sha is a local commit;
  2. re-cut this lane's branch for the order onto that tip (the module is untracked until committed, so the
     checkout cannot stomp it);
  3. import the module the way the gate would - a different working directory, the repo root pushed onto
     sys.path, no `tools/__init__.py` assumed - and prove the function it hands back actually returns a whole
     ledger that hashes to the remote blob;
  4. run the self-test: three proofs plus every counter-arm, which must refuse;
  5. commit exactly one path, push a NEW ref name, and read the sha back off the server.
"""
import ast
import hashlib
import io
import json
import os
import subprocess
import sys
import time

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
MODULE_REL = "tools/cnx_ledger_mirror_reader_r1.py"
BRANCH = "refs/heads/review/1d64acf5-ord0557-mirror-read-r1"
LOCAL = BRANCH[len("refs/heads/"):]
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
TOKEN = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8",
           CITYNEXUS_API_TOKEN_FILE=TOKEN)
for _k in ("http_proxy", "https_proxy"):
    ENV[_k] = ""
OUT = os.path.join(HERE, "ord0557_proof_r1.json")


def git(*a, cwd=REPO):
    r = subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=3600)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def step(name, **kw):
    print(json.dumps(dict({"step": name}, **kw), ensure_ascii=False), flush=True)


def abort(why):
    step("ABORT", reason=str(why)[:700])
    raise SystemExit(8)


def api_json(path):
    """A read straight off GitHub, because the local clone cannot open the commit the server calls the tip."""
    import urllib.request
    tok = io.open(TOKEN, encoding="utf-8").read().strip()
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok, "User-Agent":
                                          "cnx-ord0557-build-r1", "Accept": "application/vnd.github+json"})
    with op.open(req, timeout=600) as r:
        return r.status, json.loads(r.read())


def read_tip():
    """The tip as the server names it, and the newest commit this box can actually open.

    Measured on this run, and the reason the two can differ: `D:/moodle/CityNexus` is a shallow clone whose
    remote-tracking ref for the authoritative branch points at a commit that is NOT in its object store -
    `cat-file -t` rc 128 - while `git fetch` reports success because the negotiation advertises that same ref
    as already have.  Repairing it means either dropping the broken tracking ref (shared with other lanes, so
    not mine to touch) or a `--refetch`, which died mid-pack on this link (`Connection reset by peer`).
    So the hand is cut onto the commit the server itself names as the tip's parent, and the gap is reported
    with numbers instead of being papered over.
    """
    rc, ls, err = git("ls-remote", "--refs", "origin", TIP_REF)
    tip = ls.split()[0] if ls else None
    if not tip:
        abort("no tip from the server: %s" % err[:160])
    track = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
    if git("cat-file", "-e", "%s^{commit}" % tip)[0] != 0:
        git("fetch", "-q", "--depth=1", "origin", "+%s:%s" % (TIP_REF, track))
    if git("cat-file", "-e", "%s^{commit}" % tip)[0] == 0:
        return tip, tip, {"tip_objects_local": True}
    status, commit = api_json("/repos/%s/commits/%s" % ("Canshu-King/CityNexus", tip))
    parents = [p["sha"] for p in commit.get("parents", [])]
    base = parents[0] if parents and git("cat-file", "-e", "%s^{commit}" % parents[0])[0] == 0 else None
    if not base:
        abort("neither the tip %s nor its parent %s can be opened here (api %s) - this box's clone needs a "
              "repair before any lane can cut on the line" % (tip, parents, status))
    gap = {"tip_objects_local": False, "tip_named_by_server": tip,
           "api_status_for_tip_commit": status, "tip_parents_from_server": parents,
           "base_used": base, "base_is_the_tip_parent": True,
           "fetch_forms_tried_locally": ["+refs/heads/<tip>:refs/remotes/origin/<track>",
                                         "+refs/heads/<tip>:refs/remotes/verify/ord0557_tipfix",
                                         "git fetch --depth=1 origin <sha>",
                                         "git fetch --refetch --depth=1 (died: client_loop: send disconnect: "
                                         "Connection reset by peer / early EOF)"],
           "why_fetch_returns_success_without_objects": "the broken remote-tracking ref advertises the missing "
                                                        "sha as `have`, so the server sends no pack",
           "not_touched": "refs/remotes/origin/mirror/integration-frontend-apple-pass1 was left as it is - it "
                          "belongs to the shared clone and other lanes read it"}
    return tip, base, gap


def main():
    live_tip, tip, gap = read_tip()
    step("tip", live=live_tip, base_cut_on=tip, gap=gap)
    src = io.open(os.path.join(WT, MODULE_REL), encoding="utf-8").read()
    ast.parse(src)
    bytes_local = len(src.encode("utf-8"))
    sha_local = hashlib.sha1(b"blob %d\x00" % bytes_local + src.encode("utf-8")).hexdigest()
    if git("cat-file", "-e", tip + ":" + MODULE_REL)[0] == 0:
        abort("%s already exists on the line - this hand must not overwrite a landed path" % MODULE_REL)
    step("module_linted", path=MODULE_REL, bytes=bytes_local, blob_if_committed=sha_local)

    rc, _o, err = git("checkout", "-q", "-B", LOCAL, tip, cwd=WT)
    if rc != 0:
        abort("checkout -B rc %d: %s" % (rc, err[:300]))
    here_rc, here, _e = git("symbolic-ref", "--short", "HEAD", cwd=WT)
    if here != LOCAL:
        abort("HEAD reads %s, not %s" % (here, LOCAL))

    # 3. import the way the gate will: neutral cwd, repo root on sys.path, no package file assumed
    probe_tpl = (
        "import sys, os, hashlib\n"
        "sys.path.insert(0, '@@WT@@')\n"
        "os.chdir('@@HERE@@')\n"
        "from tools.cnx_ledger_mirror_reader_r1 import read_remote_ledger, IncompleteRemoteRead, "
        "git_blob_sha1\n"
        "info = read_remote_ledger()\n"
        "text = info['text']\n"
        "print('IMPORT_OK from', os.getcwd(), 'via', sys.path[0])\n"
        "print('blob', info['blob_id'], 'bytes', info['bytes'], 'recomputed', info['git_blob_sha1'],\n"
        "      'equal', info['git_blob_sha1'] == info['blob_id'], 'agree', info['channels_agree'])\n"
        "enc = text.encode('utf-8')\n"
        "print('text round-trip', git_blob_sha1(enc) == info['blob_id'], 'lines', text.count(chr(10)) + 1)\n")
    probe = probe_tpl.replace("@@WT@@", WT).replace("@@HERE@@", HERE)
    if "%d" in probe_tpl or "%r" in probe_tpl:
        abort("the import probe template carries a stray format sign again - use tokens, not %")
    p = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=3600)
    step("import_from_outside", rc=p.returncode, out=(p.stdout or "").strip()[-700:],
         err=(p.stderr or "").strip()[-300:])
    if p.returncode != 0:
        abort("the gate's import shape does not work: %s" % (p.stderr or "")[-400:])

    # 4. the self-proof and the counter-arms, run through the module's own CLI
    q = subprocess.run([sys.executable, os.path.join(WT, MODULE_REL), "--self-test", "--runs", "3",
                        "--out", OUT], capture_output=True, text=True, encoding="utf-8",
                       env=ENV, cwd=HERE, timeout=3600)
    qout = (q.stdout or "") + (q.stderr or "")
    step("self_test", rc=q.returncode, tail=qout.strip().splitlines()[-1][:400] if qout.strip() else "")
    if q.returncode != 0:
        abort("self-test rc %d: %s" % (q.returncode, qout[-900:]))
    doc = json.load(io.open(OUT, encoding="utf-8"))
    proof = doc["proof"]
    if not (len(proof) == 3 and all(x["hash_equal"] and x["channels_agree"] and x["size_equal"]
                                    and x["text_hash_of_decoded"] for x in proof)):
        abort("three runs did not all come back proved: %s" % json.dumps(proof)[:500])
    arms = [c for c in doc["arms"] if c.get("refused") is not None]
    if any(c["refused"] is False for c in arms):
        abort("a counter-arm passed where it must refuse: %s" % json.dumps(arms)[:500])
    old = [c for c in doc["arms"] if c.get("arm") == "old_onshot_read"][0]

    # 5. commit exactly one path onto the named branch, push a new ref, read it back
    git("reset", "-q", cwd=WT)
    rc, _o, err = git("add", "--", MODULE_REL, cwd=WT)
    if rc != 0:
        abort("git add rc %d: %s" % (rc, err[:200]))
    staged = [l.strip() for l in git("diff", "--cached", "--name-only", cwd=WT)[1].splitlines() if l.strip()]
    if staged != [MODULE_REL]:
        abort("staged set is %s, this hand means exactly [%s]" % (staged, MODULE_REL))
    rc, _o, err = git("commit", "-m",
                      "S4-ast-taint ORD-0557: the mirror's remote read becomes an importable, self-proving "
                      "module. read_remote_ledger() returns bytes only when git transport, the blob id the "
                      "fetched tree names, and the GitHub contents route all agree on the same blob and the "
                      "same size; anything else raises IncompleteRemoteRead naming the leg. The route the "
                      "mirror used before (raw blob, read to EOF) is kept as a measured counter-arm because it "
                      "silently truncates. Run as a program it prints three proofs and refuses all three "
                      "counter-arms. No gate, ledger or database is touched by this file.",
                      cwd=WT)
    if rc != 0:
        abort("commit rc %d: %s" % (rc, err[:300]))
    head = git("rev-parse", "HEAD", cwd=WT)[1]
    if git("rev-parse", LOCAL, cwd=WT)[1] != head:
        abort("committed %s but the branch reads %s" % (head, git("rev-parse", LOCAL, cwd=WT)[1]))
    blob_in_commit = git("ls-tree", "-r", head, "--", MODULE_REL, cwd=WT)[1].split()[2]
    if blob_in_commit != sha_local:
        abort("the committed module is %s, the file I linted is %s" % (blob_in_commit, sha_local))
    rc, ls, _e = git("ls-remote", "--refs", "origin", BRANCH)
    if ls.strip():
        abort("%s already exists on the server at %s" % (BRANCH, ls.split()[0]))
    rc, _o, err = git("push", "origin", "%s:%s" % (BRANCH, BRANCH))
    if rc != 0:
        abort("push rc %d: %s" % (rc, err[:300]))
    server = (git("ls-remote", "--refs", "origin", BRANCH)[1].split() or [None])[0]
    if server != head:
        abort("pushed %s, server reads %s" % (head, server))
    changed = [l.split("\t")[-1] for l in git("diff", "--name-status", tip, head, cwd=WT)[1].splitlines()
               if l.strip()]
    chain = int(git("rev-list", "--count", "%s..%s" % (tip, head), cwd=WT)[1])
    root = git("rev-parse", "%s~%d" % (head, chain), cwd=WT)[1]
    rc, mt, _e = git("merge-tree", "--write-tree", "--name-only", tip, head, cwd=WT)
    mtl = [l for l in mt.splitlines() if l.strip()]

    summary = {"generated_at_local": time.strftime("%Y-%m-%d %H:%M:%S"), "tip": tip,
               "live_tip_named_by_server": live_tip, "tip_object_gap": gap,
               "branch": BRANCH, "head": head, "server_readback": server,
               "module_path": MODULE_REL, "module_bytes": bytes_local, "module_blob": sha_local,
               "commits_on_tip": chain, "chain_root": root, "chain_root_is_tip": root == tip,
               "paths_in_the_diff": changed, "own_paths": [p for p in changed if p == MODULE_REL],
               "foreign_paths": [p for p in changed if p != MODULE_REL],
               "merge_tree": {"rc": rc, "tree": mtl[0] if mtl else None, "conflict_names": len(mtl) - 1,
                              "clean": rc == 0 and len(mtl) == 1},
               "import_probe": {"rc": p.returncode, "out": (p.stdout or "").strip()},
               "old_route": {"attempts": old["attempts"], "any_complete": old["any_complete"],
                             "per_attempt": old["per_attempt"]},
               "arms": arms, "proof": proof, "read_of_record": doc["read_of_record"],
               "all_clean": bool(root == tip and mtl and len(mtl) == 1 and changed == [MODULE_REL]
                                 and server == head)}
    io.open(os.path.join(HERE, "ord0557_build_r1.json"), "w", encoding="utf-8").write(
        json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps({"json": "ord0557_build_r1.json", "tip": tip, "head": head, "blob": sha_local,
                      "proof": [(x["blob_id"], x["bytes"], x["git_blob_sha1"] == x["blob_id"],
                                 x["channels_agree"]) for x in proof],
                      "arms": [(c["arm"], c["refused"], c.get("leg")) for c in arms],
                      "old_route_attempts_short_by": [x["short_by"] for x in old["per_attempt"]],
                      "foreign": len(summary["foreign_paths"]),
                      "all_clean": summary["all_clean"]}, ensure_ascii=False))
    return 0 if summary["all_clean"] else 7


raise SystemExit(main())
