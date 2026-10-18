"""What the inline-bilingual denominator actually counts, split by shape.

Why a second ruler instead of editing the first one. `tools/inline_bilingual_census_r1.py` counts
every `zh ? <string> : <string>` ternary as "a user-facing sentence written twice". Measured against
the tree, that is wrong in one direction that inflates the work and in one that hides it:

  * inflation: `dictionaryCopy(zh ? "zh-CN" : "en", key)` is a *locale selector*, not a sentence --
    the sentence is already in the dictionary. 27 of the sites r1 counted are of this shape, and in
    one file (features/agent/CopilotDock.tsx) every single site r1 reported is a locale selector.
  * a third shape r1 lumped in: punctuation-only pairs (`zh ? "。" : "."`), which are separator
    choices, not copy.

r1's own path is left untouched, because a published measurement tool must not be edited into
agreement with a claim. This file classifies, and the two numbers are reported side by side so the
difference is visible rather than argued about.

Self-check, because a classifier that silently loses a site is worse than the loose ruler it
replaces: the three buckets are required to sum to every match the loose pattern finds. If they do
not, this exits 3 and says which file it could not classify.

Usage: python tools/inline_bilingual_census_r2.py
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]
SRC = FRONTEND / "src"
DICT = SRC / "i18n" / "LocaleContext.tsx"

LOOSE = re.compile(r"zh\s*\?\s*([\"'`])((?:(?!\1)[\s\S]){0,400}?)\1\s*:\s*([\"'`])((?:(?!\3)[\s\S]){0,400}?)\3")
LOCALE_CODES = {"zh-CN", "zh", "en", "en-US", "zh_CN", "en_US"}
KEY_LINE = re.compile(r'^\s*"([^"]+)":', re.M)


def classify(left: str, right: str) -> str:
    pair = {left.strip(), right.strip()}
    if pair <= LOCALE_CODES:
        return "locale-selector"
    if all(len(item) <= 2 and not any("\u4e00" <= ch <= "\u9fff" or ch.isalpha() for ch in item)
           for item in (left.strip(), right.strip())):
        return "punctuation"
    return "sentence"


def block(text: str, start: str, end: str) -> str:
    return text[text.index(start) : text.index(end)]


def dictionary_duplicates() -> dict[str, list[str]]:
    text = DICT.read_text(encoding="utf-8")
    out = {}
    for locale, chunk in (
        ("en", block(text, "const en: Dict", "const zhCN: Dict")),
        ("zh", block(text, "const zhCN: Dict", "const dictionaries")),
    ):
        counts = collections.Counter(KEY_LINE.findall(chunk))
        out[locale] = sorted(key for key, seen in counts.items() if seen > 1)
    return out


def main() -> int:
    files = sorted(
        path for path in SRC.rglob("*") if path.is_file() and path.suffix in {".ts", ".tsx"}
    )
    rows = []
    totals = collections.Counter()
    unclassified = []
    for path in files:
        if path == DICT:
            continue
        body = path.read_text(encoding="utf-8", errors="ignore")
        buckets = collections.Counter()
        for match in LOOSE.finditer(body):
            kind = classify(match.group(2), match.group(4))
            if kind not in {"locale-selector", "punctuation", "sentence"}:
                unclassified.append(f"{path.relative_to(FRONTEND).as_posix()}: {kind}")
            buckets[kind] += 1
            totals[kind] += 1
        loose_count = len(LOOSE.findall(body))
        if sum(buckets.values()) != loose_count:
            unclassified.append(
                f"{path.relative_to(FRONTEND).as_posix()}: bucketed {sum(buckets.values())} "
                f"but the loose pattern found {loose_count}"
            )
        if buckets:
            rows.append((buckets["sentence"], path.relative_to(FRONTEND).as_posix(), buckets))

    print("inline bilingual ternary sites, classified (sentence sites are the ones that need keys):")
    for sentences, rel, buckets in sorted(rows, reverse=True):
        print(
            f"  {sentences:3d} sentence  {buckets['locale-selector']:2d} locale  "
            f"{buckets['punctuation']:2d} punctuation   {rel}"
        )
    print("----")
    print(f"files holding the practice: {len(rows)}")
    print(f"sentence sites (the work): {totals['sentence']}")
    print(f"locale-selector sites (not copy, already keyed): {totals['locale-selector']}")
    print(f"punctuation-only sites (separator choice): {totals['punctuation']}")
    print(f"loose total, the figure census_r1 reports: {sum(totals.values())}")
    dupes = dictionary_duplicates()
    print("duplicate dictionary keys (silently overwritten by the later entry):")
    for locale, keys in dupes.items():
        print(f"  {locale}: {len(keys)} {keys[:8]}")
    if unclassified:
        print("REFUSE (rc 3): the classifier did not account for every site:")
        for item in unclassified[:10]:
            print("  -", item)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
