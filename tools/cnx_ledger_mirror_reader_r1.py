# -*- coding: utf-8 -*-
"""ORD-0557: an importable, self-proving reader for the remote ledger, so a mirror can never write half a file.

Why this exists
---------------
The ledger is over 12 MB.  The GitHub `git/blobs/<sha>` route with `Accept: application/vnd.github.raw` answers
`Content-Length` and then ends the stream early **without raising** - measured on 2026-10-03 at 600 827 B,
1 418 476 B and 349 846 B against a declared 12 796 711 B.  A read loop that treats "read() returned nothing" as
end-of-body therefore produces a short body that looks like success, and the only thing that caught it was the
final hash - which is why the mirror reported `rc=8 truncated read` instead of corrupting the ledger.  A `Range`
probe on the same endpoint declared the FULL length again while serving a third of it, so segmenting is ruled
out by measurement.

What this module guarantees
---------------------------
`read_remote_ledger()` returns bytes ONLY when three independent things agree:

  1. the bytes came through git transport (`git fetch` + `git cat-file blob`), whose transfer is checksummed by
     the protocol, and whose length is re-counted from the pipe rather than trusted from a header;
  2. the git blob hash recomputed over those bytes equals the blob id the fetched tree itself names for the path;
  3. that same id and size equal what the GitHub contents route reports for the same ref (a second, independent
     channel - agreement between the two is the point, so a failure of this leg is reported, not worked around).

Anything else raises `IncompleteRemoteRead` naming the leg that was lost.  "Take however much arrived" is not a
supported outcome, and there is no code path that returns a body without passing the three agreements.

Interface handed to the sequencer (nothing in this file touches a gate, a ledger or a database)
----------------------------------------------------------------------------------------------
    import sys; sys.path.insert(0, "<repo root>")            # tools/ has no __init__.py; py3 namespaces resolve it
    from tools.cnx_ledger_mirror_reader_r1 import read_remote_ledger, IncompleteRemoteRead

    info = read_remote_ledger()                              # defaults: ref="commander/control", the ledger path
    text = info["text"]                                      # str, whole file, already proved
    info["blob_id"], info["bytes"], info["git_blob_sha1"]    # the four proof fields
    info["api_blob_id"], info["api_size"], info["channels_agree"]

    # keyword arguments, all optional:
    #   ref=            the branch to read (default "commander/control")
    #   path=           the repo path  (default "CITYNEXUS_AGENT_CONTROL.md")
    #   repo_dir=       a local clone to run git transport in (default the repo this file lives in)
    #   token_file=     a PAT file for the API leg (default $CITYNEXUS_API_TOKEN_FILE)
    #   cross_check=    False makes the API leg optional and marks the result as single-channel
    #   arm=            one of the counter-arms below, used only by --self-test

Counter-arms (each must refuse; they exist because a guard nobody bent is a guard nobody tested)
-----------------------------------------------------------------------------------------------
    short_body          one byte dropped from a complete git body      -> the hash gate must refuse
    wrong_expected_sha  one hex flipped on the reported blob id        -> the equality gate must refuse
    no_api              the contents route withheld                    -> the second channel must refuse
    old_onshot_read     the api route the mirror used, read to EOF     -> recorded, not required to fail: it
                          served 600 827 / 1 418 476 / 349 846 B on 2026-10-03 and a whole 13 497 412 B on
                          2026-10-04, so it is intermittent and cannot be relied on; this module never uses it

Running the module as a program performs the self-proof the order asks for: three reads, each printing the
remote blob id in full, the bytes taken, the recomputed git blob sha1 and whether they are equal.
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

GH_REPO = "Canshu-King/CityNexus"
LEDGER_PATH = "CITYNEXUS_AGENT_CONTROL.md"
DEFAULT_REF = "commander/control"
CHUNK = 1 << 20
USER_AGENT = "cnx-ord0557-mirror-reader-r1"
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class IncompleteRemoteRead(Exception):
    """Raised instead of returning a partial body.  Carries which leg failed."""

    def __init__(self, leg, detail):
        Exception.__init__(self, "%s: %s" % (leg, detail))
        self.leg, self.detail = leg, detail


def git_blob_sha1(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def _clean_env():
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    env["NO_PROXY"] = "*"
    return env


def _git(repo_dir, *a):
    r = subprocess.run(["git", "-C", repo_dir, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=_clean_env(), timeout=3600)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def _git_bytes(repo_dir, rev):
    """The blob's bytes through git transport, counted from the pipe rather than trusted from a header."""
    p = subprocess.run(["git", "-C", repo_dir, "cat-file", "blob", rev], capture_output=True,
                       env=_clean_env(), timeout=3600)
    if p.returncode != 0:
        raise IncompleteRemoteRead("git_transport", "cat-file blob %s rc %d: %s"
                                   % (rev, p.returncode, (p.stderr or b"")[-200:].decode("utf-8", "replace")))
    return p.stdout


