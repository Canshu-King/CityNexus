# -*- coding: utf-8 -*-
"""ORD-0552 step one: reproduce the truncation before changing anything.

The commander's three runs each stopped at a different byte count (7 823 486 / 1 782 243 / 839 421) against
a remote size of 12 796 711, which reads as an early EOF rather than wrong content. The mirror's own reader
treats `read()` returning nothing as end-of-body, so a closed connection looks like a complete short body
and only the final hash catches it.

Everything measured here is the same route the mirror uses, in the same shape, with three additions so the
next design choice is not a guess: the headers the server actually sent, whether that endpoint honours a
`Range` request at all, and the network context this box is in (proxy env plus whether the proxy port has a
listener), because a proxy that answers nothing is what produced two false "unreachable" calls earlier.
"""
import hashlib
import io
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TOK = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
REPO = "Canshu-King/CityNexus"
REF = "commander%2Fcontrol"
PATH = "CITYNEXUS_AGENT_CONTROL.md"
CHUNK = 1 << 20
H = {"Authorization": "Bearer " + TOK, "User-Agent": "cnx-ord0552-repro-r1",
     "Accept": "application/vnd.github+json"}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def net_context():
    env = {k: (os.environ.get(k) or "") for k in
           ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY")}
    ns = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace",
                        timeout=300).stdout or ""
    return {"proxy_env": env, "listener_on_7892": [l.strip() for l in ns.splitlines()
                                                   if ":7892 " in l and "LISTENING" in l]}


def get(url, headers=None, timeout=900):
    req = urllib.request.Request(url, headers=headers or H)
    with OPENER.open(req, timeout=timeout) as r:
        return r.status, r.headers, r.read()


def main():
    ctx = net_context()
    status, hdr, body = get("https://api.github.com/repos/%s/contents/%s?ref=%s" % (REPO, PATH, REF))
    meta = json.loads(body)
    print(json.dumps({"contents_route": {"status": status, "sha": meta["sha"], "size": meta["size"],
                                          "body_is_json_only": "content" not in meta,
                                          "media_type": hdr.get("Content-Type")}}, ensure_ascii=False))

    reads = []
    for attempt in (1, 2, 3):
        hdrs = dict(H)
        hdrs["Accept"] = "application/vnd.github.raw"
        req = urllib.request.Request("https://api.github.com/repos/%s/git/blobs/%s" % (REPO, meta["sha"]),
                                     headers=hdrs)
        t0 = time.time()
        buf = bytearray()
        err = None
        resp_hdr = None
        try:
            with OPENER.open(req, timeout=1800) as r:
                resp_hdr = dict(r.headers)
                while True:
                    part = r.read(CHUNK)
                    if not part:
                        break
                    buf += part
        except Exception as e:  # noqa: BLE001
            err = "%s: %s" % (type(e).__name__, str(e)[:200])
        raw = bytes(buf)
        got = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
        reads.append({"attempt": attempt, "bytes": len(raw), "size_from_contents_route": meta["size"],
                      "short_by": meta["size"] - len(raw), "err": err,
                      "content_length_header": resp_hdr.get("Content-Length") if resp_hdr else None,
                      "transfer_encoding": resp_hdr.get("Transfer-Encoding") if resp_hdr else None,
                      "media_type_returned": resp_hdr.get("Content-Type") if resp_hdr else None,
                      "recomputed_blob_sha1": got, "equals_remote_sha": got == meta["sha"],
                      "seconds": round(time.time() - t0, 1)})
        print(json.dumps(reads[-1], ensure_ascii=False))

    rng = None
    try:
        h2 = dict(H)
        h2["Accept"] = "application/vnd.github.raw"
        h2["Range"] = "bytes=0-1048575"
        st, hd, bd = get("https://api.github.com/repos/%s/git/blobs/%s" % (REPO, meta["sha"]), h2, 600)
        rng = {"status": st, "bytes": len(bd), "content_range": hd.get("Content-Range"),
               "content_length": hd.get("Content-Length")}
    except urllib.error.HTTPError as e:
        rng = {"status": e.code, "reason": str(e)[:160]}
    except Exception as e:  # noqa: BLE001
        rng = {"error": "%s: %s" % (type(e).__name__, str(e)[:160])}
    print(json.dumps({"range_probe_first_MiB": rng}, ensure_ascii=False))

    doc = {"net_context": ctx, "remote": {"repo": REPO, "ref": "commander/control", "path": PATH,
                                          "blob_sha": meta["sha"], "size": meta["size"]},
           "raw_reads": reads, "range_probe": rng,
           "reproduced": any(r["equals_remote_sha"] is False and not r["err"] for r in reads),
           "note": "a read that ends at a short byte count with no exception is exactly what the mirror's "
                   "loop produces; the hash is the only thing standing between it and a half-ledger merge"}
    io.open(os.path.join(HERE, "ledger_mirror_repro_r1.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"reproduced": doc["reproduced"], "sha": meta["sha"], "size": meta["size"],
                      "shortfalls": [r["short_by"] for r in reads]}, ensure_ascii=False))


raise SystemExit(main())
