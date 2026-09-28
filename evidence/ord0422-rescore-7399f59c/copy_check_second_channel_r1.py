# Second channel on one number. The shipped cmdr_bundle_copy_check_r3.py reports values_not_found = 1 at
# this tip. Its own unescape maps \n \t \r \" \' \\ and nothing else, so a source escape like "\u2026"
# becomes the literal text "u2026", which the bundler -- which writes the real ellipsis character --
# cannot match. This runs the identical extraction with one added arm (\uXXXX) and reports both numbers,
# so the cause is measured rather than asserted. The shipped ruler is not modified.
import json
import re
import subprocess
import sys
import urllib.request

REV = sys.argv[1]
BASE = sys.argv[2]
REPO = "D:/moodle/CityNexus"
PAIR_RE = re.compile(r'"([a-z][A-Za-z]*(?:[A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*))"\s*:\s*"((?:[^"\\]|\\.)+)"')
KEY_RE = re.compile(r'^[a-z][A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*$')
SIMPLE = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "\\": "\\"}


def unescape(v, wide):
    out, i = [], 0
    while i < len(v):
        c = v[i]
        if c == "\\" and i + 1 < len(v):
            nxt = v[i + 1]
            if wide and nxt == "u" and len(v) >= i + 6:
                out.append(chr(int(v[i + 2:i + 6], 16)))
                i += 6
                continue
            out.append(SIMPLE.get(nxt, nxt))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


listed = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", REV, "frontend/src"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.splitlines()
files = [p for p in listed if (p.startswith("frontend/src/i18n/") and p.endswith((".ts", ".tsx")))
         or p.endswith(("Copy.ts", "Copy.tsx"))]
raw_pairs = []
for f in files:
    src = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (REV, f)],
                         capture_output=True).stdout.decode("utf-8", "replace")
    for k, v in PAIR_RE.findall(src):
        if KEY_RE.match(k) and 12 <= len(v.replace("\\", "")) <= 400:
            raw_pairs.append((k, v))
esc = [(k, v) for k, v in raw_pairs if "\\u" in v]

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
html = opener.open(BASE + "/", timeout=25).read().decode("utf-8", "replace")
asset = re.search(r"/assets/[A-Za-z0-9_\-\.]+\.js", html).group(0)
bundle = opener.open(BASE + asset, timeout=120).read().decode("utf-8", "replace")


def score(wide):
    miss = []
    for k, v in raw_pairs:
        val = unescape(v, wide)
        if val in bundle:
            continue
        e = json.dumps(val)[1:-1]
        if e != val and e in bundle:
            continue
        miss.append([k, val])
    return len(raw_pairs), len(miss), miss


n, m_strict, misses_strict = score(False)
_ , m_wide, misses_wide = score(True)
print(json.dumps({"rev": REV, "served_asset": asset, "pairs": n,
                  "values_not_found_with_the_rulers_unescape": m_strict,
                  "values_not_found_with_a_unicode_aware_unescape": m_wide,
                  "dictionary_values_carrying_a_unicode_escape": len(esc),
                  "missed_strict": misses_strict[:6], "missed_wide": misses_wide[:6],
                  "escaped_examples": [[k, v] for k, v in esc][:6]}, ensure_ascii=False, indent=1))
