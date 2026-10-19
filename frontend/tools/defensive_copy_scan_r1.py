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

The same mistake happened a second time inside the modules, and is why the readout counts values and
not files: five `*Copy.ts` files keep both languages inside one key (`poiImportCopy.ts`,
`collectionCopy.ts`, `mapPanelCopy.ts`, `footprintCopy.ts`, `checkinCopy.ts`) instead of one table per
locale, and the first version of this file read none of their sentences while still reporting the file
count. `--selftest` pins all three shapes.

Markers are deliberately blunt: they will also catch honest sentences that happen to use the words
("Nothing was written" is a fact when the reader needs to know the request did not land). That is
why the verdict column is the product of a measurement, not a filter that hides them.

Usage: python tools/defensive_copy_scan_r1.py [--limit N] [--selftest]
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
    "这一屏", "这屏", "这句不", "所以这里不", "所以这里没有", "this screen", "this line shows no",
    # Added 2026-10-19 after the entry-shaped modules went into the denominator: these are the
    # shapes those files write their self-justification in, and the list above did not see them.
    # `这一项` was tried here and taken out again: it matched two ordinary aria labels ("改这一项"),
    # which is a demonstrative, not a defence -- a marker that fires on normal wording makes every
    # later count unreadable.
    "不另起", "不替它", "这里不说", "这里不写", "不猜", "按状态拒绝", "与你的操作无关", "和你无关",
    "屏上不说", "no fourth word", "nothing is invented", "is not invented",
    "invented here", "we do not guess", "do not guess", "refuses by state", "this one refuses",
    "nothing is inferred", "no word is", "unrelated to you", "not because of you",
    # Added again the same day, from three sentences this file walked past while the campaign was
    # already deleting them: a promise about when the screen speaks, a claim about what it reads, and
    # a design policy stated on the user's face. A fixed vocabulary under-counts by construction -- the
    # header therefore reports what this list caught, never how many defensive sentences exist.
    "不是做完再说", "这句话现在说", "我们只读", "我们只", "让缺口有名字", "本部署自己的",
    "it is said now", "so the gap has a name", "we read only", "we only read",
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
    """Which locale a table opener names -- by exact match, not by prefix.

    This used to be `startswith("en")`, and `collectionCopy.ts` has a key called `entry`, so that one
    key was read as the English half of the file: two values landed under the wrong side and the rest
    of the file was skipped as "not a per-locale table". A prefix test on a name is a guess about a
    name; the vocabulary is four strings, so compare all four.
    """

    name = block.lower()
    if name in ("zh", "zh-cn"):
        return "zh"
    if name in ("en", "en-gb", "en-us"):
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


ENTRY_BLOCK = re.compile(r'^  (?:"(?P<q>[A-Za-z0-9_.\-]+)"|(?P<bare>[A-Za-z][\w.]*)):\s*\{\s*$')
ENTRY_BLOCK_INLINE = re.compile(
    r'^  (?:"(?P<q>[A-Za-z0-9_.\-]+)"|(?P<bare>[A-Za-z][\w.]*)):\s*\{\s*(?=\S)'
)
ENTRY_CLOSE = re.compile(r"^\s*\},?\s*$")
SIDE_PAIR = re.compile(r'(?P<side>"(?:en|zh|en-US|zh-CN)"|(?:en|zh|en-US|zh-CN))\s*:\s*(?P<value>"(?:[^"\\]|\\.)*")')


def has_locale_table(lines: list[str]) -> bool:
    """True when the file keeps one table per locale (`en: {`), which is what `parse_module` reads."""

    for line in lines:
        opened = COPY_BLOCK.match(line)
        if opened and side_of(opened.group("q") or opened.group("bare") or ""):
            return True
    return False


def parse_entries(lines: list[str]) -> list[tuple[str, str, str]]:
    """(side, key, value) for the modules that keep both languages inside one key instead of one
    table per locale: poiImportCopy.ts, collectionCopy.ts, mapPanelCopy.ts, footprintCopy.ts,
    checkinCopy.ts.

    This shape was not read at all by the first version of this ruler, which then printed "module
    copy files scanned: 19" -- a file count a reader naturally takes for coverage while five of those
    files were contributing nothing. Two sub-shapes are handled: a key whose `{` opens a block, and a
    key that opens and carries the first side on the same line (`noZoneHeading: { zh: "…",`). Comments
    are skipped, because these files quote `zh:` and `en:` shapes inside their own explanations.
    """

    rows: list[tuple[str, str, str]] = []
    entry: str | None = None
    in_comment = False
    for line in lines:
        stripped = line.strip()
        if in_comment:
            in_comment = "*/" not in line
            continue
        if stripped.startswith("//"):
            continue
        if stripped.startswith("/*"):
            in_comment = "*/" not in line
            continue
        opener = ENTRY_BLOCK.match(line) or ENTRY_BLOCK_INLINE.match(line)
        if opener:
            entry = opener.group("q") or opener.group("bare")
        elif ENTRY_CLOSE.match(line):
            entry = None
        if entry is None:
            continue
        for pair in SIDE_PAIR.finditer(line):
            side = side_of(pair.group("side").strip('"'))
            if side is None:
                continue
            rows.append((side, entry, pair.group("value")[1:-1].replace('\\"', '"')))
    return rows


