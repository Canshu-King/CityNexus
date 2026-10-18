"""Two numbers this frontend cannot currently state for itself.

1. INLINE BILINGUAL DENOMINATOR. How many user-facing sentences are still written twice, in
   two languages, inside a component. The shipped pairs ruler only sees the backticked
   `zh ? \`..\` : \`..\`` shape; the plain-string and multi-line shapes are its blind spot, so
   a green pairs ruler does not mean the practice is gone. This counts all three shapes,
   per file, so the work can be sized instead of argued about.

2. DUPLICATE DICTIONARY KEYS. `LocaleContext.tsx` is one object literal per locale, so a
   repeated key silently overwrites the first one -- the parity ruler compares the two sides
   by *parsed dictionary*, and a duplicate is invisible there because both sides collapse the
   same way. TypeScript catches it (TS1117) but nothing reported how many were already there.
   This tool caught one such collision the hard way: a key added here duplicated
   `stay.priceUnavailable`, and `npm run typecheck` was the only thing that said so.

Report-only: it exits 0 with findings printed, because a census that fails the build invites
people to silence the census. Numbers are read from the tree at run time.

Usage: python tools/inline_bilingual_census_r1.py
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]
SRC = FRONTEND / "src"
DICT = SRC / "i18n" / "LocaleContext.tsx"

# A ternary choosing between two languages, in any of the shapes components actually use.
SHAPES = (
    ("backticked-pair", re.compile(r"zh\s*\?\s*`[^`]*`\s*:\s*`[^`]*`", re.S)),
    ("plain-string-pair", re.compile(r"zh\s*\?\s*[\"'][^\"']*[\"']\s*:\s*[\"'][^\"']*[\"']", re.S)),
    ("keyed-but-hardcoded", re.compile(r"zh\s*\?\s*[\u4e00-\u9fff]")),
)
KEY_LINE = re.compile(r'^\s*"([^"]+)":', re.M)


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
    total = 0
    rows = []
    for path in files:
        if path == DICT:
            continue
        body = path.read_text(encoding="utf-8", errors="ignore")
        counts = {name: len(pattern.findall(body)) for name, pattern in SHAPES}
        # `keyed-but-hardcoded` is a subset of the pair shapes: count each site once.
        sites = counts["backticked-pair"] + counts["plain-string-pair"]
        if sites:
            total += sites
            rows.append((sites, path.relative_to(FRONTEND).as_posix(), counts))

    print("inline bilingual sentences written in components (sites -> file):")
    for sites, rel, counts in sorted(rows, reverse=True):
        print(
            f"  {sites:3d}  {rel}  "
            f"[backticked={counts['backticked-pair']} plain={counts['plain-string-pair']}]"
        )
    print(f"files still holding the practice: {len(rows)}")
    print(f"sites total: {total}")
    print()
    dupes = dictionary_duplicates()
    print("duplicate dictionary keys (silently overwritten by the later entry):")
    for locale, keys in dupes.items():
        print(f"  {locale}: {len(keys)} {keys[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
