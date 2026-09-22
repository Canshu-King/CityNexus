"""Publish a local file to the arbiter-readable branch, with a byte-level (git blob sha1) proof.

Why this exists: the arbiter audits from GitHub, and the working-tip SHAs are NOT resolvable
there (measured 2026-09-22: 50b35e0 / 3e259bd / 522c414 all return 422 "No commit found for
SHA" on both Canshu-King/CityNexus and CityNexus-Workspace). So a diff/receipt that only exists
in a local worktree is, to the auditor, not evidence at all. This publishes it to the one branch
that IS readable: Canshu-King/CityNexus @ commander/control (the established ledger-mirror lane).

Usage: publish_evidence.py <local_file> <repo_path> [commit_message]
"""
import base64
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.request

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-commander"}


def call(method, path, payload=None):
    req = urllib.request.Request("https://api.github.com" + path, method=method)
    for k, v in HDRS.items():
        req.add_header(k, v)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header("Content-Length", str(len(data)))
    try:
        with urllib.request.urlopen(req, data, timeout=240) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, str(e)[:300]


def main() -> int:
    local_path, repo_path = sys.argv[1], sys.argv[2]
    message = sys.argv[3] if len(sys.argv) > 3 else f"commander: publish {repo_path}"
    blob = io.open(local_path, "rb").read()
    want = hashlib.sha1(b"blob %d\x00" % len(blob) + blob).hexdigest()

    st, meta = call("GET", f"/repos/{REPO}/contents/{repo_path}?ref={BRANCH}")
    existing = meta.get("sha") if isinstance(meta, dict) else None
    print(f"GET {repo_path}: {st} existing_sha={str(existing)[:10]}")
    if existing == want:
        print("already identical - nothing to push")
        return 0
    payload = {"message": message, "content": base64.b64encode(blob).decode(), "branch": BRANCH}
    if existing:
        payload["sha"] = existing
    st, res = call("PUT", f"/repos/{REPO}/contents/{repo_path}", payload)
    commit = (res.get("commit", {}) or {}).get("sha", "")[:12] if isinstance(res, dict) else str(res)[:200]
    print(f"PUT -> {st} commit={commit}")
    if st not in (200, 201):
        return 3
    time.sleep(2)
    for attempt in range(1, 4):
        st, after = call("GET", f"/repos/{REPO}/contents/{repo_path}?ref={BRANCH}")
        if isinstance(after, dict) and after.get("sha") == want:
            print("PROOF (git blob sha1 equality): BYTE-LEVEL MATCH")
            print(f"local bytes {len(blob)} | remote size {after.get('size')} | sha1 {want[:16]}")
            return 0
        print("attempt", attempt, "remote", str(after)[:80] if not isinstance(after, dict) else after.get("sha", "")[:10])
        time.sleep(3)
    print("MISMATCH after retries - do not claim the publish")
    return 4


if __name__ == "__main__":
    sys.exit(main())
