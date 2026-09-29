# Before claiming "the label is not in the dictionary", print what the dictionary actually holds for
# that concept: every key whose name or Chinese value mentions theme/system, at the tip under test.
import re
import subprocess
import sys

REV = sys.argv[1]
src = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "show",
                      "%s:frontend/src/i18n/LocaleContext.tsx" % REV],
                     capture_output=True).stdout.decode("utf-8", "replace")
KEY = re.compile('^  "([a-z][A-Za-z0-9_]*(?:\\.[A-Za-z0-9_]+)+)": "((?:[^"\\\\]|\\\\.)*)",$', re.M)
i = src.index("const en: Dict = {")
j = src.index("const zhCN: Dict = {")
en = dict(KEY.findall(src[i:j]))
zh = dict(KEY.findall(src[j:src.index("\n};", j)]))
hits = sorted(k for k in en if re.search(r"theme|system|lang", k, re.I))
byvalue = sorted(k for k, v in zh.items() if "系统" in v or "主题" in v or "跟随" in v)
print(subprocess.run(["git", "-C", "D:/moodle/CityNexus", "grep", "-c", "-F", "跟随系统", REV, "--",
                      "frontend/src/i18n/LocaleContext.tsx"], capture_output=True, text=True).stdout.strip()
      or "grep 跟随系统 in LocaleContext.tsx: 0 hits")
print("keys whose NAME mentions theme/system/lang:", len(hits))
for k in hits[:12]:
    print("   ", k, "|", en[k][:44], "||", zh.get(k, "(absent)")[:44])
print("keys whose CHINESE value contains 系统/主题/跟随:", len(byvalue))
for k in byvalue[:12]:
    print("   ", k, "|", en[k][:44], "||", zh[k][:44])
