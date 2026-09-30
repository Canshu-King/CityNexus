"""ORD-0504 -- the spend face's copy is a pair of real sentences, in both languages, in the served bytes.

Three claims, each read rather than asserted:

  1. every `spend.*` key exists on BOTH sides of `frontend/src/i18n/LocaleContext.tsx`, and neither
     side has a key the other lacks. A one-sided key is a runtime fallback to the key name, which is
     how a machine token reaches a Chinese screen (`t()` returns the key when it has no entry).
  2. every one of those values is present in the bundle the front is actually serving -- not in the
     source file. A dictionary entry that the build dropped, or that the served port is not carrying,
     is not copy a traveller can read.
  3. the parameter slots match: a sentence that takes `{value}` in English must take `{value}` in
     Chinese, or one of the two languages renders a hole.

    /d/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/spend_dictionary_check_r1.py
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
SOURCE = TREE / "frontend" / "src" / "i18n" / "LocaleContext.tsx"
FRONT = "http://127.0.0.1:4931"
OUT = TREE / "review" / "ord0504" / "spend_dictionary_check_r1.json"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

BLOCK = re.compile(r"const (en|zhCN): Dict = \{(.*?)\n\};", re.S)
ENTRY = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)",\s*$', re.M)
PARAM = re.compile(r"\{(\w+)\}")


def sides() -> tuple[dict[str, str], dict[str, str]]:
    text = SOURCE.read_text(encoding="utf-8")
    found: dict[str, dict[str, str]] = {}
    for name, body in BLOCK.findall(text):
        entries = {key: value for key, value in ENTRY.findall(body)}
        found[name] = {key: value for key, value in entries.items() if key.startswith("spend.")}
    if "en" not in found or "zhCN" not in found:
        raise SystemExit(f"REFUSE: did not find both dictionary blocks, saw {sorted(found)}")
    return found["en"], found["zhCN"]


def served_bytes() -> tuple[bytes, str]:
    with OPENER.open(FRONT + "/", timeout=60) as answer:
        shell = answer.read()
    entry = re.search(rb'src="(?:\./)?(/assets/index-[A-Za-z0-9_-]+\.js)"', shell)
    if entry is None:
        raise SystemExit("REFUSE: the served shell names no entry bundle")
    with OPENER.open(FRONT + entry.group(1).decode(), timeout=120) as answer:
        return answer.read(), entry.group(1).decode()


def main() -> int:
    en, zh = sides()
    bundle, asset = served_bytes()

    only_en = sorted(set(en) - set(zh))
    only_zh = sorted(set(zh) - set(en))
    # The value has to be findable in the bytes the port served. Quotes and escapes are the source's
    # spelling, not the bundle's, so the comparison is made on the unescaped text.
    def unescape(text: str) -> str:
        return text.replace('\\"', '"').replace("\\n", "\n")

    missing_en = sorted(key for key, value in en.items()
                        if unescape(value).encode("utf-8") not in bundle)
    missing_zh = sorted(key for key, value in zh.items()
                        if unescape(value).encode("utf-8") not in bundle)
    params_mismatched = sorted(
        key for key in set(en) & set(zh)
        if set(PARAM.findall(en[key])) != set(PARAM.findall(zh[key]))
    )
    # A key whose two sides are byte-identical and ASCII is a copy-paste, not a translation -- with one
    # named exception: a value that is nothing but a parameter slot has no words to translate. Two of
    # this order's keys are of that shape (`{label}` for a day heading, `{currency}` for a group
    # heading), and the text they carry is produced elsewhere, in the traveller's language already.
    only_a_slot = re.compile(r"\A\{\w+\}\Z")
    untranslated = sorted(key for key in set(en) & set(zh)
                          if en[key] == zh[key] and all(ord(char) < 128 for char in en[key])
                          and not only_a_slot.match(en[key]))

    ok = not (only_en or only_zh or missing_en or missing_zh or params_mismatched or untranslated)
    report = {
        "looked_at": {
            "source": str(SOURCE.relative_to(TREE)),
            "served_entry_asset": asset,
            "served_entry_bytes": len(bundle),
        },
        "keys_this_order_added": len(en),
        "dictionary_totals": {"en": len(en), "zh-CN": len(zh)},
        "one_sided_keys": {"en_only": only_en, "zh_only": only_zh},
        "values_not_found_in_the_served_bundle": {"en": missing_en, "zh": missing_zh},
        "parameter_slots_mismatched": params_mismatched,
        "identical_in_both_languages": untranslated,
        # Named rather than silently dropped, so the exemption can be argued with.
        "identical_because_only_a_parameter_slot": sorted(
            key for key in set(en) & set(zh)
            if en[key] == zh[key] and only_a_slot.match(en[key])
        ),
        "verdict": "ALL_SPEND_PAIRS_PRESENT_IN_BUNDLE" if ok else "RED",
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
