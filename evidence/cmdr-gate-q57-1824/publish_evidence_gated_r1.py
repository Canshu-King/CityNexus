"""Q57=② implemented on the commander's side: an identical-or-refuse wrapper for evidence publishing.

Ruling relayed 2026-09-25 18:22 (+08), arbiter symbol ②: any single-file publish into `evidence/` must
either be a NEW path, or be byte-identical to what is already there (SKIP), or be REFUSED. The ledger
mirror is the one path exempt because it is rewritten whole file by design.

The point of the wrapper is not convenience - it is that "0 overwrites" stops being a sentence I type and
becomes a state the tool refuses to leave. A refusal prints both blob coordinates and the full commit
history of that path so the operator can move to a new filename instead of reaching for a force.

Self-test: three arms, two directions, run against throwaway paths under evidence/_cmdr-gate-selftest-<hhmmss>/
  A new-path        -> PUBLISH
  B same bytes      -> SKIP
  C different bytes -> REFUSE (and the path must still hold B's bytes afterwards)
"""
import argparse
import base64
import hashlib
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"
HDRS = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-cmdr-gated-publisher", "X-GitHub-Api-Version": "2022-11-28"}
EXEMPT = {"CITYNEXUS_AGENT_CONTROL.md"}          # the whole-file ledger mirror, by ruling ②
EVIDENCE_PREFIX = "evidence/"


def call(method, path, payload=None):
    req = urllib.request.Request("https://api.github.com" + path, method=method)
    for k, v in HDRS.items():
        req.add_header(k, v)
    data = json.dumps(payload).encode() if payload is not None else None
    if data:
        req.add_header("Content-Length", str(len(data)))
    try:
        with urllib.request.urlopen(req, data, timeout=180) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, str(e)[:300]