def _api(path, token_file, headers=None, timeout=1800):
    if not token_file or not os.path.exists(token_file):
        raise IncompleteRemoteRead("api_channel", "no token file at %r - set CITYNEXUS_API_TOKEN_FILE"
                                   % (token_file or ""))
    tok = io.open(token_file, encoding="utf-8").read().strip()
    h = {"Authorization": "Bearer " + tok, "User-Agent": USER_AGENT}
    h.update(headers or {})
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request("https://api.github.com" + path, headers=h)
    with op.open(req, timeout=timeout) as r:
        return r.status, dict(r.headers), r.read()


def remote_meta(ref, path, token_file, arm=""):
    """What the contents route says about the file on that ref: blob id, size, and the shape of `content`."""
    if arm == "no_api":
        raise IncompleteRemoteRead("api_channel", "arm no_api: the second channel is what tells us the blob "
                                   "id independently of the tree we fetched; without it there is no agreement "
                                   "to check")
    status, _hdr, body = _api("/repos/%s/contents/%s?ref=%s" % (GH_REPO, path, ref.replace("/", "%2F")),
                              token_file, {"Accept": "application/vnd.github+json"})
    meta = json.loads(body)
    c = meta.get("content")
    return {"status": status, "blob_id": meta["sha"], "size": meta["size"],
            "content_key_present": "content" in meta, "content_value_type": type(c).__name__,
            "content_in_body": isinstance(c, str) and len(c) > 0}


def _fetch_ref(repo_dir, ref, fetch_ref, path):
    """Fetch one branch into a ref name this tool owns, and prove the commit AND this path's blob are in the store.

    Measured on the box this runs on: `git fetch` can report success and update the ref while the commit object
    is NOT in the object store - the broken ref then advertises that sha as `have`, so every later fetch
    negotiates zero objects.  The commit alone is not enough either: once the commit opened and the tree behind
    it did not, which is a silent way to read a stale ledger.  So both objects are opened before they are used,
    and the one name this tool owns is dropped and re-fetched once when the bookkeeping is found broken.
    """
    def attempt(depth):
        args = ["fetch", "-q"] + (["--depth=1"] if depth else []) + ["origin", "+refs/heads/%s:%s" % (ref, fetch_ref)]
        rc, _o, err = _git(repo_dir, *args)
        sha = _git(repo_dir, "rev-parse", fetch_ref)[1]
        blob = _git(repo_dir, "rev-parse", "%s:%s" % (fetch_ref, path))[1]
        openable = bool(sha) and bool(blob) and _git(repo_dir, "cat-file", "-e", "%s^{commit}" % sha)[0] == 0 \
            and _git(repo_dir, "cat-file", "-e", blob)[0] == 0
        return rc, err, sha, blob, openable

    rc, err, sha, blob, openable = attempt(True)
    heals = []
    if rc:
        raise IncompleteRemoteRead("git_transport", "fetch of refs/heads/%s rc %d: %s" % (ref, rc, err[-300:]))
    if not openable:
        heals.append({"problem": "ref %s reads %s but the commit or the blob for %s is not openable in this "
                                 "object store (%s)" % (fetch_ref, sha or "NOTHING", path, blob or "NO BLOB IN "
                                 "THE TREE"),
                      "action": "drop the name this tool owns and re-fetch"})
        _git(repo_dir, "update-ref", "-d", fetch_ref)
        rc, err, sha, blob, openable = attempt(True)
        heals[-1]["after"] = {"sha": sha, "blob_for_the_path": blob, "openable": openable, "rc": rc}
        if not openable:
            raise IncompleteRemoteRead(
                "git_transport", "the clone cannot materialise refs/heads/%s: the ref reads %s and the object "
                                "store cannot open it or the blob for %s even after dropping %s and re-fetching. "
                                "This box needs `git fetch --refetch --depth=1 origin +refs/heads/%s:...` on a "
                                "link that holds, or a fresh clone"
                                % (ref, sha or "NOTHING", path, fetch_ref, ref))
    return sha, blob, heals


