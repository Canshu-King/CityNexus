# Names the cause of the single value the copy ruler cannot find, so the number is not reported without
# its reason. Tests each candidate form of that string against the bytes the bundler actually emitted.
import codecs
import glob
import json
import re
import subprocess
import sys

REV = "7399f59ccdb2dfe3cdf04477d4e4ffcc077e214a"
KEY = "rank.loading"
src = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "show", "%s:frontend/src/i18n/LocaleContext.tsx" % REV],
                     capture_output=True).stdout.decode("utf-8")
lines = [l for l in src.splitlines() if '"%s"' % KEY in l]
print("dictionary lines carrying the key:", len(lines))
for l in lines:
    print("   ascii-escaped:", l.encode("ascii", "backslashreplace").decode("ascii")[:140])
vals = [m.group(1) for l in lines for m in [re.search(r'"%s": "((?:[^"\\]|\\.)*)"' % KEY, l)] if m]
print("raw values:", [v.encode("ascii", "backslashreplace").decode("ascii") for v in vals])

asset = glob.glob("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_q0422rescore/frontend/dist/assets/index-*.js")[0]
bundle = open(asset, "rb").read().decode("utf-8", "replace")
print("asset:", asset.rsplit("\\", 1)[-1], len(bundle), "decoded chars")
for v in vals:
    unescaped = codecs.decode(v, "unicode_escape") if "\\u" in v else v
    for label, probe in (("as written in source", v),
                         ("json-escaped form", json.dumps(v)[1:-1]),
                         ("python-unescaped form", unescaped)):
        print("   %-22s -> %s | present in bundle: %s (count %s)"
              % (label, probe.encode("ascii", "backslashreplace").decode("ascii")[:70],
                 probe in bundle, bundle.count(probe)))
i = bundle.find("Reading the plan")
print("bundle bytes at the site:", repr(bundle[i - 20:i + 40]) if i >= 0 else "absent")
print("uses outside i18n at this rev:")
for l in subprocess.run(["git", "-C", "D:/moodle/CityNexus", "grep", "-n", '-F', '"%s"' % KEY, REV,
                         "--", "frontend/src"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace").stdout.splitlines():
    print("   ", l[:150])
