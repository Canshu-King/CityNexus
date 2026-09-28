# Does the delivered ORD-0422 dictionary work still hold at a tip that moved again under it?
# Compares, key by key, the 65 keys this order added against the live tip: present or not, same value
# or re-written by someone else, and what else the live tip changed in the same file. Read-only.
import json
import re
import subprocess
import sys

KEY = re.compile('^  "([a-z][A-Za-z0-9_]*(?:\\.[A-Za-z0-9_]+)+)": "((?:[^"\\\\]|\\\\.)*)",$', re.M)
REPO = "D:/moodle/CityNexus"
PATH = "frontend/src/i18n/LocaleContext.tsx"
DELIVERED = sys.argv[1]
LIVE = sys.argv[2]
ORDER_KEYS_FILE = sys.argv[3] if len(sys.argv) > 3 else None


def dicts(rev):
    src = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, PATH)],
                         capture_output=True).stdout.decode("utf-8")
    i = src.index("const en: Dict = {")
    j = src.index("const zhCN: Dict = {")
    return (dict(KEY.findall(src[i:j])), dict(KEY.findall(src[j:src.index("\n};", j)])))


pe, ze = dicts(DELIVERED)
le, lz = dicts(LIVE)
# Every key the delivered build carries must still be carried at the live tip, with the same wording;
# a key someone else re-worded is named rather than averaged away.
missing = sorted(set(pe) - set(le))
changed = sorted(k for k in set(pe) & set(le) if pe[k] != le[k] or ze.get(k) != lz.get(k))
added_by_others = sorted(set(le) - set(pe))
out = {
    "delivered_rev": DELIVERED,
    "live_rev": LIVE,
    "keys_delivered_en": len(pe),
    "keys_live_en": len(le),
    "delivered_keys_absent_at_live": len(missing),
    "absent_list": missing[:40],
    "delivered_keys_whose_value_changed_at_live": changed,
    "keys_live_has_that_delivered_did_not": len(added_by_others),
    "live_only_key_examples": added_by_others[:15],
    "zh_side_missing": sorted(set(ze) - set(lz)),
    "zh_side_changed": sorted(k for k in set(ze) & set(lz) if ze[k] != lz[k]),
}
print(json.dumps(out, ensure_ascii=False, indent=1))