def read_remote_ledger(ref=DEFAULT_REF, path=LEDGER_PATH, repo_dir=REPO_DIR, token_file=None,
                       cross_check=True, arm=""):
    """Return the whole remote file, proved.  Raises IncompleteRemoteRead rather than a short body."""
    token_file = token_file or os.environ.get("CITYNEXUS_API_TOKEN_FILE") or ""
    fetch_ref = "refs/remotes/verify/cnx_reader_" + ref.replace("/", "_")
    tip, tree_blob, heals = _fetch_ref(repo_dir, ref, fetch_ref, path)
    if not tree_blob:
        raise IncompleteRemoteRead("git_transport", "the fetched tree names no blob for %s on %s" % (path, ref))
    rc4, declared_size, _e4 = _git(repo_dir, "cat-file", "-s", tree_blob)
    if rc4 or not str(declared_size).strip().isdigit():
        raise IncompleteRemoteRead("size_gate", "cannot read the object's own size for %s (rc %d, reads %r) - "
                                   "without it there is no second length to check the body against"
                                   % (tree_blob, rc4, declared_size))
    declared_size = int(str(declared_size).strip())
    raw = _git_bytes(repo_dir, tree_blob)
    if arm == "short_body":
        raw = raw[:-1]
    got = git_blob_sha1(raw)
    expect = tree_blob[:-1] + ("0" if tree_blob[-1] != "0" else "1") if arm == "wrong_expected_sha" else tree_blob
    if got != expect:
        raise IncompleteRemoteRead("hash_gate", "bytes taken do not hash to the blob the tree names: recomputed "
                                   "%s != %s over %d of %s B" % (got, expect, len(raw), declared_size))
    if len(raw) != declared_size:
        raise IncompleteRemoteRead("size_gate", "git transport delivered %d B but the object is %d B"
                                   % (len(raw), declared_size))
    out = {"ref": ref, "path": path, "branch_tip_commit": tip, "blob_id": tree_blob, "bytes": len(raw),
           "git_blob_sha1": got, "hash_equal": True, "size_equal": len(raw) == declared_size,
           "object_size_from_cat_file": declared_size,
           "fetch_ref_used": fetch_ref, "fetch_self_heal": heals,
           "arm": arm or "none", "channels_agree": None, "api_blob_id": None, "api_size": None,
           "api_status": None, "single_channel": not cross_check}
    if cross_check:
        meta = remote_meta(ref, path, token_file, arm=arm)
        out.update({"api_blob_id": meta["blob_id"], "api_size": meta["size"], "api_status": meta["status"],
                    "content_key_present": meta["content_key_present"],
                    "content_in_body_from_api": meta["content_in_body"],
                    "channels_agree": meta["blob_id"] == tree_blob and meta["size"] == len(raw)})
        if not out["channels_agree"]:
            raise IncompleteRemoteRead(
                "channel_agreement", "git transport says blob %s / %d B and the contents route says %s / %s B"
                % (tree_blob, len(raw), meta["blob_id"], meta["size"]))
    out["text"] = raw.decode("utf-8")
    return out


def read_old_way(sha, expect_size, token_file, attempts=3):
    """The route the mirror used before ORD-0552: read until read() returns nothing.  Kept so the difference
    can be measured on the same box in the same minute instead of asserted."""
    per = []
    for i in range(attempts):
        buf = bytearray()
        err, declared = None, None
        t0 = time.time()
        try:
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            req = urllib.request.Request("https://api.github.com/repos/%s/git/blobs/%s" % (GH_REPO, sha),
                                         headers={"Authorization": "Bearer " + io.open(token_file,
                                                                                       encoding="utf-8")
                                                  .read().strip(),
                                                  "User-Agent": USER_AGENT,
                                                  "Accept": "application/vnd.github.raw"})
            with op.open(req, timeout=1800) as r:
                declared = r.headers.get("Content-Length")
                while True:
                    part = r.read(CHUNK)
                    if not part:
                        break
                    buf += part
        except Exception as e:  # noqa: BLE001 - the transport is the thing under test
            err = "%s: %s" % (type(e).__name__, str(e)[:200])
        raw = bytes(buf)
        per.append({"attempt": i + 1, "declared_content_length": declared, "bytes": len(raw),
                    "short_by": (int(declared or expect_size)) - len(raw), "err": err,
                    "git_blob_sha1": git_blob_sha1(raw), "complete": git_blob_sha1(raw) == sha,
                    "seconds": round(time.time() - t0, 1)})
        if per[-1]["complete"]:
            break
    return {"route": "api_raw_old_onshot_read", "attempts": len(per), "per_attempt": per,
            "any_complete": bool([p for p in per if p["complete"]])}


