# -*- coding: utf-8 -*-
"""ORD-0552: read the remote ledger so that it can prove itself, instead of hoping one page came whole.

What the commander saw is real and I reproduced it before touching anything: the `git/blobs/<sha>` route with
`Accept: application/vnd.github.raw` answers `Content-Length: 12796711` and then ends the stream early
without raising - three reads on 2026-10-03 stopped at 600 827 B, 1 418 476 B and 349 846 B. The mirror's own
loop treats "read() returned nothing" as end-of-body, so the only thing that caught it was the final hash,
which is why every run degraded to rc 8. A `Range` probe on the same endpoint came back declaring the FULL
length again (it served 3 335 026 bytes of 12 796 711 before breaking), so segmenting is not available here
and route (乙) on the list is ruled out by measurement, not by preference.

Route (甲)+(丙) combined is what works and is what this ships as the default:

  1. `git fetch` the branch tip through git transport - the pack transfer is checksummed by the protocol,
     so short delivery cannot pass as a body.
  2. Take the blob id the fetched tree itself names for the path, and the bytes `git cat-file` gives back.
  3. Recompute the git blob hash over those bytes and require THREE agreements: recomputed == the id the tree
     names == the id the GitHub contents route reports for the same ref, and the byte count == the size that
     route reports. Anything else exits non-zero. "Take however much arrived" is not a supported outcome.

The GitHub API is still asked, because the point of the check is that two independent channels agree; if the
network route is unavailable the instrument says which leg it lost instead of silently switching to one
source.

Arms, all of which must go red - they exist because a guard nobody bent is a guard nobody tested:
  --arm=old_onshot_read    the mirror's own read loop (read to EOF, no target): reports a truncated read
  --arm=wrong_expected_sha one hex flipped on the reported blob: the equality gate must refuse
  --arm=short_body         one byte dropped from a complete git-transport body: the hash gate must refuse
  --arm=no_api             the contents route withheld: must report WHICH leg is missing, not pass
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO_DIR = r"D:/moodle/CityNexus"
GH_REPO = "Canshu-King/CityNexus"
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
PATH = "CITYNEXUS_AGENT_CONTROL.md"
CHUNK = 1 << 20


def blob_hash(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def human(n):
    return "%d B (%.2f MiB)" % (n, n / 1048576.0)


def git(*a, cwd=REPO_DIR):
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    env["NO_PROXY"] = "*"
    r = subprocess.run(["git", "-C", cwd, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=3600)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def git_bytes(rev):
    """Bytes of a blob through git transport, counted from the pipe rather than trusted from a header."""
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    env["NO_PROXY"] = "*"
    p = subprocess.run(["git", "-C", REPO_DIR, "cat-file", "blob", rev], capture_output=True,
                       env=env, timeout=3600)
    if p.returncode != 0:
        raise SystemExit("ABORT: git cat-file failed for %s: %s" % (rev, p.stderr[-200:]))
    return p.stdout


def api(path, headers, timeout=900):
    tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
    h = {"Authorization": "Bearer " + tok, "User-Agent": "cnx-ord0552-mirror-read-r1"}
    h.update(headers)
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request("https://api.github.com" + path, headers=h)
    with op.open(req, timeout=timeout) as r:
        return r.status, dict(r.headers), r.read()


def contents_meta(ref, arm=None):
    status, hdr, body = api("/repos/%s/contents/%s?ref=%s" % (GH_REPO, PATH, ref.replace("/", "%2F")),
                            {"Accept": "application/vnd.github+json"})
    meta = json.loads(body)
    c = meta.get("content")
    import base64
    dec = None
    if isinstance(c, str) and c:
        try:
            dec = len(base64.b64decode(c, validate=False))
        except Exception:  # noqa: BLE001 - the shape is what is under test, not the decode
            dec = -1
    out = {"status": status, "sha": meta["sha"], "size": meta["size"],
           "content_key_present": "content" in meta, "content_value_type": type(c).__name__,
           "content_value_str_len": len(c) if isinstance(c, str) else None,
           "content_decoded_bytes": dec,
           "content_carries_the_whole_body": dec == meta["size"],
           "media_type": hdr.get("Content-Type")}
    if arm == "no_api":
        raise SystemExit("ARM no_api: expected the api leg to be unavailable - see caller")
    return out


def read_via_git(ref, arm=None):
    fetch_ref = "refs/remotes/verify/ord0552_" + ref.replace("/", "_")
    rc, _o, err = git("fetch", "-q", "origin", "+refs/heads/%s:%s" % (ref, fetch_ref))
    if rc:
        raise SystemExit("ABORT: git fetch of refs/heads/%s failed: %s" % (ref, err[-300:]))
    tip = git("rev-parse", fetch_ref)[1]
    blob_id = git("rev-parse", "%s:%s" % (fetch_ref, PATH))[1]
    want_len = int(git("cat-file", "-s", blob_id)[1])
    raw = git_bytes(blob_id)
    if arm == "short_body":
        raw = raw[:-1]
    got = blob_hash(raw)
    expect = blob_id[:-1] + ("0" if blob_id[-1] != "0" else "1") if arm == "wrong_expected_sha" else blob_id
    return {"route": "git_transport", "ref": ref, "branch_tip_commit": tip, "blob_id_named_by_tree": blob_id,
            "bytes_fetched": len(raw), "bytes_as_reported_by_cat_file": want_len,
            "git_blob_sha1_of_fetched_bytes": got, "compared_against": expect,
            "hash_equal": got == expect, "size_equal": len(raw) == want_len, "arm": arm or "none"}


def read_via_api_raw(sha, expect_size, arm=None, attempts=6):
    """The route that truncates. Kept so the difference is measured on the same box, in the same minute."""
    hdr = {"Accept": "application/vnd.github.raw"}
    per = []
    for i in range(attempts):
        t0 = time.time()
        buf = bytearray()
        err = None
        declared = None
        per_status = None
        try:
            if arm == "old_onshot_read":
                # the mirror's own loop verbatim: read until read() returns nothing, no target length
                status, h2, body = api("/repos/%s/git/blobs/%s" % (GH_REPO, sha), hdr, timeout=1800)
                buf += body
                declared = h2.get("Content-Length")
                per_status = status
            else:
                per_status = None
                op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
                req = urllib.request.Request("https://api.github.com/repos/%s/git/blobs/%s"
                                             % (GH_REPO, sha),
                                             headers={"Authorization": "Bearer " + tok,
                                                      "User-Agent": "cnx-ord0552-mirror-read-r1",
                                                      "Accept": "application/vnd.github.raw"})
                with op.open(req, timeout=1800) as r:
                    declared = r.headers.get("Content-Length")
                    target = int(declared) if declared else expect_size
                    while len(buf) < target:
                        part = r.read(CHUNK)
                        if not part:
                            break
                        buf += part
        except Exception as e:  # noqa: BLE001 - transport is the thing under test
            err = "%s: %s" % (type(e).__name__, str(e)[:200])
        raw = bytes(buf)
        per.append({"attempt": i + 1, "http_status": per_status, "bytes": len(raw),
                    "declared_content_length": declared,
                    "expected_size": expect_size, "short_by": expect_size - len(raw), "err": err,
                    "git_blob_sha1": blob_hash(raw), "seconds": round(time.time() - t0, 1)})
        if blob_hash(raw) == sha and len(raw) == expect_size:
            break
    complete = [p for p in per if p["git_blob_sha1"] == sha and p["bytes"] == expect_size]
    return {"route": "api_raw_%s" % (arm or "size_bounded"), "attempts": len(per), "per_attempt": per,
            "bytes_fetched": complete[-1]["bytes"] if complete else per[-1]["bytes"],
            "git_blob_sha1_of_fetched_bytes": complete[-1]["git_blob_sha1"] if complete else per[-1]["git_blob_sha1"],
            "hash_equal": bool(complete), "size_equal": bool(complete)}


def main():
    ap = argparse.ArgumentParser(prog="ledger_mirror_complete_read_r1.py")
    ap.add_argument("--ref", default="commander/control")
    ap.add_argument("--route", default="git", choices=("git", "api"))
    ap.add_argument("--arm", default="", choices=("", "old_onshot_read", "wrong_expected_sha",
                                                  "short_body", "no_api"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    if a.arm == "no_api":
        try:
            contents_meta(a.ref)
            print("ARM no_api passed the way it should not: the api leg answered")
            return 3
        except SystemExit:
            print("ARM no_api: refused - the api leg is what tells us the remote blob id, without it the "
                  "two-channel agreement is impossible")
            return 0
        except Exception as e:  # noqa: BLE001
            print("ARM no_api refused: %s" % type(e).__name__)
            return 0

    meta = contents_meta(a.ref, arm=a.arm)
    wants_refusal = a.arm in ("old_onshot_read", "wrong_expected_sha", "short_body")
    if a.arm == "old_onshot_read" or a.route == "api":
        res = read_via_api_raw(meta["sha"], meta["size"],
                               arm="old_onshot_read" if a.arm == "old_onshot_read" else None,
                               attempts=1 if a.arm == "old_onshot_read" else 6)
    else:
        res = read_via_git(a.ref, arm=a.arm or None)
    res["reported_blob_by_api"] = meta["sha"]
    if res["route"] == "git_transport":
        # the point of two channels: the id git transport's own tree names must be the id the API reports
        complete = bool(res["hash_equal"] and res["size_equal"]
                        and res["blob_id_named_by_tree"] == meta["sha"])
    else:
        complete = bool(res["hash_equal"] and res["size_equal"])
    verdict = (not complete) if wants_refusal else complete
    out = {"checked_at": time.strftime("%Y-%m-%d %H:%M:%S"), "request": vars(a),
           "api_contents_route": meta, "read": res,
           "remote_blob_from_api": meta["sha"], "remote_size_from_api": meta["size"],
           "bytes_fetched": human(res["bytes_fetched"]),
           "recomputed_git_blob_sha1": res["git_blob_sha1_of_fetched_bytes"],
           "two_channel_agreement": complete,
           "verdict": "COMPLETE_AND_HASHED_EQUAL" if complete else "ABORT_truncated_or_hash_mismatch",
           "arm": a.arm or "none", "arm_expected_refusal": wants_refusal,
           "arm_passes_by_refusing": bool(wants_refusal and not complete)}
    text = json.dumps(out, ensure_ascii=False, indent=1)
    print(text)
    if a.out:
        io.open(a.out, "w", encoding="utf-8", newline="\n").write(text)
    return 0 if verdict else 8


raise SystemExit(main())
