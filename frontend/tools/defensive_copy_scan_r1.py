"""Where the travel dictionary still talks about itself, its own honesty, or the reader's blame.

The owner's instruction this serves: "make the UI simpler -- delete the unnecessary waffle, the
defensive statements and the unnecessary declarations". A message should carry the server's answer
and the reader's next action. It should not carry self-justification ("we would never invent ..."),
reassurance repeated across screens ("nothing was changed"), or a disclaimer about who is at fault.

This tool does not decide. It surfaces every dictionary value that contains one of the markers,
prints the sentence around it, and says whether that exact sentence is demanded elsewhere -- an e2e
spec, a repo ruler, or another module rendering it as its own sentence. A candidate with
`asserted: no` is safe to trim with the guarded writer; a candidate with `asserted: yes` is
load-bearing, and cutting it would turn a green suite red for a reason a human should agree to.

Markers are deliberately blunt: they will also catch honest sentences that happen to use the words
("Nothing was written" is a fact when the reader needs to know the request did not land). That is
why the verdict column is the product of a measurement, not a filter that hides them.

Usage: python tools/defensive_copy_scan_r1.py [--limit N]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]
SRC = FRONTEND / "src"
DICT = SRC / "i18n" / "LocaleContext.tsx"

MARKERS = (
    "我们不会", "不会编造", "不编造", "不是你的错", "不是你填", "无需担心", "不用担心", "放心",
    "请知悉", "如实", "没有改动", "不会被改动", "不会替你", "这不是", "而不是猜",
    "we will not", "we do not invent", "never invent", "not your fault", "do not worry",
    "rest assured", "nothing was changed", "was not changed", "this is not a",
    "no need to worry", "we are not guessing", "not a guess",
)

KEY_LINE = re.compile(r'^\s*"([A-Za-z0-9_.\-]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')


def blocks(lines: list[str]) -> dict[str, tuple[int, int]]:
    marks = {}
    for index, line in enumerate(lines):
        if line.startswith("const en: Dict"):
            marks["en"] = index
        elif line.startswith("const zhCN: Dict"):
            marks["zh"] = index
        elif line.startswith("const dictionaries"):
            marks["end"] = index
    if len(marks) != 3:
        raise SystemExit("dictionary layout changed: locale block anchors not found")
    return {"en": (marks["en"], marks["zh"]), "zh": (marks["zh"], marks["end"])}


def sentences(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[。；;.]|\s--\s", value) if part.strip()]


_CHECKS: list[tuple[str, str]] | None = None
_SOURCE_SENTENCES: dict[str, set[str]] | None = None


def check_files() -> list[tuple[str, str]]:
    """Every spec and ruler in the repo, read once -- this is asked about hundreds of times.

    This file is left out of its own index: a scanner quotes defensive phrasing as its vocabulary,
    and counting that vocabulary as "a check demands this sentence be rendered" would report every
    marker as load-bearing.
    """

    global _CHECKS
    if _CHECKS is None:
        _CHECKS = []
        for folder in ("e2e", "scripts", "tools"):
            for path in (FRONTEND / folder).rglob("*"):
                if (
                    path.is_file()
                    and path.suffix in {".ts", ".tsx", ".py", ".mjs"}
                    and not path.name.startswith("defensive_copy_scan")
                ):
                    _CHECKS.append(
                        (
                            path.relative_to(FRONTEND).as_posix(),
                            path.read_text(encoding="utf-8", errors="ignore"),
                        )
                    )
    return _CHECKS


def source_sentences() -> dict[str, set[str]]:
    """Sentences another module writes as its own literal, per file."""

    global _SOURCE_SENTENCES
    if _SOURCE_SENTENCES is None:
        _SOURCE_SENTENCES = {}
        for path in SRC.rglob("*"):
            if not path.is_file() or path.suffix not in {".ts", ".tsx"} or path == DICT:
                continue
            body = path.read_text(encoding="utf-8", errors="ignore")
            pieces = set()
            for literal in re.findall(r'"([^"\n]{8,})"|\'([^\'\n]{8,})\'|`([^`\n]{8,})`', body):
                text = next((group for group in literal if group), "")
                pieces.update(sentences(text))
            _SOURCE_SENTENCES[path.relative_to(FRONTEND).as_posix()] = pieces
    return _SOURCE_SENTENCES


def asserted_elsewhere(sentence: str) -> list[str]:
    """Files outside the dictionary that demand this exact sentence."""

    if len(sentence) < 8:
        return []
    hits = [name for name, body in check_files() if sentence in body]
    hits += [name for name, pieces in source_sentences().items() if sentence in pieces]
    return hits


def main() -> int:
    limit = 40
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    lines = DICT.read_text(encoding="utf-8").split("\n")
    ranges = blocks(lines)
    rows = []
    for locale, (low, high) in ranges.items():
        seen = set()
        for line in lines[low:high]:
            match = KEY_LINE.match(line)
            if not match:
                continue
            key, value = match.group(1), match.group(2)
            if key in seen:
                continue
            seen.add(key)
            for sentence in sentences(value):
                hit = next((marker for marker in MARKERS if marker in sentence), None)
                if hit:
                    rows.append((locale, key, hit, sentence))

    print("dictionary sentences carrying a defensive / self-describing marker:", len(rows))
    shown = 0
    for locale, key, marker, sentence in rows:
        if shown >= limit:
            break
        where = asserted_elsewhere(sentence)
        print(
            "  {locale} {key} [{marker}] asserted: {verdict}{detail}".format(
                locale=locale, key=key, marker=marker,
                verdict="YES" if where else "no",
                detail="" if not where else " <- " + ", ".join(sorted(set(where))[:2]),
            )
        )
        print("      " + sentence[:150])
        shown += 1
    free = sum(1 for locale, key, marker, sentence in rows if not asserted_elsewhere(sentence))
    print("----")
    print(f"candidates: {len(rows)} | shown: {shown} | not asserted anywhere: {free}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
