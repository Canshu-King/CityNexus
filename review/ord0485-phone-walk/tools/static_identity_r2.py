"""ORD-0485 lane tool: the two service-identity proofs for this lane's static face.

stack_up_r1 booted `vite preview` and polled it, but its own index read lost the race with the
server's start-up, so the byte-equality arms never ran.  This tool takes exactly those two proofs
now, plus the process-line third angle, and names the access-log proof it cannot take.

  proof 1 - the entry asset name is read out of THIS lane's served index.html,
  proof 2 - served bytes sha1 == disk bytes sha1, per file, paired one face to one file,
  proof 3 - the static face writes no request log line, so it is reported as taken or not taken
            rather than silently dropped.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EXPORT = LANE + "/export"
STATIC_PORT = int(os.environ.get("CNX_PHONE_STATIC_PORT", "4861"))
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def raw_get(path):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (STATIC_PORT, path),
                                 headers={"User-Agent": "ORD-0485-lane-phone", "Accept": "*/*"})
    with opener.open(req, timeout=25) as r:
        return r.status, dict(r.headers), r.read()


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def main():
    out = {"tool": "static_identity_r2", "static_port": STATIC_PORT,
           "took_local": time.strftime("%Y-%m-%d %H:%M:%S %z")}
    st, hd, body = raw_get("/")
    html = body.decode("utf-8", "replace")
    out["root_status"] = st
    out["root_bytes"] = len(body)
    out["disk_index_bytes"] = os.path.getsize(EXPORT + "/frontend/dist/index.html")
    disk_index = open(EXPORT + "/frontend/dist/index.html", "rb").read()
    out["PROOF_1_index_served_is_my_file"] = sha1(body) == sha1(disk_index)
    out["index_sha1_served"] = sha1(body)
    out["index_sha1_disk"] = sha1(disk_index)

    m = re.search(r'src="/assets/(index-[A-Za-z0-9_\-]+\.js)', html)
    js = m.group(1) if m else None
    out["PROOF_0_entry_asset_named_from_served_index_html"] = js
    rows = []
    for name in [n for n in (js, re.search(r'href="/assets/(index-[A-Za-z0-9_\-]+\.css)', html).group(1)) if n]:
        st2, hd2, b2 = raw_get("/assets/" + name)
        disk = open("%s/frontend/dist/assets/%s" % (EXPORT, name), "rb").read()
        rows.append({"asset": name, "status": st2, "content_type": hd2.get("Content-Type"),
                     "served_bytes": len(b2), "disk_bytes": len(disk),
                     "served_sha1_over_bytes": sha1(b2), "disk_sha1_over_bytes": sha1(disk),
                     "bytes_equal": sha1(b2) == sha1(disk),
                     "is_html_fallback": b2[:15].lstrip().lower().startswith(b"<!doctype")})
    out["PROOF_2_asset_bytes_served_vs_disk"] = rows

    # a name that does not exist must NOT be served as HTML-with-200 by my own face
    fake = "index-ZzzZzzzZ.js"
    try:
        st3, hd3, b3 = raw_get("/assets/" + fake)
    except Exception as e:
        st3, hd3, b3 = None, {"error": type(e).__name__}, b""
    out["nonexistent_asset_probe"] = {"status": st3, "content_type": hd3.get("Content-Type"),
                                      "bytes": len(b3),
                                      "answered_as_html_fallback": b3[:15].lstrip().lower().startswith(b"<!doctype")}

    rc, o = subprocess.run(["netstat", "-ano", "-p", "tcp"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT).returncode, \
              subprocess.run(["netstat", "-ano", "-p", "tcp"], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT).stdout.decode("gbk", errors="replace")
    pid = None
    for line in o.splitlines():
        p = line.split()
        if len(p) >= 5 and p[0].upper() == "TCP" and p[1].endswith(":%d" % STATIC_PORT) \
                and p[3].upper() == "LISTENING":
            pid = p[4]
    out["listener_pid"] = pid
    if pid:
        cl = subprocess.run(["powershell", "-NoProfile", "-Command",
                             "Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
                             "Select-Object -ExpandProperty CommandLine" % pid],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                            ).stdout.decode("gbk", errors="replace").strip()
        out["listener_command_line"] = cl
        out["listener_command_line_points_at_my_dist"] = ("--outDir" in cl and "phone_ord0485" in cl)

    log = "%s/run/vite_preview_%d.log" % (LANE, STATIC_PORT)
    size_before = os.path.getsize(log)
    raw_get("/")
    time.sleep(1.5)
    size_after = os.path.getsize(log)
    out["preview_log_bytes_delta_after_a_request"] = size_after - size_before
    out["PROOF_3_access_log"] = ("AVAILABLE" if size_after > size_before
                                 else "NOT_AVAILABLE_BY_CMDR")
    out["overall_static_identity"] = (
        "GREEN_TWO_PROOFS_PLUS_PROCESS_LINE"
        if out["PROOF_1_index_served_is_my_file"]
        and all(r["bytes_equal"] for r in out["PROOF_2_asset_bytes_served_vs_disk"])
        and out["PROOF_2_asset_bytes_served_vs_disk"]
        and out.get("listener_command_line_points_at_my_dist")
        else "RED")

    path = LANE + "/run/static_identity_r2.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
