import subprocess, re, json, os, pathlib, urllib.request
HERE = pathlib.Path(__file__).parent
REPO = r"D:/moodle/CityNexus"
TIP = subprocess.run(["git", "-C", REPO, "rev-parse", "refs/remotes/origin/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True).stdout.strip()
def blob_of(rev, path):
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, path)],
                          capture_output=True).stdout.decode("utf-8", "replace")
loc = blob_of(TIP, "frontend/src/i18n/LocaleContext.tsx")
# every "key: 'value'" style entry on the zh side
pairs = re.findall(r'"([a-z][A-Za-z]*\.[A-Za-z]+)"\s*:\s*"([^"]{12,70})"', loc)
bykey = {}
for k, v in pairs:
    bykey.setdefault(k, []).append(v)
index = blob_of(TIP, "frontend/index.html")
# Which surface to measure. Default stays the phone-facing hop2; CNX_BUNDLE_BASE lets me point it at
# the private preview that serves a not-yet-deployed bundle, so "dictionary value missing from the
# shipped JS" can be checked on the generation I am about to switch to, not only on the old one.
BASE = os.environ.get("CNX_BUNDLE_BASE", "http://127.0.0.1:4781")
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
html = opener.open(BASE + "/", timeout=20).read().decode("utf-8", "replace")
asset = re.search(r'/assets/[A-Za-z0-9_\-\.]+\.js', html).group(0)
raw_bundle = opener.open(BASE + asset, timeout=60).read()
bundle = raw_bundle.decode("utf-8", "replace")
# r1 called len(bundle) "bundle_bytes"; it is a CHARACTER count and the two differ by the CJK
# multi-byte tail (measured: 1,324,044 bytes vs 1,287,036 chars).  Both are reported now.
hits, misses = [], []
for k in sorted(bykey):
    for v in bykey[k]:
        (hits if v in bundle else misses).append((k, v))
print(json.dumps({"tip": TIP, "served_asset": asset, "bundle_chars": len(bundle),
                  "bundle_raw_bytes": len(raw_bundle),
                  "dictionary_pairs": len(pairs), "distinct_keys": len(bykey),
                  "values_found_in_served_bundle": len(hits),
                  "values_not_found": len(misses)}, ensure_ascii=False))
out = {"tip": TIP, "served_asset": asset, "bundle_chars": len(bundle),
       "bundle_raw_bytes": len(raw_bundle),
       "dictionary_pairs": len(pairs), "distinct_keys": len(bykey),
       "values_found_in_served_bundle": len(hits), "values_not_found": len(misses),
       "hits": hits[:40], "misses": misses[:40]}
(HERE / "cmdr_bundle_copy_check_r1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in hits[:6]:
    print("HIT", k, v.encode("ascii", "replace").decode()[:60])
