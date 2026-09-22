"""Mirror the ledger and prove it byte-level WITHOUT downloading 1.6 MB (big bodies link-reset here).

Proof: the contents API returns the git blob sha, and a git blob sha is
sha1("blob " + N + NUL + bytes). Computing that locally and comparing to the remote sha is a
byte-level equality proof for the pushed snapshot without transferring the body back.
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
PATH = "CITYNEXUS_AGENT_CONTROL.md"
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


local = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", "rb").read()
want = hashlib.sha1(b"blob %d\x00" % len(local) + local).hexdigest()
st, meta = call("GET", f"/repos/Canshu-King/CityNexus/contents/{PATH}?ref=commander/control")
# Fail closed on a non-dict answer (measured 2026-09-23 02:53): when the initial GET raises instead of
# returning an HTTPError, call() returns (ErrType, "message") and this line used to crash with
# `'str' object has no attribute 'get'` - i.e. an assumption about the return SHAPE, the same family
# as the doubled-verdict bug.  Say what happened and stop; a crash is not a diagnosis.
if not isinstance(meta, dict):
    print(f"MIRROR_PRECONDITION_FAILED: the initial GET answered {st}: {str(meta)[:200]}")
    print("  fail-closed: no PUT attempted and nothing claimed; re-run the mirror.")
    raise SystemExit(6)
print("remote before:", st, "sha", str(meta.get("sha"))[:10], "size", meta.get("size"))
if isinstance(meta, dict) and meta.get("sha") == want:
    print("already identical - nothing to push")
    raise SystemExit(0)

def put_once(sha, message):
    return call("PUT", f"/repos/Canshu-King/CityNexus/contents/{PATH}", {
        "message": message,
        "content": base64.b64encode(local).decode(),
        "sha": sha, "branch": "commander/control"})


message = sys.argv[1] if len(sys.argv) > 1 else "commander: ledger mirror"
st, res = put_once(meta["sha"], message)
print("PUT ->", st, "commit", (res.get("commit", {}) or {}).get("sha", "")[:12] if isinstance(res, dict) else str(res)[:200])
if st == 401:
    # Measured 2026-09-22 19:18-19:27: this PUT returned 401 twice while reads and equally-sized
    # writes succeeded seconds apart, and the identical request then returned 200.  Per arbiter
    # 5775473121 §2 the tool must NOT auto-retry auth failures (fail closed so it is noticed) and
    # must NOT touch credentials.  Record the anomaly and tell the operator to re-run.
    print("AUTH_ANOMALY_401: intermittent (a same-minute read succeeded and the same request later")
    print("  returned 200).  NOT a credential failure - do NOT rotate or edit the token.")
    print("  Re-run this mirror; if it recurs, capture status + endpoint + GitHub request id.")
    raise SystemExit(4)
if st == 409:
    # Measured 2026-09-23 01:52: this PUT returned 409 ("is at <A> but expected <B>") and a fresh GET
    # a minute later showed the remote still holding my own previous snapshot - so the conflict was
    # transient, and the retry that followed succeeded.  What made the retry SAFE was the reconcile
    # (remote had no block I lacked), not the retry itself: a blind retry would push this whole-file
    # snapshot over any concurrent writer's ledger.  So fail closed and demand the reconcile first.
    print("MIRROR_CONFLICT_409: the remote ledger moved between my GET and my PUT.")
    print("  Do NOT blind-retry.  First run:  python mirror_reconcile.py --fetch-remote")
    print("  Push again only if the verdict is LOCAL_AHEAD (or IDENTICAL-overlap); if it is")
    print("  REMOTE_AHEAD / DIVERGENT, merge by block first - the ledger is whole-file rewritten")
    print("  by others and a blind push would clobber their write.")
    raise SystemExit(5)
if st not in (200, 201):
    raise SystemExit(3)

time.sleep(2)
for attempt in range(1, 4):
    st, after = call("GET", f"/repos/Canshu-King/CityNexus/contents/{PATH}?ref=commander/control")
    if isinstance(after, dict) and after.get("sha") == want:
        print("PROOF (git blob sha1 equality, no body download): BYTE-LEVEL MATCH")
        print("local bytes %d | remote size %s | sha1 %s" % (len(local), after.get("size"), want[:16]))
        raise SystemExit(0)
    print("attempt", attempt, "remote sha", str(after.get("sha"))[:10] if isinstance(after, dict) else after,
          "size", after.get("size") if isinstance(after, dict) else "")
    time.sleep(3)
print("MISMATCH after retries - do not claim the mirror")
raise SystemExit(4)
