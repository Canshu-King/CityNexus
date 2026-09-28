# Companion to cmdr_bundle_copy_check_r3.py, not a replacement: the shipped ruler reads its dictionary
# from whatever the mirror ref points at WHEN IT RUNS, and tonight the ref moves every few minutes, so
# a bundle built at one generation is scored against a dictionary from a later one. That is exactly how
# the "1 value not found" at tip 35326e62 arose -- the missing key is rank.loading, added by another
# lane after the build under test. Same extraction rules (PAIR_RE / KEY_RE / the 12..400 window / the
# plain + json_escaped dual form), but the dictionary is pinned to a rev passed on the command line.
import json
import re
import subprocess
import sys
import urllib.request

REPO = "D:/moodle/CityNexus"
REV = sys.argv[1]
BASE = sys.argv[2]
PAIR_RE = re.compile(r'"([a-z][A-Za-z]*(?:[A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*))"\s*:\s*"((?:[^"\\]|\\.)+)"')
KEY_RE = re.compile(r'^[a-z][A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*$')


def unescape(v):
    out, i = [], 0
    while i < len(v):
        c = v[i]
        if c == "\\" and i + 1 < len(v):
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "\\": "\\"}.get(v[i + 1], v[i + 1]))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


listed = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", REV, "frontend/src"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.splitlines()
files = [p for p in listed if (p.startswith("frontend/src/i18n/") and p.endswith((".ts", ".tsx")))
         or p.endswith(("Copy.ts", "Copy.tsx"))]
pairs, per_file = [], {}
for f in files:
    src = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (REV, f)], capture_output=True).stdout.decode("utf-8", "replace")
    got = [(k, unescape(v)) for k, v in PAIR_RE.findall(src) if KEY_RE.match(k) and 12 <= len(unescape(v)) <= 400]
    per_file[f] = len(got)
    pairs += got

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
html = opener.open(BASE + "/", timeout=25).read().decode("utf-8", "replace")
asset = re.search(r"/assets/[A-Za-z0-9_\-\.]+\.js", html).group(0)
raw = opener.open(BASE + asset, timeout=120).read()
bundle = raw.decode("utf-8", "replace")
hits, misses, forms = [], [], {"plain": 0, "json_escaped": 0}
for k, v in pairs:
    if v in bundle:
        hits.append(k); forms["plain"] += 1
    else:
        esc = json.dumps(v)[1:-1]
        if esc != v and esc in bundle:
            hits.append(k); forms["json_escaped"] += 1
        else:
            misses.append([k, v])
print(json.dumps({"rev": REV, "dictionary_files": per_file, "served_asset": asset,
                  "bundle_raw_bytes": len(raw), "dictionary_pairs": len(pairs),
                  "values_found_in_served_bundle": len(hits), "values_not_found": len(misses),
                  "match_forms": forms, "misses": misses[:20]}, ensure_ascii=False, indent=1))
sys.exit(0 if not misses else 3)
