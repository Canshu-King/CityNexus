"""CMDR dictionary-vs-bundle coverage ruler r3 - escape-aware extraction and dual-form matching.

r2 reported exactly one miss at tip 8a7665be: `shell.reservationReviewFields`.  That miss was the
ruler's, not the product's.  The value contains an inner quoted phrase, so in the .ts source it is
written with backslash-escaped quotes; r2's `"([^"]{12,120})"` stopped at the FIRST quote character,
i.e. it extracted a truncated value ending in a stray backslash, and a truncated value is of course
not in the bundle.  Reading the served asset directly shows the whole sentence shipping verbatim,
only re-quoted by the minifier (single quotes, because the string itself contains double quotes).

r3 therefore:
  * extracts values with an escape-aware pattern (`(?:[^"\\]|\\.)*`) and unescapes them, so the
    value compared is the value a traveller would read;
  * accepts either quoting form in the bundle - the unescaped text, or the JSON-escaped text - and
    records WHICH form matched (`match_form`), so a future reader can see the match was real;
  * still reports per-file contribution counts, so a denominator that silently stops covering a new
    copy file is visible (that was r1's original sin).

Read-only: the bundle is fetched over HTTP from CNX_BUNDLE_BASE; the dictionary is read out of git.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

HERE = pathlib.Path(__file__).parent
REPO = r"D:/moodle/CityNexus"
TIP = subprocess.run(["git", "-C", REPO, "rev-parse",
                      "refs/remotes/origin/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True).stdout.strip()

PAIR_RE = re.compile(r'"([a-z][A-Za-z]*(?:[A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*))"\s*:\s*"((?:[^"\\]|\\.)+)"')
KEY_RE = re.compile(r'^[a-z][A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*$')


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


def show(rev, path):
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, path)],
                          capture_output=True).stdout.decode("utf-8", "replace")


def dictionary_files():
    listed = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", TIP, "frontend/src"],
                            capture_output=True, text=True).stdout.splitlines()
    return [p for p in listed
            if (p.startswith("frontend/src/i18n/") and p.endswith((".ts", ".tsx")))
            or p.endswith(("Copy.ts", "Copy.tsx"))]


files = dictionary_files()
pairs, per_file, skipped = [], {}, 0
for f in files:
    src = show(TIP, f)
    found = []
    for k, v in PAIR_RE.findall(src):
        val = unescape(v)
        if not KEY_RE.match(k) or not (12 <= len(val) <= 400):
            skipped += 1
            continue
        found.append((k, val))
    per_file[f] = len(found)
    pairs += found

bykey = {}
for k, v in pairs:
    bykey.setdefault(k, []).append(v)

BASE = os.environ.get("CNX_BUNDLE_BASE", "http://127.0.0.1:4781")
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
html = opener.open(BASE + "/", timeout=25).read().decode("utf-8", "replace")
asset = re.search(r'/assets/[A-Za-z0-9_\-\.]+\.js', html).group(0)
raw = opener.open(BASE + asset, timeout=120).read()
bundle = raw.decode("utf-8", "replace")

hits, misses, forms = [], [], {"plain": 0, "json_escaped": 0}
for k in sorted(bykey):
    for v in bykey[k]:
        if v in bundle:
            hits.append((k, v, "plain"))
            forms["plain"] += 1
        else:
            esc = json.dumps(v)[1:-1]
            if esc != v and esc in bundle:
                hits.append((k, v, "json_escaped"))
                forms["json_escaped"] += 1
            else:
                misses.append((k, v))

out = {"tip": TIP, "ruler": "cmdr_bundle_copy_check_r3.py", "dictionary_files": per_file,
       "served_asset": asset, "bundle_chars": len(bundle), "bundle_raw_bytes": len(raw),
       "dictionary_pairs": len(pairs), "distinct_keys": len(bykey),
       "pairs_skipped_by_shape": skipped,
       "values_found_in_served_bundle": len(hits), "values_not_found": len(misses),
       "match_forms": forms, "misses": misses[:60],
       "sample_hits": [{"key": k, "form": f, "value_head": v[:70]} for k, v, f in hits[:12]]}
print(json.dumps({k: v for k, v in out.items() if k not in ("misses", "sample_hits")},
                 ensure_ascii=False, indent=1))
for m in misses[:20]:
    print("MISS", m[0], "|", m[1][:70])
_out_path = HERE / ("cmdr_bundle_copy_check_r3__%s.json" % str(out.get("tip") or "untagged")[:8])
if _out_path.exists():
    print("REFUSE: %s already holds a previous run; a run must not overwrite earlier evidence." % _out_path, file=sys.stderr)
    print("      Read the old one first, or delete it deliberately.", file=sys.stderr)
    sys.exit(4)
_out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
_out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
sys.exit(0 if not misses else 3)
