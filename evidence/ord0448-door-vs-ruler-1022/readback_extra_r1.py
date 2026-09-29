"""Independent remote read-back for the five files the second publish batch reported as already live.

The mirror answers `ALREADY_LIVE no write needed` when the path already holds the blob, which is a claim about
the remote, not a reading of it. So each path is fetched from the GitHub contents API on `commander/control`
and its server-side blob id and byte size are compared against what this machine holds. Nothing is written.
"""
import hashlib
import io
import json
import os
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request

os.environ["HTTPS_PROXY"] = ""
os.environ["HTTP_PROXY"] = ""
os.environ["NO_PROXY"] = "*"

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0448"
REPO = "D:/moodle/CityNexus"
TOKPATH = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
PROJ = "Canshu-King/CityNexus"
NUL = chr(0).encode()
BRANCH = "commander/control"
NAMES = ["landed_recheck_r1.py", "landed_recheck_r1.json", "current_line_r1.py",
         "current_line_r1.json", "publish_0448_receipt.json"]


def local_blob(path):
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d" % len(raw) + NUL + raw).hexdigest(), len(raw)


def gh(path):
    import urllib.request
    req = urllib.request.Request("https://api.github.com/repos/%s/contents/%s?ref=%s"
                                 % (PROJ, urllib.parse.quote(path, safe="/"), BRANCH))
    for k, v in (("Authorization", "Bearer " + io.open(TOKPATH, encoding="utf-8").read().strip()),
                 ("Accept", "application/vnd.github+json"), ("User-Agent", "cnx-s4-readback"),
                 ("X-GitHub-Api-Version", "2022-11-28")):
        req.add_header(k, v)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=180) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, str(e)[:300]


def main():
    slug = json.load(io.open(os.path.join(WORK, "publish_0448_receipt.json"),
                             encoding="utf-8"))["slug"]
    rows = []
    for name in NAMES:
        lp = os.path.join(WORK, name)
        lb, size = local_blob(lp)
        remote = slug + "/" + name
        code, doc = gh(remote)
        rec = {"path": remote, "local_blob": lb, "local_bytes": size, "http": code,
               "remote_sha": doc.get("sha") if isinstance(doc, dict) else None,
               "remote_size": doc.get("size") if isinstance(doc, dict) else None,
               "tail": None if isinstance(doc, dict) else str(doc)[:200]}
        rec["remote_equals_local"] = rec["remote_sha"] == lb and rec["remote_size"] == size
        rows.append(rec)
        print("%-58s %-6s local %s remote %s size %s/%s" % (
            remote, "VERIFIED" if rec["remote_equals_local"] else "CHECK", lb[:12],
            (rec["remote_sha"] or "")[:12], size, rec["remote_size"]))
    out = {"schema": "CNX_S4_ORD0448_READBACK_R1", "branch": BRANCH, "slug": slug, "rows": rows,
           "all_remote_verified": all(r["remote_equals_local"] for r in rows)}
    io.open(os.path.join(WORK, "readback_extra_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("all_remote_verified", out["all_remote_verified"])
    return 0 if out["all_remote_verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
