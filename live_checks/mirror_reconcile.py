"""Reconcile the local ledger against the remote mirror WITHOUT clobbering another writer.

Why this exists: on 2026-09-23 01:52 the mirror's PUT returned 409 ("is at <A> but expected <B>"),
i.e. the remote `CITYNEXUS_AGENT_CONTROL.md` changed between my GET and my PUT.  A blind retry would
push my whole-file snapshot over whatever the other writer had just published, which is the
shared-branch clobber this project already learned to avoid.  So: read both sides, say whether the
remote is AHEAD / BEHIND / DIVERGENT / IDENTICAL, and only then decide.

Usage: python mirror_reconcile.py [--fetch-remote]
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"
PATH = "CITYNEXUS_AGENT_CONTROL.md"
LOCAL = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-commander"}


def call(method, path, payload=None, timeout=240):
    req = urllib.request.Request("https://api.github.com" + path, method=method)
    for k, v in HDRS.items():
        req.add_header(k, v)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header("Content-Length", str(len(data)))
    try:
        with urllib.request.urlopen(req, data, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, str(e)[:400]


def blob_sha(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def main() -> int:
    local = io.open(LOCAL, "rb").read()
    lsha = blob_sha(local)
    st, meta = call("GET", f"/repos/{REPO}/contents/{PATH}?ref={BRANCH}")
    print(f"local : {len(local):>9} B  blob {lsha[:16]}")
    if not isinstance(meta, dict):
        print("remote: GET failed:", st, meta)
        return 5
    rsha, rsize = meta.get("sha"), meta.get("size")
    print(f"remote: {rsize:>9} B  blob {str(rsha)[:16]}  ({st})")
    if rsha == lsha:
        print("VERDICT: IDENTICAL - nothing to do")
        return 0
    print(f"VERDICT(prelim): DIFFERENT | size delta local-remote = {len(local) - int(rsize or 0):+} B")
    if "--fetch-remote" not in sys.argv:
        print("  re-run with --fetch-remote to compare contents (heads/tails + block headings)")
        return 1
    st2, blob = call("GET", f"/repos/{REPO}/git/blobs/{rsha}")
    if st2 != 200 or not isinstance(blob, dict):
        print("blob fetch failed:", st2, str(blob)[:200])
        return 5
    remote = base64.b64decode(blob["content"])
    print(f"fetched remote: {len(remote)} B  blob(local recompute) {blob_sha(remote)[:16]} "
          f"match_metadata_sha={blob_sha(remote) == rsha}")
    lset = set(ln for ln in local.decode("utf-8", "replace").splitlines() if ln.startswith("## "))
    rset = set(ln for ln in remote.decode("utf-8", "replace").splitlines() if ln.startswith("## "))
    only_local = sorted(lset - rset)
    only_remote = sorted(rset - lset)
    print(f"heading count local={len(lset)} remote={len(rset)}")
    print(f"headings ONLY in local  ({len(only_local)}):")
    for h in only_local[:12]:
        print("   L+", h[:110])
    print(f"headings ONLY in remote ({len(only_remote)}):")
    for h in only_remote[:12]:
        print("   R+", h[:110])
    if not only_local and only_remote:
        print("VERDICT: REMOTE_AHEAD - the other writer has blocks I lack; do NOT push my snapshot.")
        return 1
    if only_local and not only_remote:
        print("VERDICT: LOCAL_AHEAD - safe to push IF the shared lines are otherwise equal.")
        return 0
    if only_local and only_remote:
        print("VERDICT: DIVERGENT - both sides have unique blocks; merge by block before pushing.")
        return 1
    print("VERDICT: SAME_HEADINGS_DIFFERENT_BYTES - compare body text before pushing.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
