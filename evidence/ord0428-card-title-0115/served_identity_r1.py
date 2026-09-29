"""Prove, into a file, that the port the screen arms are read from serves this tree's own bytes.

A `vite preview` listener is only "mine" if the bytes it answers are the bytes my build wrote and the
process belongs to this invocation.  `index.html` is compared byte for byte, every asset it references is
fetched and compared to the file on disk, and the listening pid's command line is captured verbatim.
The SPA fallback answers 200 with HTML for a path that does not exist, so a status code alone proves
nothing -- hence the byte comparison.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0428"
DIST = r"D:\moodle\_qoder_lane_S4_0926\wt0428\frontend\dist"
BASE = os.environ.get("CNX_PROBE_BASE", "http://localhost:4473")
PORT = BASE.rsplit(":", 1)[-1]
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"


def fetch(url, dst):
    r = subprocess.run(["curl", "-s", "--noproxy", "*", "-o", dst, "-w", "%{http_code} %{size_download}",
                        url], capture_output=True, text=True, timeout=300)
    parts = (r.stdout or "").split()
    return (parts[0] if parts else "?", parts[1] if len(parts) > 1 else "?")


def sha(path):
    return hashlib.sha1(io.open(path, "rb").read()).hexdigest()


def main():
    out = {"base_url": BASE, "dist": DIST}
    tmp = os.path.join(WORK, "_probe_fetch")
    code, size = fetch(BASE + "/v8/trips", tmp)
    served_index = io.open(tmp, "rb").read()
    disk_index = io.open(os.path.join(DIST, "index.html"), "rb").read()
    out["index"] = {"http": code, "served_bytes": len(served_index), "disk_bytes": len(disk_index),
                    "served_sha1": hashlib.sha1(served_index).hexdigest(),
                    "disk_sha1": hashlib.sha1(disk_index).hexdigest(),
                    "equal": served_index == disk_index}
    refs = re.findall(r'(?:src|href)="(/[^"]+\.(?:js|css))"', served_index.decode("utf-8"))
    assets = []
    for p in refs:
        code, size = fetch(BASE + p, tmp)
        served = io.open(tmp, "rb").read()
        f = os.path.join(DIST, p.lstrip("/").replace("/", os.sep))
        on_disk = os.path.isfile(f)
        assets.append({"path": p, "http": code, "served_bytes": len(served),
                       "served_sha1": hashlib.sha1(served).hexdigest(),
                       "disk_exists": on_disk,
                       "disk_sha1": sha(f) if on_disk else None,
                       "equal": on_disk and served == io.open(f, "rb").read()})
    out["assets"] = assets
    out["assets_all_equal"] = bool(assets) and all(a["equal"] for a in assets)
    # a path that does not exist must still answer 200 with HTML -- which is why the byte comparison,
    # not the status code, is the proof.
    code, size = fetch(BASE + "/definitely-not-a-real-asset-9f3c.js", tmp)
    bogus = io.open(tmp, "rb").read()
    out["spa_fallback_control"] = {"http": code, "bytes": len(bogus),
                                   "is_html": (bogus.lstrip()[:15].lower().startswith(b"<!doctype")
                                               or bogus[:200].lower().find(b"<html") >= 0),
                                   "equals_index_html": bogus == served_index}
    ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                         "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*--port %s*' } "
                         "| ForEach-Object { \"$($_.ProcessId)|$($_.CommandLine)\" }" % PORT],
                        capture_output=True, text=True, timeout=300)
    out["listener_command_lines"] = [l for l in (ps.stdout or "").splitlines() if l.strip()][:4]
    ns = subprocess.run(["netstat", "-ano", "-t"], capture_output=True, text=True, timeout=300)
    out["netstat_lines_for_port"] = [l.strip() for l in (ns.stdout or "").splitlines()
                                     if (":" + PORT) in l and "LISTENING" in l.upper()]
    os.remove(tmp)
    io.open(os.path.join(WORK, "served_identity_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:1600])
    return 0 if out["index"]["equal"] and out["assets_all_equal"] else 1


if __name__ == "__main__":
    sys.exit(main())