def blob_sha1(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def q(s, safe=""):
    return urllib.parse.quote(s, safe=safe)


def remote(path):
    """(exists, blob sha, bytes) for a path on the branch, or (None, ...) when the route failed."""
    st, meta = call("GET", "/repos/%s/contents/%s?ref=%s" % (REPO, q(path, "/"), q(BRANCH)))
    if st == 404:
        return False, None, None
    if st != 200 or not isinstance(meta, dict):
        return None, st, meta                      # a dead route is never a verdict
    st2, bl = call("GET", "/repos/%s/git/blobs/%s" % (REPO, meta["sha"]))
    if st2 != 200:
        return None, st2, bl
    raw = base64.b64decode(bl["content"])
    return True, meta["sha"], raw


def history(path):
    st, arr = call("GET", "/repos/%s/commits?path=%s&sha=%s&per_page=100" % (REPO, q(path, "/"), q(BRANCH)))
    return [(c["sha"][:12], c["commit"]["author"]["date"]) for c in arr] if st == 200 else [("<route failed %s>" % st, "")]


def put(path, raw, message):
    for attempt in range(4):
        exists, sha, _ = remote(path)
        st, res = call("PUT", "/repos/%s/contents/%s" % (REPO, q(path, "/")),
                       {"message": message, "content": base64.b64encode(raw).decode(),
                        "branch": BRANCH, **({"sha": sha} if exists else {})})
        if st in (200, 201):
            commit = res["commit"]["sha"]
            back, bsha, braw = remote(path)
            want = blob_sha1(raw)
            proof = "BYTE-LEVEL MATCH" if bsha == want == blob_sha1(braw or b"") else "MISMATCH-after-write"
            return {"decision": "CREATED" if not exists else "UPDATED", "commit": commit,
                    "blob": want, "readback_blob": bsha, "proof": proof, "bytes": len(raw)}
        if st == 409:
            time.sleep(2 * (attempt + 1))          # branch moved under me; re-read and retry
            continue
        return {"decision": "PUT_FAILED", "status": st, "detail": str(res)[:300]}
    return {"decision": "PUT_FAILED_CONCURRENT", "status": 409}


def publish(path, local, message):
    raw = io.open(local, "rb").read()
    want = blob_sha1(raw)
    if path in EXEMPT:
        print("EXEMPT-BY-RULING: %s is the whole-file ledger mirror, gate does not apply" % path)
        return put(path, raw, message)
    if not path.startswith(EVIDENCE_PREFIX):
        return {"decision": "REFUSED_OUT_OF_SCOPE", "why": "ruling ② covers only the evidence/ prefix; "
                "refusing rather than silently doing nothing for other paths"}
    exists, sha, cur = remote(path)
    if exists is None:
        return {"decision": "REFUSED_ROUTE_UNREADABLE", "detail": [sha, cur]}
    if not exists:
        print("GATE: new path -> publish")
        return put(path, raw, message)
    if blob_sha1(cur or b"") == want and len(cur) == len(raw) and cur == raw:
        print("GATE: identical bytes already on the branch -> SKIP (nothing sent)")
        return {"decision": "SKIP_IDENTICAL", "blob": want, "bytes": len(raw)}
    print("GATE: REFUSE - path already exists with different bytes")
    print("   on-branch blob %s (%d B)" % (sha, len(cur or b"")))
    print("   proposed  blob %s (%d B)" % (want, len(raw)))
    print("   history of that path:", history(path))
    print("   -> publish under a NEW filename; do not overwrite, do not re-push the old bytes")
    return {"decision": "REFUSE_OVERWRITE", "on_branch": sha, "proposed": want,
            "bytes_on_branch": len(cur or b""), "bytes_proposed": len(raw),
            "commits": history(path)}


def selftest():
    stamp = time.strftime("%H%M%S")
    base = EVIDENCE_PREFIX + "_cmdr-gate-selftest-" + stamp + "/"
    payload_a = ("selftest arm A, published %s by publish_evidence_gated_r1. marker %s\n"
                 % (time.strftime("%Y-%m-%d %H:%M:%S %z"), stamp)).encode("utf-8")
    payload_c = payload_a + b"arm C adds bytes so the gate must refuse\n"
    io.open("_gate_selftest_a.txt", "wb").write(payload_a)
    io.open("_gate_selftest_c.txt", "wb").write(payload_c)
    res = {}
    res["A_new_path"] = publish(base + "arm_A_new.json", "_gate_selftest_a.txt", "cmdr gate selftest A (new path)")
    res["B_same_bytes"] = publish(base + "arm_A_new.json", "_gate_selftest_a.txt", "cmdr gate selftest B (same bytes)")
    res["C_different_bytes"] = publish(base + "arm_A_new.json", "_gate_selftest_c.txt", "cmdr gate selftest C (must refuse)")
    exists, sha, cur = remote(base + "arm_A_new.json")
    res["D_after_state"] = {"blob": sha, "bytes": len(cur or b""), "still_arm_A_bytes": cur == payload_a,
                            "arm_C_never_landed": blob_sha1(payload_c) != sha}
    res["verdict"] = ("SELFTEST_PASS" if res["A_new_path"]["decision"] == "CREATED"
                      and res["B_same_bytes"]["decision"] == "SKIP_IDENTICAL"
                      and res["C_different_bytes"]["decision"] == "REFUSE_OVERWRITE"
                      and res["D_after_state"]["still_arm_A_bytes"]
                      and res["D_after_state"]["arm_C_never_landed"] else "SELFTEST_FAIL")
    res["scope"] = ("Three arms, two directions: a new path is written, identical bytes are skipped, different bytes are "
                    "refused and the branch is left holding the original bytes. The refusal path prints both blobs and "
                    "the path's commit list so the operator moves to a new filename instead of forcing.")
    out = json.dumps(res, ensure_ascii=False, indent=1)
    io.open("_gate_selftest_result_%s.json" % stamp, "w", encoding="utf-8").write(out)
    print(out)
    print("result file _gate_selftest_result_%s.json" % stamp)
    return 0 if res["verdict"] == "SELFTEST_PASS" else 7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local")
    ap.add_argument("--path")
    ap.add_argument("--message", default="commander: gated evidence publish")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.local or not a.path:
        ap.error("--local and --path are required (or --selftest)")
    r = publish(a.path, a.local, a.message)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r.get("decision") in ("CREATED", "SKIP_IDENTICAL") and "MISMATCH" not in str(r) else (
        6 if r.get("decision") == "REFUSE_OVERWRITE" else 3)


if __name__ == "__main__":
    raise SystemExit(main())
