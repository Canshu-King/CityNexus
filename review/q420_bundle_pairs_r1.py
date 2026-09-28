#!/usr/bin/env python3
"""ORD-0420: the five new pairs against the bundle the commander's ruler cannot see yet.

cmdr_bundle_copy_check_r3 reads the dictionary out of refs/remotes/origin/mirror/..., which is the
authoritative line - a lane may not move it, so my new keys are not in that denominator until the
order lands. This script applies the ruler's own escape-aware extraction and its dual-form match rule
to the five pairs at THIS commit, against the same bytes the ruler fetched.
"""
import hashlib
import os
import re
import subprocess
import sys
import urllib.request

WT = r"D:/moodle/_qoder_lane_q0420"
REL = "frontend/src/i18n/LocaleContext.tsx"
BASE = os.environ.get("CNX_BUNDLE_BASE", "http://127.0.0.1:4901")
PAIR_RE = re.compile(r'"([a-z][A-Za-z]*(?:[A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*))"\s*:\s*"((?:[^"\\]|\\.)+)"')
KEYS = ["nav.groupToday", "nav.groupPlan", "nav.groupTravel", "nav.groupSystem", "nav.groupOther"]
bad = []

head = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
src = subprocess.run(["git", "-C", WT, "show", "HEAD:" + REL], capture_output=True,
                     text=True, encoding="utf-8").stdout
reg = subprocess.run(["git", "-C", WT, "show", "HEAD:frontend/src/routes/v8Routes.ts"],
                     capture_output=True, text=True, encoding="utf-8").stdout
pairs = [(k, v) for k, v in PAIR_RE.findall(src)]
mine = [(k, v) for k, v in pairs if k in KEYS]
bykey = {}
for k, v in mine:
    bykey.setdefault(k, []).append(v)

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
html = opener.open(BASE + "/", timeout=25).read().decode("utf-8", "replace")
asset = re.search(r"/assets/[A-Za-z0-9_\-\.]+\.js", html).group(0)
raw = opener.open(BASE + asset, timeout=120).read()
bundle = raw.decode("utf-8", "replace")

rows = []
for k in KEYS:
    vals = bykey.get(k, [])
    if len(vals) != 2:
        bad.append("%s has %d values, expected the en/zh pair" % (k, len(vals)))
    for v in vals:
        if v in bundle:
            form = "plain"
        else:
            esc = v.encode("unicode_escape").decode()
            form = "json_escaped" if esc != v and esc in bundle else "MISSING"
        if form == "MISSING":
            bad.append("%s value %r is not in the served bundle" % (k, v[:24]))
        rows.append({"key": k, "value": v, "value_chars": len(v), "has_cjk": bool(re.search(r"[一-鿿]", v)),
                     "match_form": form, "registry_collision": v in reg})

old_sites = [l for l in subprocess.run(["git", "-C", WT, "grep", "-n", "-e", "item.group",
                                         "HEAD", "--", "frontend/src/app/V8Experience.tsx"],
                                        capture_output=True, text=True).stdout.split("\n") if l.strip()]
RENDER_RAW = ">{item.group}<"
print("HEAD", head)
print("served_asset", asset, "bundle_raw_bytes", len(raw), "bundle_sha1",
      hashlib.sha1(raw).hexdigest())
print("pair_count_at_this_commit", len(pairs), "new_pairs", len(mine))
for r in rows:
    print("  %-16s value=%-9r value_chars=%d has_cjk=%s match_form=%s registry_collision=%s" % (
        r["key"], r["value"], r["value_chars"], r["has_cjk"], r["match_form"], r["registry_collision"]))
raw_renders = [l for l in old_sites if RENDER_RAW in l.replace(" ", "")]
through_t = [l for l in old_sites if "t(navGroupKey(item.group))" in l]
compares = [l for l in old_sites if l not in raw_renders and l not in through_t]
print("heading_sites_reading_the_raw_code=%d heading_sites_reading_the_dictionary=%d "
      "comparison_sites_that_must_keep_the_code=%d" % (len(raw_renders), len(through_t), len(compares)))
for l in old_sites:
    kind = "RAW" if l in raw_renders else ("DICTIONARY" if l in through_t else "COMPARISON")
    print("   %s %s" % (kind, l[-118:]))
if bad:
    print("REFUSING -- " + "; ".join(bad))
    sys.exit(1)
print("VERDICT ALL_FIVE_PAIRS_SHIP")
