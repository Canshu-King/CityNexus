"""Which copy keys does the product never read?

Why this exists: a sentence can be trimmed to perfection and still be invisible, if nothing renders it.
`src/i18n/agentWorkFeedCopy.ts` carries `sheetLede`, whose "Nothing is inferred" clause this campaign
shortened -- and the panel that owns that sheet never asks for the key; the lede a traveller sees comes
from `derivedRule` instead. That was found by hand, once. A dead key is not harmless: the next reader
edits it believing a screen shows it, which is how a copy campaign starts grading a document instead of
a product.

What counts as a reader: any live line that names the key -- `t("nav.trash")`, `copy("noRunHint")`,
`agentWorkCopy(locale, "entryTrip")`, `plan.unreachableBody` reached as a member. Lines that are the
key's own table entry, a `| "key"` member of a union type, or a comment are definitions and prose, not
uses, and are stripped before the question is asked. That bias can only cost a false "dead", never a
false "read", so each reported orphan is meant to be looked at, not deleted on the strength of this
file alone.

Keys a dynamic composition could reach (`t("nav." + key)`) are never called dead: they are counted as
unknowable and printed, because "0 dead keys" from a scan that cannot see that door would be a lie of
the kind this campaign has been busy catching elsewhere.

Usage: python tools/copy_orphan_keys_r1.py [--selftest] [--limit N]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]
SRC = FRONTEND / "src"
DICT = SRC / "i18n" / "LocaleContext.tsx"

DICT_BLOCK = re.compile(r"^const (en|zhCN): Dict")
MODULE_TABLE = re.compile(r'^\s{0,4}(?:"(en|zh|zh-CN|en-US)"|(en|zh)):\s*\{\s*$')
ENTRY = re.compile(r'^\s*(?:"(?P<q1>[A-Za-z0-9_.\-]+)"|(?P<q2>[A-Za-z][\w]*)):\s*(?:"|\'|`|_)')
UNION = re.compile(r'^\s*\|\s*"?[A-Za-z0-9_.\-]+"?')
COMMENT = re.compile(r"^\s*(//|/\*|\*)")
TABLE_CLOSE = re.compile(r"^\s{0,4}\}")


def dictionary_keys() -> dict[str, list[str]]:
    if not DICT.exists():
        return {}
    found: dict[str, list[str]] = {}
    inside = False
    for line in DICT.read_text(encoding="utf-8").split("\n"):
        if DICT_BLOCK.match(line):
            inside = True
            continue
        if line.startswith("const dictionaries"):
            inside = False
        match = ENTRY.match(line) if inside else None
        if match:
            found.setdefault(match.group("q1") or match.group("q2"), []).append(str(DICT))
    return found


def source_files() -> list[Path]:
    return sorted(p for p in SRC.rglob("*") if p.is_file() and p.suffix in {".ts", ".tsx"})


def module_keys() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in source_files():
        if path == DICT or not path.name.endswith("Copy.ts"):
            continue
        in_table = False
        for line in path.read_text(encoding="utf-8", errors="ignore").split("\n"):
            if MODULE_TABLE.match(line):
                in_table = True
                continue
            if TABLE_CLOSE.match(line):
                in_table = False
                continue
            match = ENTRY.match(line) if in_table else None
            if match:
                found.setdefault(match.group("q1") or match.group("q2"), []).append(str(path))
    return found


def read_uses(body: str, key: str, defining_here: bool) -> bool:
    """Does this file *use* the key, once its own definitions and prose are removed?"""

    quoted = re.compile(r'["\'`]' + re.escape(key) + r'["\'`]')
    member = re.compile(r"\b" + re.escape(key) + r"\b\s*[:(\[],]")
    for line in body.split("\n"):
        if COMMENT.match(line) or UNION.match(line):
            continue
        if defining_here and ENTRY.match(line):
            continue
        if quoted.search(line) or member.search(line):
            return True
    return False


def dynamic_prefixes(files: dict[str, str]) -> list[str]:
    prefixes: set[str] = set()
    pattern = re.compile(r'["\']([A-Za-z0-9_.\-]+\.)["\']\s*\+')
    for body in files.values():
        prefixes.update(pattern.findall(body))
    return sorted(prefixes)


VARIABLE_SUBSCRIPT = re.compile(r"\w+\[\s*[A-Za-z_]\w*\s*\]")


def variable_indexed_files(files: dict[str, str]) -> set[str]:
    """Files that look a key up from a runtime value instead of a literal.

    `prepFailureCopy.ts` answers a server reason code -- `START_COPY[job.status]` -- so its keys never
    appear as source literals and a literal-only scan would call all of them dead. Those keys are put
    in a third bucket rather than judged: a table reached by a server's own word is reachable, but a
    key in it that no caller and no server contract names is still suspicious, and the report says so.
    """

    return {path for path, body in files.items() if VARIABLE_SUBSCRIPT.search(body)}


def selftest() -> int:
    """Four readings that must all go the right way before a clean report means anything."""

    cases = [
        ("a key passed to a helper is a reader",
         read_uses('const x = () => copy("noRunHint");\n', "noRunHint", False), True),
        ("the key's own table line is not a reader",
         read_uses('  noRunHint: "Nothing here is inferred",\n', "noRunHint", True), False),
        ("a union type listing the key is not a reader",
         read_uses('export type K =\n  | "noRunHint";\n', "noRunHint", False), False),
        ("a comment naming the key is not a reader",
         read_uses('// sheetLede used to be rendered here\n', "sheetLede", False), False),
    ]
    for name, got, want in cases:
        print(("PASS " if got == want else "FAIL ") + name + " (got %r want %r)" % (got, want))
    files = {"a": 'const f = (k: string) => t("nav." + k);\n'}
    prefixes = dynamic_prefixes(files)
    print("PASS dynamic prefix discovered" if prefixes == ["nav."] else "FAIL dynamic prefix", prefixes)
    if any(got != want for _, got, want in cases) or prefixes != ["nav."]:
        print("REFUSE (rc 4): the classifier does not discriminate; an orphan list means nothing.")
        return 4
    return 0


def inventory() -> dict:
    """The counts, as data -- so a second tool can watch them without re-implementing this rule.

    Two tools re-deriving "which copy key has no reader" is two tools that can disagree, and the one
    that is wrong is the one nobody notices.
    """

    files = {str(path): path.read_text(encoding="utf-8", errors="ignore") for path in source_files()}
    keys = dictionary_keys()
    keys.update(module_keys())
    prefixes = dynamic_prefixes(files)

    read: dict[str, bool] = {}
    for key, defining in keys.items():
        read[key] = any(read_uses(body, key, path in defining) for path, body in files.items())

    # A table is either addressed by literals the callers write, or by a value that only exists at
    # run time (a server reason code). The difference decides whether a key nobody names is dead or
    # simply unreachable by this scan, and it is read from the data: if no key of that file is ever
    # written as a literal, the file cannot be judged by literal search at all.
    by_file: dict[str, list[str]] = {}
    for key, defining in keys.items():
        for path in defining:
            by_file.setdefault(path, []).append(key)
    # A file whose tables are indexed by a value (`arm[code]`, `table[key]`) can be addressed without
    # any source literal, so a key with no literal is only *suspicious* there -- the server's own word
    # may name it. That is what `prepFailureCopy.ts:107` is (`return code ? arm[code] : arm[kind]`,
    # where no file ever writes the string "EMPTY_QUERY"): a literal-only scan would have called six
    # live keys dead, which is the mistake this ruler exists to avoid rather than repeat.
    runtime_keyed = {path for path in by_file if VARIABLE_SUBSCRIPT.search(files[path])}

    dynamic = {k for k in keys if any(k.startswith(prefix) for prefix in prefixes)}
    judged_dead = [k for k, defining in keys.items() if not read[k] and not runtime_keyed.intersection(defining)]
    dead = sorted(k for k in judged_dead if k not in dynamic)
    suspect = sorted(k for k, defining in keys.items() if not read[k] and runtime_keyed.intersection(defining))
    return {
        "keys": keys,
        "dead": dead,
        "suspect": suspect,
        "prefixes": prefixes,
        "runtime_keyed": runtime_keyed,
        "dynamic": len(dynamic),
        "inventoried": len(keys),
        "files": len({p for paths in keys.values() for p in paths}),
    }


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    limit = 40
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    seen = inventory()
    keys, dead, suspect, prefixes, runtime_keyed = (
        seen["keys"], seen["dead"], seen["suspect"], seen["prefixes"], seen["runtime_keyed"]
    )

    print("copy keys inventoried:", seen["inventoried"], "across", seen["files"], "files")
    print("dynamic prefixes seen (their keys are not judged):", ", ".join(prefixes) or "(none)")
    print("keys reachable through one of those prefixes:", seen["dynamic"])
    print("files whose tables a run-time value could address (a literal scan cannot judge them):",
          ", ".join(sorted(Path(p).name for p in runtime_keyed)) or "(none)")
    print("   keys with no literal anywhere, but such a file owns them (SUSPECT, not dead):", len(suspect))
    for key in suspect[:10]:
        print("     ?", key, "<=", Path(keys[key][0]).name)
    print("keys no product file names as a literal, in a file whose callers do write literals:", len(dead))
    print("   (that is the only bucket this file calls dead; every entry still wants a reader's eye)")
    for key in dead[:limit]:
        print("   ", key, "<=", Path(keys[key][0]).name)
    if len(dead) > limit:
        print("   ... {} more; raise --limit, this is not the whole list.".format(len(dead) - limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
