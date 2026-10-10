"""CMDR copy check r2 - same question as r1, over a wider dictionary surface.

r1 (kept as published at evidence/cmdr-instruments/bundle_copy_check_r1.py) scanned only
`frontend/src/i18n/LocaleContext.tsx`.  Two panels since then shipped their copy in their own named
dictionary files (`i18n/mapPanelCopy.ts` for ORD-A, `features/trash/journeyTrashCopy.ts` for
ORD-0402 slice 2), so r1's denominator stayed frozen at 627 pairs while the bundle grew - the尺 was
blind to new copy, which is the opposite of what a coverage gauge is for.

r2 enumerates every dictionary-shaped file the tree actually has:
  - anything under frontend/src/i18n/
  - anything named *Copy.ts / *Copy.tsx anywhere under frontend/src
and reports per-file counts, so a lane can see which file contributed which pairs.
Same rule as r1: a zh-side pair counts as shipped only if its exact value string appears in the
bundle the surface actually serves.  Nothing here is written; the bundle is fetched, the sources
are read with `git show`.
"""
import json, os, pathlib, re, subprocess, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).parent
REPO = r"D:/moodle/CityNexus"
TIP = subprocess.run(["git", "-C", REPO, "rev-parse",
                      "refs/remotes/origin/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True).stdout.strip()

PAIR_RE = re.compile(r'"([a-z][A-Za-z]*[A-Za-z]*\.[A-Za-z][A-Za-z0-9]*)"[\s:]*"([^"]{12,120})"')


def show(rev, path):
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, path)],
                          capture_output=True).stdout.decode("utf-8", "replace")


def dictionary_files():
    listed = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", TIP, "frontend/src"],
                            capture_output=True, text=True).stdout.splitlines()
    return [p for p in listed
            if (p.startswith("frontend/src/i18n/") and p.endswith((".ts", ".tsx")))
            or (p.endswith("Copy.ts") or p.endswith("Copy.tsx"))]


files = dictionary_files()
pairs, per_file = [], {}
for f in files:
    src = show(TIP, f)
    found = PAIR_RE.findall(src)
    per_file[f] = len(found)
    pairs += found

bykey = {}
for k, v in pairs:
    bykey.setdefault(k, []).append(v)

BASE = os.environ.get("CNX_BUNDLE_BASE", "http://127.0.0.1:4781")
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
html = opener.open(BASE + "/", timeout=25).read().decode("utf-8", "replace")
asset = re.search(r'/assets/[A-Za-z0-9_\-\.]+\.js', html).group(0)
raw = opener.open(BASE + asset, timeout=90).read()
bundle = raw.decode("utf-8", "replace")

hits, misses = [], []
for k in sorted(bykey):
    for v in bykey[k]:
        (hits if v in bundle else misses).append((k, v))

out = {"tip": TIP, "dictionary_files": per_file, "served_asset": asset,
       "bundle_chars": len(bundle), "bundle_raw_bytes": len(raw),
       "dictionary_pairs": len(pairs), "distinct_keys": len(bykey),
       "values_found_in_served_bundle": len(hits), "values_not_found": len(misses),
       "misses": misses[:60], "sample_hits": hits[:12]}
print(json.dumps({k: v for k, v in out.items() if k not in ("misses", "sample_hits")},
                 ensure_ascii=False, indent=1))
for m in misses[:20]:
    print("MISS", m[0], "|", m[1][:60])
(HERE / "cmdr_bundle_copy_check_r2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
