# Companion to cmdr_bundle_copy_check_r3.py, which reads its dictionary from the mirror TIP and so
# cannot see the 65 keys this order adds. Same extraction rules, copied verbatim from that ruler
# (PAIR_RE / KEY_RE / unescape / the 12..400 length window), applied to the delta between the mirror
# dictionary and this candidate's dictionary, and matched against the same served asset.
# The shipped ruler is not modified here; this file only adds the second half of its denominator.
import json
import re
import subprocess
import sys
import urllib.request

REPO = "D:/moodle/CityNexus"
CAND = sys.argv[1]
TIP_ARG = sys.argv[3] if len(sys.argv) > 3 else None
BASE = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:4314"
PATH = "frontend/src/i18n/LocaleContext.tsx"

PAIR_RE = re.compile(r'"([a-z][A-Za-z]*(?:[A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*))"\s*:\s*"((?:[^"\\]|\\.)+)"')
KEY_RE = re.compile(r'^[a-z][A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*$')
TIP = TIP_ARG or "f662905ec4cafe05687d33a05dcbc7ca8031de43"


def unescape(v):
    out, i = [], 0
    while i < len(v):
        c = v[i]
        if c == "\\" and i + 1 < len(v):
            n = v[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "\\": "\\"}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def pairs_of(rev):
    src = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, PATH)],
                         capture_output=True).stdout.decode("utf-8", "replace")
    out = {}
    for k, v in PAIR_RE.findall(src):
        val = unescape(v)
        if not KEY_RE.match(k) or not (12 <= len(val) <= 400):
            continue
        out.setdefault(k, set()).add(val)
    return out


mirror = pairs_of(TIP)
cand = pairs_of(CAND)
new = {k: sorted(v - mirror.get(k, set())) for k, v in cand.items() if v - mirror.get(k, set())}
gone = sorted(set(mirror) - set(cand))

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
html = opener.open(BASE + "/", timeout=25).read().decode("utf-8", "replace")
asset = re.search(r'/assets/[A-Za-z0-9_\-\.]+\.js', html).group(0)
bundle = opener.open(BASE + asset, timeout=120).read().decode("utf-8", "replace")

hits, misses = [], []
for k in sorted(new):
    for v in new[k]:
        if v in bundle:
            hits.append((k, v, "plain"))
        else:
            esc = json.dumps(v)[1:-1]
            if esc != v and esc in bundle:
                hits.append((k, v, "json_escaped"))
            else:
                misses.append((k, v))

out = {
    "candidate": CAND, "mirror_tip": TIP, "dictionary_path": PATH,
    "served_base": BASE, "served_asset": asset, "bundle_chars": len(bundle),
    "mirror_pairs": sum(len(v) for v in mirror.values()),
    "candidate_pairs": sum(len(v) for v in cand.values()),
    "new_key_values": sum(len(v) for v in new.values()),
    "distinct_new_keys": len(new),
    "keys_dropped_from_mirror": gone,
    "new_values_found_in_served_bundle": len(hits),
    "new_values_not_found": len(misses),
    "misses": misses,
}
print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(0 if not misses and not gone else 3)
