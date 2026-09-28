"""ORD-0417 lane copy check r1 -- the commander's r2 rule, over a sha the caller names.

`cmdr_bundle_copy_check_r2.py` pins TIP to `refs/remotes/origin/mirror/integration-frontend-apple-pass1`,
which is right for judging the authoritative line and useless for judging a lane candidate: this order
adds two dictionary values, and the only question that matters is whether *this* commit's *this* value
is the byte string the served bundle actually carries.  Same rule, same regex, same dictionary-file
enumeration -- only the rev and the output path move, so the numbers are comparable rather than
parallel.

Nothing is written to the repo. The bundle is fetched over HTTP from a dist this lane built.

usage: python ord0417_bundle_copy_check_r1.py --sha <40-hex> --base http://127.0.0.1:4832 --out FILE
"""
import argparse, json, os, pathlib, re, subprocess, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = r"D:/moodle/CityNexus"

PAIR_RE = re.compile(r'"([a-z][A-Za-z]*[A-Za-z]*\.[A-Za-z][A-Za-z0-9]*)"[\s:]*"([^"]{12,120})"')


def show(rev, path):
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, path)],
                          capture_output=True).stdout.decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", required=True)
    ap.add_argument("--base", default="http://127.0.0.1:4832")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sha = subprocess.run(["git", "-C", REPO, "rev-parse", a.sha], capture_output=True,
                         text=True).stdout.strip()
    assert sha, "cannot resolve %s" % a.sha
    listed = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", sha, "frontend/src"],
                            capture_output=True, text=True).stdout.splitlines()
    files = [p for p in listed
             if (p.startswith("frontend/src/i18n/") and p.endswith((".ts", ".tsx")))
             or (p.endswith("Copy.ts") or p.endswith("Copy.tsx"))]

    pairs, per_file = [], {}
    for f in files:
        found = PAIR_RE.findall(show(sha, f))
        per_file[f] = len(found)
        pairs += found

    bykey = {}
    for k, v in pairs:
        bykey.setdefault(k, []).append(v)

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    html = opener.open(a.base + "/", timeout=25).read().decode("utf-8", "replace")
    asset = re.search(r'/assets/[A-Za-z0-9_\-\.]+\.js', html).group(0)
    css_asset = re.search(r'/assets/[A-Za-z0-9_\-\.]+\.css', html)
    bundle = opener.open(a.base + asset, timeout=90).read()
    text = bundle.decode("utf-8", "replace")

    hits, misses = [], []
    for k in sorted(bykey):
        for v in bykey[k]:
            (hits if v in text else misses).append((k, v))

    # this order's own two arms, named, so the delivery block can carry them without a grep
    named = {}
    for v in bykey.get("mapComp.selectedStopOnMap", []):
        named[v] = v in text
    # the class this order renders, and the CSS rule that makes it visible, live in the css asset
    css_text = ""
    if css_asset:
        css_text = opener.open(a.base + css_asset.group(0), timeout=60).read().decode("utf-8", "replace")

    out = {"sha": sha, "base": a.base, "dictionary_files": per_file, "served_asset": asset,
           "served_css_asset": css_asset.group(0) if css_asset else None,
           "bundle_bytes": len(bundle), "bundle_chars": len(text), "css_chars": len(css_text),
           "dictionary_pairs": len(pairs), "distinct_keys": len(bykey),
           "values_found_in_served_bundle": len(hits), "values_not_found": len(misses),
           "ord0417_arms_found": named,
           "selector_v8_map_selected_stop_in_css": ".v8-map-selected-stop" in css_text,
           "misses": misses[:60]}
    pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "misses"}, ensure_ascii=False, indent=1))
    for m in out["misses"][:20]:
        print("MISS", m[0], "|", m[1][:70])
    return 0


if __name__ == "__main__":
    sys.exit(main())