POINTER = re.compile(
    r"上面|下面|上方|下方|左方|右方|上一格|下一格|左手边|右手边|\babove\b|\bbelow\b|the line above|the button below"
)


def dictionary_values() -> list[tuple[str, str, str]]:
    """(side, key, value) for the travel dictionary's two locale blocks."""

    lines = DICT.read_text(encoding="utf-8").split("\n")
    rows: list[tuple[str, str, str]] = []
    for side, (low, high) in blocks(lines).items():
        seen: set[str] = set()
        for line in lines[low:high]:
            match = KEY_LINE.match(line)
            if not match or match.group(1) in seen:
                continue
            seen.add(match.group(1))
            rows.append((side, match.group(1), match.group(2)))
    return rows


def layout_pointers() -> list[tuple[str, str, str, str]]:
    """(origin, side, key, value) for copy that points at the screen's own layout.

    The second disease this campaign serves, and it lives in the same ruler on purpose: a sentence may
    say what is on the screen and what the reader can do, but not where -- "the roster below",
    "the button below", "pick a trip above" are facts about this build's arrangement and survive a
    rearrangement only by luck. Both spellings of the Chinese word (上面 / 上方) are in the pattern
    because the first version searched one and let two sentences through a whole wave.
    """

    rows = [(DICT_LABEL, side, key, value) for side, key, value in dictionary_values() if POINTER.search(value)]
    rows += [(label, side, key, value) for label, side, key, value in module_copy() if POINTER.search(value)]
    return rows


def module_copy() -> list[tuple[str, str, str, str]]:
    """(file label, side, key, value) for every sentence in the feature copy modules, both shapes."""

    rows: list[tuple[str, str, str, str]] = []
    table_files = entry_files = 0
    for path in module_files():
        label = path.relative_to(FRONTEND).as_posix()
        lines = path.read_text(encoding="utf-8", errors="ignore").split("\n")
        table = parse_module(path)
        rows += [(label, side, key, value) for side, key, value in table]
        table_files += 1 if table else 0
        if has_locale_table(lines):
            continue
        extra = parse_entries(lines)
        rows += [(label, side, key, value) for side, key, value in extra]
        entry_files += 1 if extra else 0
    COVERAGE["table_files"] = table_files
    COVERAGE["entry_files"] = entry_files
    COVERAGE["values"] = len(rows)
    return rows


COVERAGE: dict[str, int] = {}


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


LIST_ITEM = re.compile(r'^[\s\t]*[\'"`]')
COMMENT = re.compile(r"^\s*(//|/\*|\*)")
DECL = re.compile(r"^(?:export\s+)?(?:const|let|var)\s+[A-Za-z_]\w*\b.*[:=]")
FORBIDDEN = re.compile(
    r"NEGATED|BANNED|FORBIDDEN|NOT_ALLOWED|DISALLOW|not\.to|must\s+not|may\s+not|不得|禁止|禁项", re.I
)


def _banned_by_a_check(body: str, sentence: str) -> bool:
    """True when every file that quotes this sentence quotes it as something that must NOT appear.

    A phrase can reach a check file in two opposite roles: demanded to be rendered, or listed so a
    gate can fail it when it is rendered. Reading the second as the first told me that the 回收站's
    "这一屏没有改动你的任何行程" was load-bearing, when `copyOnScreenCheck_r1.mjs` has it in the ban
    list precisely because the campaign retired that reassurance.
    """

    lines = body.split("\n")
    seen_any = False
    for index, line in enumerate(lines):
        if sentence not in line:
            continue
        seen_any = True
        if FORBIDDEN.search(line):
            continue
        opener = ""
        for back in range(index, -1, -1):
            candidate = lines[back]
            if COMMENT.match(candidate) or LIST_ITEM.match(candidate):
                continue
            opener = candidate.strip() if DECL.match(candidate) else ""
            break
        if not FORBIDDEN.search(opener):
            return False
    return seen_any


