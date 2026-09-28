# Measures whether keeping the token "V14" on a Chinese screen follows the dictionary's own convention,
# instead of me declaring it a brand word from the armchair. Counts V1x tokens per side of every key.
import json
import re
import subprocess
import sys

sha = sys.argv[1]
src = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "show",
                      "%s:frontend/src/i18n/LocaleContext.tsx" % sha],
                     capture_output=True).stdout.decode("utf-8")
i = src.index("const en: Dict = {")
j = src.index("const zhCN: Dict = {")
key = re.compile('^  "([a-z][A-Za-z0-9_]*(?:\\.[A-Za-z0-9_]+)+)": "((?:[^"\\\\]|\\\\.)*)",$', re.M)
en = dict(key.findall(src[i:j]))
zh = dict(key.findall(src[j:src.index("\n};", j)]))
tok = re.compile(r"\bV1[0-9]\b")
en_v = {k for k, v in en.items() if tok.search(v)}
zh_v = {k for k, v in zh.items() if tok.search(v)}
both = sorted(en_v & zh_v)
dropped = sorted(en_v - zh_v)
out = {
    "sha": sha,
    "keys_total_en_zh": [len(en), len(zh)],
    "en_values_with_a_V1x_token": len(en_v),
    "zh_values_with_a_V1x_token": len(zh_v),
    "keys_where_both_sides_keep_the_token": len(both),
    "keys_where_en_has_it_and_zh_dropped_it": len(dropped),
    "kept_examples": [{"key": k, "en": en[k][:52], "zh": zh[k][:52]} for k in both][:12],
    "dropped_examples": [{"key": k, "en": en[k][:52], "zh": zh.get(k, "")[:52]} for k in dropped][:12],
    "zh_values_still_carrying_Edge": [k for k, v in zh.items() if "Edge" in v][:8],
}
print(json.dumps(out, ensure_ascii=False, indent=1))
