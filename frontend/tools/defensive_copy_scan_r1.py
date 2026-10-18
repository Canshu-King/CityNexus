"""Where the product copy still talks about itself, its own honesty, or the reader's blame.

The owner's instruction this serves: "make the UI simpler -- delete the unnecessary waffle, the
defensive statements and the unnecessary declarations". A message should carry the server's answer
and the reader's next action. It should not carry self-justification ("we would never invent ..."),
reassurance repeated across screens ("nothing was changed"), or a disclaimer about who is at fault.

This tool does not decide. It surfaces every copy value that contains one of the markers -- in the
travel dictionary (`src/i18n/LocaleContext.tsx`) *and* in the 19 `*Copy.ts` feature dictionaries that
carry the same kind of sentence outside it -- prints the sentence, and says whether that exact
sentence is demanded elsewhere: an e2e spec, a repo ruler, or another module writing it as its own
sentence. A candidate with `asserted: no` is safe to trim with the guarded writer; a candidate with
`asserted: YES` is load-bearing, and cutting it would turn a green suite red for a reason a human
should agree to.

The module dictionaries are in the denominator because they are where the copy actually moved: the
campaign trimmed `LocaleContext.tsx` for eight waves while `features/access/accessCopy.ts` and
`features/estimation/estimationLadderCopy.ts` went uns scanned, and both of them carry the exact
"so this screen declines to ..." shape this file was written to find. A ruler that reads only the
shared dictionary reports a clean UI it has not looked at.

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
DICT_LABEL = "dictionary"

MARKERS = (
    "我们不会", "不会编造", "不编造", "不是你的错", "不是你填", "无需担心", "不用担心", "放心",
    "请知悉", "如实", "没有改动", "不会被改动", "不会替你", "这不是", "而不是猜",
    "we will not", "we do not invent", "never invent", "not your fault", "do not worry",
    "rest assured", "nothing was changed", "was not changed", "this is not a",
    "no need to worry", "we are not guessing", "not a guess",
    "so this screen", "so this line", "so nothing is", "so there is no figure",
    "这一屏不", "这句不", "所以这里不", "所以这里没有",
)

KEY_LINE = re.compile(r'^\s*"([A-Za-z0-9_.\-]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')

# A feature copy module opens a locale table at two-space indent: `  en: {` or `  "zh-CN": {`,
# closes it at two-space indent with `}`, and writes its sentences four spaces in -- with the value
# either on the key's own line or folded onto the next one.
COPY_BLOCK = re.compile(r'^  (?:"(?P<q>[A-Za-z][\w-]*)"|(?P<bare>[A-Za-z][\w-]*)):\s*\{\s*$')
COPY_CLOSE = re.compile(r"^\}\s*,?\s*$|^  \}?,?\s*$")
COPY_PAIR = re.compile(
    r'^\s{4}(?:"(?P<dq>[A-Za-z0-9_.\-]+)"|\'(?P<sq>[A-Za-z0-9_.\-]+)\'|(?P<bare>[A-Za-z][\w.]*)):\s*(?P<rest>.*)$'
)
COPY_VALUE = re.compile(
    r'^\s*(?:"(?P<dq>(?:[^"\\]|\\.)*)"|\'(?P<sq>(?:[^\'\\]|\\.)*)\'|`(?P<tick>(?:[^`\\]|\\.)*)`)\s*,?\s*$'
)


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


def side_of(block: str) -> str | None:
    name = block.lower()
    if name.startswith("zh"):
        return "zh"
    if name.startswith("en"):
        return "en"
    return None


def module_files() -> list[Path]:
    return sorted(
        path
        for path in SRC.rglob("*Copy.ts")
        if path.is_file() and ".test." not in path.name and ".spec." not in path.name
    )


def parse_module(path: Path) -> list[tuple[str, str, str]]:
    """(side, key, value) for every string in a feature copy module's locale tables."""

    rows: list[tuple[str, str, str]] = []
    side: str | None = None
    pending: str | None = None
    for line in path.read_text(encoding="utf-8", errors="ignore").split("\n"):
        if pending is not None:
            value = COPY_VALUE.match(line)
            if value:
                rows.append((side or "?", pending, next(g for g in value.groups() if g)))
                pending = None
                continue
            pending = None
        opened = COPY_BLOCK.match(line)
        if opened:
            side = side_of(opened.group("q") or opened.group("bare") or "")
            continue
        if re.match(r"^  \}", line):
            side = None
            continue
        if side is None:
            continue
        pair = COPY_PAIR.match(line)
        if not pair:
            continue
        key = pair.group("dq") or pair.group("sq") or pair.group("bare")
        rest = pair.group("rest").strip()
        if not rest:
            pending = key
            continue
        value = COPY_VALUE.match(rest)
        if value:
            rows.append((side, key, next(g for g in value.groups() if g)))
    return rows


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


def asserted_elsewhere(sentence: str, own: str) -> list[str]:
    """Files outside the dictionary and outside the candidate's own file that demand this sentence.

    `own` matters now that the candidates come from the modules themselves: a module quote is the
    sentence under test, not a second writer of it. Without it every module candidate would be
    "asserted" by the very line it is being judged on.
    """

    if len(sentence) < 8:
        return []
    hits = [name for name, body in check_files() if sentence in body]
    hits += [name for name, pieces in source_sentences().items() if sentence in pieces]
    return [name for name in sorted(set(hits)) if name != own]


def candidates() -> list[tuple[str, str, str, str, str]]:
    """(origin, side, key, marker, sentence) for every copy value that carries a marker."""

    rows: list[tuple[str, str, str, str, str]] = []
    lines = DICT.read_text(encoding="utf-8").split("\n")
    for side, (low, high) in blocks(lines).items():
        seen: set[str] = set()
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
                    rows.append((DICT_LABEL, side, key, hit, sentence))
    for path in module_files():
        label = path.relative_to(FRONTEND).as_posix()
        seen_key: set[tuple[str, str]] = set()
        for side, key, value in parse_module(path):
            if (side, key) in seen_key:
                continue
            seen_key.add((side, key))
            for sentence in sentences(value):
                hit = next((marker for marker in MARKERS if marker in sentence), None)
                if hit:
                    rows.append((label, side, key, hit, sentence))
    return rows


def main() -> int:
    limit = 40
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    rows = candidates()
    in_dictionary = sum(1 for row in rows if row[0] == DICT_LABEL)
    print("module copy files scanned:", len(module_files()))
    print(
        "copy sentences carrying a defensive / self-describing marker: {} "
        "(dictionary {} / module {})".format(len(rows), in_dictionary, len(rows) - in_dictionary)
    )
    shown = 0
    for origin, side, key, marker, sentence in rows:
        if shown >= limit:
            break
        own = "" if origin == DICT_LABEL else origin
        where = asserted_elsewhere(sentence, own)
        print(
            "  {origin} {side} {key} [{marker}] asserted: {verdict}{detail}".format(
                origin=origin, side=side, key=key, marker=marker,
                verdict="YES" if where else "no",
                detail="" if not where else " <- " + ", ".join(where[:2]),
            )
        )
        print("      " + sentence[:150])
        shown += 1
    free = sum(
        1 for origin, side, key, marker, sentence in rows
        if not asserted_elsewhere(sentence, "" if origin == DICT_LABEL else origin)
    )
    print("----")
    print(f"candidates: {len(rows)} | shown: {shown} | not asserted anywhere: {free}")
    if shown < len(rows):
        print(f"NOTE: {len(rows) - shown} candidates were not printed -- raise --limit, this is not an empty list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
