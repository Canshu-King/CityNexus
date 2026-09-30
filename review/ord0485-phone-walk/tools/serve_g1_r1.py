"""ORD-0485: serve generation G1 (tip + the two dictionary keys) on its own port.

A fresh dist directory AND a fresh port: a reused port reuses the old Service Worker's
precache, which would make the second face serve the first generation's bytes.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EXPORT = LANE + "/export"
PORT = int(os.environ.get("CNX_PHONE_G1_PORT", "4862"))
BACKEND = os.environ.get("CNX_PHONE_BACKEND_PORT", "8139")
NODE = os.environ.get("CNX_PHONE_NODE", r"C:/Program Files/nodejs/node.exe")
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

env = dict(os.environ)
env["CITYNEXUS_BACKEND_PORT"] = str(BACKEND)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    env.pop(k, None)
log = "%s/run/vite_preview_g1_%d.log" % (LANE, PORT)
proc = subprocess.Popen(
    [NODE, "node_modules/vite/bin/vite.js", "preview", "--outDir",
     EXPORT + "/frontend/dist_g1", "--host", "127.0.0.1", "--port", str(PORT), "--strictPort"],
    cwd=EXPORT + "/frontend", env=env, creationflags=0x00000208,
    stdout=open(log, "ab"), stderr=subprocess.STDOUT)

served = None
for _ in range(30):
    time.sleep(2)
    try:
        with opener.open("http://127.0.0.1:%d/" % PORT, timeout=10) as r:
            if r.status == 200:
                served = r.read().decode("utf-8", "replace")
                break
    except Exception:
        continue
out = {"port": PORT, "spawn_pid": proc.pid, "alive": proc.poll() is None,
       "index_html_bytes": len(served or ""), "served": None}
if served:
    import re
    m = re.search(r'src="/assets/(index-[A-Za-z0-9_\-]+\.js)', served)
    out["served"] = {"entry_asset": m.group(1) if m else None}
    disk = open(EXPORT + "/frontend/dist_g1/index.html", "rb").read()
    out["index_served_sha1"] = __import__("hashlib").sha1(served.encode()).hexdigest()
    out["index_disk_sha1"] = __import__("hashlib").sha1(disk).hexdigest()
    out["index_bytes_equal_served_vs_disk"] = out["index_served_sha1"] == out["index_disk_sha1"]
print(json.dumps(out, indent=2))
sys.exit(0 if served else 5)