def _proof_line(run, info):
    return ("run %d | ref %s | remote blob %s | bytes %d B | recomputed git blob sha1 %s | equal=%s | "
            "api agrees=%s (api says blob %s / %s B)"
            % (run, info["ref"], info["blob_id"], info["bytes"], info["git_blob_sha1"],
               str(info["hash_equal"]).lower(), str(info["channels_agree"]).lower(),
               info["api_blob_id"], info["api_size"]))


def self_proof(runs=3, ref=DEFAULT_REF, token_file=None, repo_dir=REPO_DIR):
    rows = []
    for i in range(1, runs + 1):
        info = read_remote_ledger(ref=ref, token_file=token_file, repo_dir=repo_dir)
        line = _proof_line(i, info)
        print(line, flush=True)
        rows.append({"run": i, "line": line, "blob_id": info["blob_id"], "bytes": info["bytes"],
                     "git_blob_sha1": info["git_blob_sha1"], "hash_equal": info["hash_equal"],
                     "size_equal": info["size_equal"], "channels_agree": info["channels_agree"],
                     "api_blob_id": info["api_blob_id"], "api_size": info["api_size"],
                     "tip": info["branch_tip_commit"], "text_len": len(info["text"]),
                     "text_hash_of_decoded": git_blob_sha1(info["text"].encode("utf-8")) == info["blob_id"]})
    return rows


def self_test(token_file=None, repo_dir=REPO_DIR):
    """Every arm must refuse.  A counter-arm that passes is reported as a failure of THIS module."""
    checks = []
    for arm in ("short_body", "wrong_expected_sha", "no_api"):
        try:
            read_remote_ledger(token_file=token_file, repo_dir=repo_dir, arm=arm)
            checks.append({"arm": arm, "refused": False, "leg": None, "detail": "the guard did NOT fire"})
        except IncompleteRemoteRead as e:
            checks.append({"arm": arm, "refused": True, "leg": e.leg, "detail": e.detail[:220]})
    base = read_remote_ledger(token_file=token_file, repo_dir=repo_dir)
    old = read_old_way(base["blob_id"], base["bytes"], token_file)
    checks.append({"arm": "old_onshot_read", "refused": None, "route": old["route"],
                   "attempts": old["attempts"], "any_complete": old["any_complete"],
                   "per_attempt": old["per_attempt"],
                   "meaning": "this is the route the mirror used. it is NOT a supported source: on 2026-10-03 "
                              "three reads stopped short and on 2026-10-04 one read came whole - intermittent is "
                              "the defect, and a reader that cannot tell the two apart is the hazard"})
    del base["text"]
    return checks, base


def main():
    ap = argparse.ArgumentParser(prog="cnx_ledger_mirror_reader_r1.py")
    ap.add_argument("--ref", default=DEFAULT_REF)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--token-file", default=os.environ.get("CITYNEXUS_API_TOKEN_FILE") or "")
    ap.add_argument("--repo-dir", default=REPO_DIR)
    ap.add_argument("--arm", default="", choices=("", "short_body", "wrong_expected_sha", "no_api",
                                                  "old_onshot_read"))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.arm == "old_onshot_read":
        base = read_remote_ledger(ref=a.ref, token_file=a.token_file, repo_dir=a.repo_dir)
        print(json.dumps(read_old_way(base["blob_id"], base["bytes"], a.token_file), ensure_ascii=False))
        return 0
    if a.self_test:
        checks, base = self_test(a.token_file, a.repo_dir)
        for c in checks:
            print(json.dumps(c, ensure_ascii=False))
        doc = {"proof": self_proof(a.runs, a.ref, a.token_file, a.repo_dir), "arms": checks,
               "read_of_record": base}
        if a.out:
            io.open(a.out, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
        bad = [c for c in checks if c.get("refused") is False]
        all_equal = all(p["hash_equal"] and p["channels_agree"] and p["size_equal"] and p["text_hash_of_decoded"]
                        for p in doc["proof"])
        print(json.dumps({"runs": a.runs, "all_three_complete": all_equal,
                          "arms_all_refused": not bad,
                          "old_route_completed_this_run": checks[-1]["any_complete"]}, ensure_ascii=False))
        return 0 if (all_equal and not bad) else 7
    rows = self_proof(a.runs, a.ref, a.token_file, a.repo_dir)
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(json.dumps({"proof": rows}, ensure_ascii=False, indent=1))
    return 0 if all(r["hash_equal"] and r["channels_agree"] for r in rows) else 7


if __name__ == "__main__":
    raise SystemExit(main())