def asserted_elsewhere(sentence: str, own: str) -> tuple[list[str], list[str]]:
    """Files outside the dictionary and outside the candidate's own file: (demanded, forbidden).

    `own` matters now that the candidates come from the modules themselves: a module quote is the
    sentence under test, not a second writer of it. Without it every module candidate would be
    "asserted" by the very line it is being judged on.

    The two buckets exist because the campaign's own auditor learned the lesson twice: a spec that
    quotes a sentence inside a *ban* list demands the opposite of a spec that demands it be rendered.
    `tools/copyOnScreenCheck_r1.mjs` lists "这一屏没有改动你的任何行程" among the phrases that may NOT
    reach the screen, so counting that file as a writer of the demand would tell the next reader that
    the reassurance is load-bearing -- when it is exactly what the gate is waiting to catch.
    """

    if len(sentence) < 8:
        return [], []
    demanded: list[str] = []
    forbidden: list[str] = []
    for name, body in check_files():
        if name == own or sentence not in body:
            continue
        (forbidden if _banned_by_a_check(body, sentence) else demanded).append(name)
    for name, pieces in source_sentences().items():
        if sentence in pieces and name != own:
            demanded.append(name)
    return sorted(set(demanded)), sorted(set(forbidden))


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
    seen_key: set[tuple[str, str, str]] = set()
    for label, side, key, value in module_copy():
        if (label, side, key) in seen_key:
            continue
        seen_key.add((label, side, key))
        for sentence in sentences(value):
            hit = next((marker for marker in MARKERS if marker in sentence), None)
            if hit:
                rows.append((label, side, key, hit, sentence))
    return rows


