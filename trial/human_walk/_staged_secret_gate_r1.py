"""Refuse a commit if any staged text file contains the AMap key or an Authorization header.
Reads the key from the process environment only; prints counts, never the value. Exit 1 = do not commit."""
import os, subprocess
key = (os.environ.get("CITYNEXUS_AMAP_WEB_KEY") or "").strip()
files = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True).stdout.split()
hits = scanned = 0
for f in files:
    if f.endswith((".png", ".jpg", ".ico")):
        continue
    try:
        data = open(f, "rb").read().decode("utf-8", "replace")
    except Exception:
        continue
    scanned += 1
    for marker in (key, "Authorization", "Bearer "):
        if marker and marker in data:
            hits += 1
            print("MARKER_IN", f, "marker_len=%d" % len(marker))
print("key_len=%d text_files_scanned=%d hits=%d" % (len(key), scanned, hits))
raise SystemExit(1 if hits else 0)
