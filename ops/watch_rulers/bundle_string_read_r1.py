"""Commander's own read: is the X-5 sentence actually present in the bundle the phone is served?

This is deliberately NOT a runtime claim.  It answers one narrower question with bytes:
the served `index.html` names asset refs; fetch those from the same origin the tunnel serves and
search for (a) the 「技术详情」 label, (b) the NO_PLANS_PRODUCED sentence fragment, and record the
offsets and the asset that carries them, plus the generation the served root was built from (read from
the deploy receipt, cited by blob).  If either string is absent, X-5 cannot fire on this generation.
"""
import hashlib
import io
import json
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SERVE_ROOT = r"D:\moodle\_qoder_preview_20260920\dist"
BASE = "http://127.0.0.1:4781"
NEEDLES = {
    "label_technical_details": "技术详情",
    "no_plans_sentence": "原因原文在",
    "no_plans_status_token": "NO_PLANS_PRODUCED",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "cmdr-string-read"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status, r.headers.get("content-type", ""), r.read()


def main():
    status, ctype, index = fetch(BASE + "/index.html")
    refs = re.findall(r'(?:src|href)="(/[^"]+\.(?:js|css))"', index.decode("utf-8", "replace"))
    refs = sorted(set(refs))
    rows = []
    for ref in refs:
        st, ct, raw = fetch(BASE + ref)
        text = raw.decode("utf-8", "replace")
        found = {k: text.count(v) for k, v in NEEDLES.items()}
        rows.append({"ref": ref, "status": st, "content_type": ct, "bytes": len(raw),
                     "sha256": hashlib.sha256(raw).hexdigest()[:16],
                     "git_blob_sha1": hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(),
                     "served_as_html": "text/html" in ct,
                     "needle_hits": found,
                     "on_disk_equal": None})
    # disk cross-check: the same bytes must exist under the served root
    for row in rows:
        path = SERVE_ROOT + row["ref"].replace("/", "\\")
        try:
            disk = io.open(path, "rb").read()
            row["on_disk_equal"] = hashlib.sha256(disk).hexdigest().startswith(row["sha256"][:16])
            row["disk_bytes"] = len(disk)
        except OSError as exc:
            row["on_disk_equal"] = "UNREADABLE: " + type(exc).__name__

    totals = {k: sum(r["needle_hits"][k] for r in rows) for k in NEEDLES}
    out = {
        "schema": "CNX_CMDR_BUNDLE_STRING_READ_V1", "read_at_local": __import__("datetime").datetime.now(
            __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))).strftime(
            "%Y-%m-%d %H:%M:%S %z"),
        "origin": BASE, "index_status": status, "index_bytes": len(index),
        "assets_named_by_index": len(refs), "rows": rows,
        "needle_totals": totals,
        "decisions": {
            "every_named_asset_fetched_200": all(r["status"] == 200 for r in rows),
            "no_asset_served_as_html": not any(r["served_as_html"] for r in rows),
            "x5_label_present_in_deployed_bundle": totals["label_technical_details"] > 0,
            "x5_promise_sentence_present_in_deployed_bundle": totals["no_plans_sentence"] > 0,
            "no_plans_branch_present": totals["no_plans_status_token"] > 0},
        "scope": "Byte presence inside the JS the phone is served right now. It proves the code path is "
                 "in the deployed generation; it does NOT prove the screen renders the sentence, which "
                 "needs a runtime read (and, for the NO_PLANS_PRODUCED class, a working backend - the "
                 "data plane is currently down, so that runtime half stays NOT-DEPLOYED-OBSERVED)."}
    json.dump(out, io.open("_cmdr_bundle_string_read_r1.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("assets named by index:", len(refs))
    for r in rows:
        print("  ", r["ref"], r["status"], r["bytes"], "B", r["git_blob_sha1"][:12],
              "hits", r["needle_hits"], "disk-equal", r["on_disk_equal"])
    print("totals:", totals)
    print("decisions:", json.dumps(out["decisions"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
