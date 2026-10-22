"""Which of the shell's remaining inline bilingual pairs already have a dictionary twin?

Value equality, not substring: `还没有` lives inside a dozen longer sentences, and swapping one of
those in would silently change what the screen says.  So this indexes the dictionary's own zh values
and only reports a key when the whole string is equal.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

LC = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_bilingual_count_r1.py"
ROOT = Path(r"D:/moodle/_cmdr_ord0705_wt_1022/frontend/src")

spec = importlib.util.spec_from_file_location("bc", LC)
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)

src = (ROOT / "app/V8Experience.tsx").read_text(encoding="utf-8")
loc_lines = (ROOT / "i18n/LocaleContext.tsx").read_text(encoding="utf-8").splitlines()

entry = re.compile(r'^\s*"([^"]+)":\s*"(.*)",?\s*$')
zh_value_to_key: dict[str, str] = {}
en_value_by_key: dict[str, str] = {}
block = None
# The two blocks are `const en: Dict = {` and `const zhCN: Dict = {`; the type annotation sits
# between the name and the brace, so a pattern that requires `name = {` never fires and the whole
# index comes back empty -- which would read as "no twins exist" instead of "the probe was blind".
decl = re.compile(r"^const\s+(\w+)\s*(?::\s*\w+)?\s*=\s*\{")
for line in loc_lines:
    head = decl.match(line)
    if head:
        name = head.group(1)
        block = "en" if name.lower().startswith("en") else ("zh" if "zh" in name.lower() else None)
    match = entry.match(line)
    if not match or block is None:
        continue
    key, value = match.group(1), match.group(2)
    if block == "zh":
        zh_value_to_key.setdefault(value, key)
    else:
        en_value_by_key[key] = value
print("indexed zh values:", len(zh_value_to_key), "| en keys:", len(en_value_by_key))

exact = []
pairs = []
for hit in bc.TERN.finditer(src):
    a, b = hit.group(1), hit.group(2)
    if bool(bc.CJK.search(a)) == bool(bc.CJK.search(b)):
        continue
    zh = (a if bc.CJK.search(a) else b).strip('"').strip("'")
    en = (b if bc.CJK.search(a) else a).strip('"').strip("'")
    line = src[: hit.start()].count("\n") + 1
    pairs.append((line, zh, en))
    key = zh_value_to_key.get(zh)
    if key:
        exact.append((line, key, zh, en, en_value_by_key.get(key)))

print("counted inline bilingual pairs in this file:", len(pairs))
print("pairs whose zh value equals a dictionary entry exactly:", len(exact))
for line, key, zh, en, dict_en in exact:
    same_en = dict_en is not None and dict_en.strip('"') == en
    print("  line {0:>5}  key {1:<28}  zh={2!s:<26}  en_also_equal={3}".format(
        line, key, zh[:26], same_en
    ))
    if not same_en:
        print("        dict en:", (dict_en or "<none>")[:70])
        print("        inline en:", en[:70])
