"""ORD-0545 slice 2 -- move the whole POI-import sentence family out of the shared dictionary.

Ruled at 02:35 item 6: 整族入表, sequenced after the calendar-entry branch was pushed.  No new order
number was given, so this ships as the second slice of ORD-0545 and says so.

The family is 52 entries, not the 46 I first named from the screen, and the difference is the reason
this script exists instead of a search-and-replace: 45 keys appear at a `t("…")` call site, 6 more are
only ever reached through the module-level `FAILURE_SENTENCE` lookup (`t(FAILURE_SENTENCE[code])`), and
one key sits in both.  A regex over call sites would have moved 45 and silently orphaned 7 refusal
sentences -- the exact class of defect this family has now produced twice.

What the script refuses to do unless it can check it:

* it takes each sentence from the dictionary and puts the SAME string in the table, so the move is
  verbatim by construction, and it then compares the pair it removed against the pair it wrote;
* it strips the `poiImport.` prefix and aborts on any collision with a name the table already uses;
* it types `FAILURE_SENTENCE` as `Record<Failure["code"], PoiImportCopyKey>`, which is what turns a
  future orphaned refusal into a build failure instead of a missing sentence at run time;
* it removes the dictionary entries from BOTH books and checks the two books lose exactly the same
  52 keys;
* it asserts no `t(` call survives in the panel, and only then drops the now-unused `useT` binding;
* it introduces no CR into any of the three files (this line pins `.py`/sources to LF since ORD-0532).

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0545/move_family_r1.py --check   (dry)
    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0545/move_family_r1.py --apply
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PANEL = ROOT / "frontend/src/features/poiimport/PoiImportPanel.tsx"
TABLE = ROOT / "frontend/src/features/poiimport/poiImportCopy.ts"
DIC = ROOT / "frontend/src/i18n/LocaleContext.tsx"
PREFIX = "poiImport."

ENTRY_LINE = re.compile(r'^  "(poiImport\.[a-zA-Z0-9._]+)": "(.*)",$', re.M)
STATIC_CALL = re.compile(r'\bt\("(poiImport\.[a-zA-Z0-9._]+)"\)')
PARAM_CALL = re.compile(r'\bt\("(poiImport\.[a-zA-Z0-9._]+)", (\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\)')
TABLE_VALUE = re.compile(r'^\s*\w+: "(poiImport\.[a-zA-Z0-9._]+)",$', re.M)


def read(path: pathlib.Path) -> str:
    text = path.read_bytes().decode("utf-8")
    assert "\r" not in text, f"{path.name} holds CR; this line is LF"
    return text


def write(path: pathlib.Path, text: str, apply: bool) -> None:
    assert "\r" not in text, f"refusing to write a CR into {path.name}"
    if apply:
        path.write_bytes(text.encode("utf-8"))


def dictionary_entries(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = re.match(r'^  "(poiImport\.[a-zA-Z0-9._]+)": "(.*)",$', line)
        if match:
            out.setdefault(match.group(1), []).append(match.group(2))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    apply = args.apply and not args.check
    assert args.apply or args.check, "pass --apply or --check"

    panel, table, dic = read(PANEL), read(TABLE), read(DIC)

    static_keys = set(STATIC_CALL.findall(panel)) | {m[0] for m in PARAM_CALL.findall(panel)}
    table_keys = set(TABLE_VALUE.findall(panel))   # single group -> plain strings
    move = sorted(static_keys | table_keys)
    assert move, "no family found"
    entries = dictionary_entries(dic)
    assert all(len(entries.get(k, [])) == 2 for k in move), sorted(
        k for k in move if len(entries.get(k, [])) != 2)
    assert not any("{plural:" in "".join(entries[k]) for k in move), "a moved value carries a plural marker"

    short = {k: k[len(PREFIX):] for k in move}
    union_before = re.findall(r'\|\s*"([a-zA-Z]+)"', table.split("export type PoiImportCopyKey")[1].split(";")[0])
    clash = sorted(set(short.values()) & set(union_before))
    assert not clash, f"short names collide with the table's existing keys: {clash}"
    assert len(set(short.values())) == len(short), "two family keys collapse to one short name"

    # 1. the panel's own calls
    def replace_calls(text: str) -> str:
        text = PARAM_CALL.sub(lambda m: f'poiImportCopy(locale, "{short[m.group(1)]}", {m.group(2)})', text)
        text = STATIC_CALL.sub(lambda m: f'poiImportCopy(locale, "{short[m.group(1)]}")', text)
        # the two dynamic sites read the lookup table, so only the wrapper changes
        text = text.replace("t(FAILURE_SENTENCE[", "poiImportCopy(locale, FAILURE_SENTENCE[")
        return text

    panel_new = replace_calls(panel)
    panel_new = panel_new.replace(
        'const FAILURE_SENTENCE: Record<Failure["code"], string> = {',
        'const FAILURE_SENTENCE: Record<Failure["code"], PoiImportCopyKey> = {',
    )
    # the lookup table's values become the short names; each must occur exactly once, or the rewrite is
    # silently dropping a refusal sentence -- the failure mode this slice exists to avoid
    for key in sorted(table_keys):
        before = panel_new.count(f': "{key}",')
        assert before == 1, (key, before)
        panel_new = panel_new.replace(f': "{key}",', f': "{short[key]}",', 1)
    assert "t(FAILURE_SENTENCE[" not in panel_new
    assert not re.search(r"\bt\(", panel_new), "a t() call survived the move"
    panel_new = panel_new.replace("import { useT, useLocale }", "import { useLocale }")
    # the retyped lookup table names the key union, so the type has to be imported too
    assert panel_new.count('import { poiImportCopy } from "./poiImportCopy";') == 1
    panel_new = panel_new.replace(
        'import { poiImportCopy } from "./poiImportCopy";',
        'import { poiImportCopy, type PoiImportCopyKey } from "./poiImportCopy";',
        1,
    )
    assert "type PoiImportCopyKey" in panel_new
    panel_new = panel_new.replace("  const t = useT();\n", "")
    assert "useT" not in panel_new, "useT is imported or bound but nothing calls t() any more"

    # 2. the table gains the family, verbatim, and the union names them.  The anchor is the union's own
    # last member as it stands on this line -- slice 1 put `channelLocal` there -- so the rewrite fails
    # closed rather than silently no-oping if that tail moves again.
    union_anchor = '  | "channelLocal";\n'
    assert table.count(union_anchor) == 1, table.count(union_anchor)
    union_add = "".join(f'  | "{short[k]}"\n' for k in move[:-1])
    last = move[-1]
    table_new = table.replace(
        union_anchor,
        '  | "channelLocal"\n'
        "  /* ORD-0545 slice 2: the rest of this screen's sentences came over from the shared\n"
        "     dictionary, so one file owns them and a refusal sentence cannot be orphaned without the\n"
        "     build noticing.  The values are moved verbatim; see review/ord0545/move_family_r1.py. */\n"
        + union_add + f'  | "{short[last]}";\n',
        1,
    )
    assert table_new != table, "the union was not extended -- anchor moved"

    body = []
    for key in move:
        en_value, zh_value = entries[key]          # the English book comes first in the file
        body.append(
            f"  {short[key]}: {{\n"
            f'    zh: "{zh_value}",\n'
            f'    en: "{en_value}",\n'
            "  },\n"
        )
    table_new = table_new.replace("\n};\n\nexport function poiImportCopy(",
                                  "\n" + "".join(body) + "};\n\nexport function poiImportCopy(", 1)
    assert table_new.count("\n  channelLocal: {") == 1

    # 3. both books lose exactly the family
    removed: dict[str, int] = {}
    dic_lines = dic.splitlines(keepends=True)
    kept = []
    for line in dic_lines:
        match = ENTRY_LINE.match(line.rstrip("\n"))
        if match and match.group(1) in short:
            removed[match.group(1)] = removed.get(match.group(1), 0) + 1
            continue
        kept.append(line)
    assert all(removed.get(k) == 2 for k in move), sorted(k for k in move if removed.get(k) != 2)
    dic_new = "".join(kept)
    survivors = set(ENTRY_LINE.findall(dic_new))
    assert not (survivors & set(move)), sorted(survivors & set(move))

    summary = {
        "mode": "apply" if apply else "check-only",
        "family_keys_moved": len(move),
        "reached_from_a_call_site": len(static_keys),
        "reached_only_through_the_lookup_table": len(table_keys - static_keys),
        "reached_both_ways": sorted(table_keys & static_keys),
        "dictionary_lines_removed_per_book": {"en": len(move), "zh": len(move)},
        "table_keys_before": len(union_before),
        "table_keys_after": len(union_before) + len(move),
        "t_call_sites_left_in_panel": len(re.findall(r'\bt\(', panel_new)),
        "panel_lines": {"before": panel.count("\n"), "after": panel_new.count("\n")},
        "dictionary_lines": {"before": dic.count("\n"), "after": dic_new.count("\n")},
        "table_lines": {"before": table.count("\n"), "after": table_new.count("\n")},
        "moved_verbatim_pairs_checked": True,
    }
    # the strongest single claim here: every string removed from a book appears unchanged in the table
    for key in move:
        zh_value, en_value = entries[key][1], entries[key][0]
        assert f'\n    zh: "{zh_value}",\n' in table_new and f'\n    en: "{en_value}",\n' in table_new, key

    write(PANEL, panel_new, apply)
    write(TABLE, table_new, apply)
    write(DIC, dic_new, apply)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data/move_family_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if not apply:
        print("CHECK_ONLY: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
