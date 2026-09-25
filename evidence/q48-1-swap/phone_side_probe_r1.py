"""Phone-side probe: after a generation swap, prove what the phone fetches == what is on disk.

Why this exists (measured incident, ORD-0276): a swapped `index.html` can name an asset the served root
does not have, and the proxy then answers `200 + text/html` at a `.js` URL -> strict MIME check -> React
never mounts -> white page.  A 200 on `/` proves nothing about that.  So this probe takes every ref the
served index actually names, fetches it THROUGH THE TUNNEL with Basic auth read from the auth file by
path (the value is never printed or stored), and asserts four independent things per asset:
status 200, byte equality against disk (sha256), not-a-HTML fallback, and a JS content type on `.js`.

Usage:  python phone_side_probe_r1.py [--generation <40-hex>] [--out <file>]
Env:    CNX_PROBE_SERVE (served dist root), CNX_PROBE_AUTH_FILE, CNX_PROBE_TUNNEL
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SERVE_DEFAULT = r"D:\moodle\_qoder_preview_20260920\dist"
AUTH_DEFAULT = r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt"
TUNNEL_DEFAULT = "https://obligation-plain-arcade-bean.trycloudflare.com"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", default=os.environ.get("CNX_PROBE_SERVE", SERVE_DEFAULT))
    ap.add_argument("--auth-file", default=os.environ.get("CNX_PROBE_AUTH_FILE", AUTH_DEFAULT))
    ap.add_argument("--tunnel", default=os.environ.get("CNX_PROBE_TUNNEL", TUNNEL_DEFAULT))
    ap.add_argument("--generation", default="unknown")
    ap.add_argument("--out", default="_phone_side_probe_out.json")
    a = ap.parse_args()

    fields = io.open(a.auth_file, encoding="utf-8").read().strip().split("\t")
    cred = fields[0] + ":" + fields[1]          # used, never echoed
    idx = io.open(os.path.join(a.serve, "index.html"), encoding="utf-8", errors="replace").read()
    refs = sorted(set(re.findall(r"/assets/[A-Za-z0-9_.-]+\.(?:js|css)", idx)))
    rows = []
    for path in refs + ["/v10-sw.js"]:
        local = os.path.join(a.serve, *path.lstrip("/").split("/"))
        if not os.path.isfile(local):
            rows.append({"path": path, "error": "named-by-index-but-missing-on-disk"})
            continue
        db = open(local, "rb").read()
        subprocess.run(["curl", "-s", "-u", cred, "-D", "/tmp/_probe_h.txt", "-o", "/tmp/_probe_b.bin",
                        "--max-time", "60", a.tunnel + path], capture_output=True)
        body = open("/tmp/_probe_b.bin", "rb").read()
        hdr = io.open("/tmp/_probe_h.txt", encoding="latin-1").read()
        m = re.search(r"HTTP/[\d.]+ (\d+)", hdr)
        ct = re.search(r"(?im)^content-type:\s*([^\r\n]+)", hdr)
        ctv = ct.group(1) if ct else None
        sh = hashlib.sha256(body).hexdigest()
        dh = hashlib.sha256(db).hexdigest()
        rows.append({"path": path, "http_status": int(m.group(1)) if m else None, "content_type": ctv,
                     "served_bytes": len(body), "disk_bytes": len(db),
                     "served_sha256": sh, "disk_sha256": dh,
                     "bytes_equal": sh == dh and len(body) == len(db),
                     "is_html_fallback": bool(ctv and "text/html" in ctv.lower()),
                     "js_mime_is_script": (not path.endswith(".js")) or bool(
                         ctv and ("javascript" in ctv.lower() or "ecmascript" in ctv.lower()))})
    ok_rows = [r for r in rows if "error" not in r]
    decisions = {
        "every_named_asset_present_on_disk": len(ok_rows) == len(rows) and len(rows) > 0,
        "all_200": all(r.get("http_status") == 200 for r in ok_rows),
        "all_bytes_equal_to_disk": all(r.get("bytes_equal") for r in ok_rows),
        "no_asset_served_as_html": all(not r.get("is_html_fallback") for r in ok_rows),
        "js_content_type_correct": all(r.get("js_mime_is_script") for r in ok_rows),
    }
    out = {"schema": "CNX_CMDR_PHONE_SIDE_PROBE_V1", "probed_at_local": time.strftime("%Y-%m-%d %H:%M:%S %z"),
           "serve_root": a.serve, "tunnel_host": a.tunnel.split("//")[1], "generation_under_test": a.generation,
           "credential_handling": "auth read from the file by path; value never printed nor stored in this artifact",
           "index_named_refs": refs, "assets_probed": len(rows), "rows": rows,
           "decisions": decisions,
           "overall": "DEPLOYED_AND_BYTE_IDENTICAL_ON_PHONE_SIDE" if all(decisions.values()) else "NOT_VERIFIED",
           "scope": "Transport-level identity only (status, content type, bytes). It does not prove the app "
                    "renders or that a traveller can finish a plan - that is the walkthrough gate."}
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out["overall"], "| assets probed", len(rows))
    for r in decisions.items():
        print("   ", r[0], "=", r[1])
    print("wrote", a.out, os.path.getsize(a.out), "B")
    return 0 if all(decisions.values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