def selftest() -> int:
    """Controls over the three module shapes and the marker list, on text typed here.

    This file's own history is the reason: it read one of the two module shapes for eight waves and
    printed a file count that looked like coverage. Each control below is a shape or a phrasing that
    exists in the tree, and a mutation of the reader or the vocabulary turns one of them RED -- the
    paired mutation script (`_copy_trim_door_mutate_r1.py` in the campaign scratch tree) is what proves
    that, not this list of strings.
    """

    table = [
        "export const accessCopy = {",
        "  en: {",
        '    "access.doorPresent":',
        '      "The server answered the doors. Nothing is invented by this reader.",',
        "  },",
        "};",
    ]
    blocks = [
        "export const poiImportCopy = {",
        "  exitStoreOnly: {",
        '    zh: "只存不排（测试字串）",',
        '    en: "Keep them without a day (test string)",',
        "  },",
        "  storeOnlyRefusal: {",
        '    zh: "这里不另起第三种说法（测试字串）。",',
        '    en: "No third word is invented here (test string), so this choice refuses.",',
        "  },",
        "};",
    ]
    inline = [
        "const COPY = {",
        '  noZoneHeading: { zh: "下面的印按本机钟排（测试字串）。",',
        '                   en: "The rows below follow this device clock (test string)." },',
        '  plain: { zh: "服务器答了 200。", en: "The server answered 200." },',
        "};",
    ]

    results: list[tuple[str, bool, str]] = []
    results.append(("a per-locale table file is recognised as a table", has_locale_table(table), str(has_locale_table(table))))
    results.append(("a per-key file is NOT mistaken for a table", not has_locale_table(blocks), str(has_locale_table(blocks))))
    entries = parse_entries(blocks)
    results.append(("both sides of a {zh, en} block are read",
                    {side for side, _, _ in entries} == {"zh", "en"} and len(entries) == 4, str(entries)[:60]))
    key_hit = [value for side, key, value in entries if key == "storeOnlyRefusal" and side == "en"]
    results.append(("the refusal sentence is attributed to its own key",
                    bool(key_hit) and key_hit[0].startswith("No third word"), str(key_hit)[:60]))
    flat = parse_entries(inline)
    results.append(("both languages inside one line are read (key: { zh: ..., en: ... } on one line)",
                    len(flat) == 4, str([(side, key) for side, key, _ in flat])[:64]))
    comments = parse_entries([
        "const X = {",
        "  a: {",
        '    zh: "真正的中文",',
        '    /* prose that quotes en: "not a value" */',
        "  },",
        "};",
    ])
    results.append(("a comment inside an entry is not read as a value",
                    all("not a value" not in value for _, _, value in comments), str(comments)[:60]))
    real = parse_module(FRONTEND / "src/features/access/accessCopy.ts")
    results.append(("the per-locale table shape is still read (accessCopy.ts on disk)",
                    len(real) > 200 and {side for side, _, _ in real} == {"en", "zh"}, "%d values" % len(real)))
    results.append(("a key named `entry` is not read as the English half of a table",
                    side_of("entry") is None and side_of("en") == "en" and side_of("en-US") == "en",
                    "entry=%s en=%s en-US=%s" % (side_of("entry"), side_of("en"), side_of("en-US"))))
    collected = parse_entries((SRC / "features/collections/collectionCopy.ts").read_text(encoding="utf-8").split("\n"))
    results.append(("collectionCopy.ts is read through the entry shape (it was the file the `entry` key hid)",
                    len(collected) >= 40 and {side for side, _, _ in collected} == {"en", "zh"},
                    "%d values" % len(collected)))
    per_file: dict[str, int] = {}
    for label, side, key, value in module_copy():
        name = label.split("/")[-1]
        per_file[name] = per_file.get(name, 0) + 1
    results.append(("the entry-shaped files reach the candidate list (module_copy wiring)",
                    per_file.get("poiImportCopy.ts", 0) >= 140 and per_file.get("mapPanelCopy.ts", 0) >= 60,
                    "poiImport=%s mapPanel=%s" % (per_file.get("poiImportCopy.ts"), per_file.get("mapPanelCopy.ts"))))
    hits = layout_pointers()
    results.append(("layout pointers are found in the tree, on both spellings of the word",
                    len(hits) >= 1 and any("上方" in value or "下面" in value or "above" in value or "below" in value
                                           for _, _, _, value in hits), "%d values still point" % len(hits)))
    pointing = sorted(key for _, _, key, value in hits if "上方" in value or "下面" in value)
    results.append(("the identity sentences this campaign cut are no longer among them",
                    all("identity" not in key for key in pointing), str(pointing)[:56]))
    dictionary_rows = dictionary_values()
    results.append(("the dictionary is read on both sides",
                    len(dictionary_rows) > 2000 and {side for side, _, _ in dictionary_rows} == {"en", "zh"},
                    "%d values" % len(dictionary_rows)))
    for text, want in [
        ("No third word is invented here, so this choice refuses.", True),
        ("这里不另起第三种说法。", True),
        ("这句话现在说，不是做完再说。", True),
        ("截图列着，让缺口有名字。", True),
        ("我们只读本地能读的文字。", True),
        ("The server answered 200 for this trip.", False),
    ]:
        hit = next((marker for marker in MARKERS if marker in text), None)
        results.append(("marker list %s a sentence of this shape" % ("catches" if want else "ignores"),
                        (hit is not None) == want, str(hit)))
    failed = [name for name, ok, _ in results if not ok]
    for name, ok, detail in results:
        print("%s | %s | %s" % ("PASS" if ok else "FAIL", name, detail))
    print("controls: {} | failed: {}".format(len(results), len(failed)))
    if failed:
        print("SELFTEST RED (rc 3): " + "; ".join(failed))
        return 3
    print("SELFTEST GREEN: all three module shapes are read and the vocabulary bites where it claims to.")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    limit = 40
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    rows = candidates()
    in_dictionary = sum(1 for row in rows if row[0] == DICT_LABEL)
    # Coverage, because "N files scanned" was read as "N files' copy judged" while five of those
    # files were contributing no sentences at all. These are counts of values that were parsed.
    print(
        "copy values read: {} (module files with per-locale tables {} / with per-key {{zh, en}} blocks {})".format(
            COVERAGE.get("values", 0), COVERAGE.get("table_files", 0), COVERAGE.get("entry_files", 0)
        )
    )
    print("module copy files in the tree:", len(module_files()))
    print(
        "copy sentences carrying a defensive / self-describing marker: {} "
        "(dictionary {} / module {})".format(len(rows), in_dictionary, len(rows) - in_dictionary)
    )
    shown = 0
    free = 0
    banned_only = 0
    for origin, side, key, marker, sentence in rows:
        own = "" if origin == DICT_LABEL else origin
        demanded, banned = asserted_elsewhere(sentence, own)
        if not demanded:
            free += 1
            if banned:
                banned_only += 1
        if shown >= limit:
            continue
        shown += 1
        detail = ""
        if demanded:
            detail = " <- " + ", ".join(demanded[:2])
        elif banned:
            detail = " <- banned by " + ", ".join(banned[:2])
        print(
            "  {origin} {side} {key} [{marker}] demanded: {verdict}{detail}".format(
                origin=origin, side=side, key=key, marker=marker,
                verdict="YES" if demanded else "no",
                detail=detail,
            )
        )
        print("      " + sentence[:150])
    print("----")
    print(
        "candidates: {} | shown: {} | not demanded by any check: {} (of which named in a ban list: {})".format(
            len(rows), shown, free, banned_only
        )
    )
    if shown < len(rows):
        print(f"NOTE: {len(rows) - shown} candidates were not printed -- raise --limit, this is not an empty list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
