"""ORD-0485 lane tool: which t("...") keys are missing from the dictionaries, and which of
those are provably ON SCREEN in this lane's 390x844 readings.

`t(key)` answers with the key itself when the dictionary has no entry, so a missing key is a
machine word on the traveller's screen.  A name-only grep over the source cannot tell a live
leak from a dormant one, so this tool joins the gap list with the rendered text captured by
walk_phone_r2 and reports both halves.
"""
import json
import os
import re
import sys

SRC = r"D:/moodle/_qoder_phone_ord0485_20260930/export/frontend/src"
WALK = r"D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_r2/walk_r2.json"
OUT = r"D:/moodle/_qoder_phone_ord0485_20260930/evidence/i18n_gap_r1.json"

DICT = os.path.join(SRC, "i18n", "LocaleContext.tsx")

key_line = re.compile(r'^\s*"([A-Za-z0-9_.\-]+)"\s*:')
ref = re.compile(r'\bt\(\s*"([A-Za-z0-9_.\-]+)"\s*[,)]')


def load_dictionary_blocks():
    """Range the two word tables by their own literal openers, not by repeated-key guessing.

    LocaleContext.tsx holds `const en: Dict = {` and `const zhCN: Dict = {`; the range of each
    table is the line after its opener up to the next table's opener.  t() falls back
    en -> key, so a key missing from BOTH tables is the one shape that reaches the screen
    dressed as a machine word.
    """
    lines = open(DICT, encoding="utf-8").read().splitlines()
    openers = {}
    for i, line in enumerate(lines, start=1):
        m = re.match(r"^const (en|zhCN): Dict = \{\s*$", line)
        if m:
            openers.setdefault(m.group(1), i)
    if set(openers) != {"en", "zhCN"}:
        raise SystemExit("ABORT_DICTIONARY_OPENERS_NOT_FOUND " + json.dumps(openers))
    order = sorted(openers.items(), key=lambda kv: kv[1])
    blocks = {}
    for idx, (name, start) in enumerate(order):
        stop = order[idx + 1][1] if idx + 1 < len(order) else len(lines)
        table = {}
        for n in range(start + 1, stop):
            m = key_line.match(lines[n - 1])
            if m:
                table.setdefault(m.group(1), []).append(n)
        blocks[name] = table
    return blocks, len(lines)


def references():
    out = {}
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d not in ("node_modules",)]
        for f in files:
            if not f.endswith((".ts", ".tsx")):
                continue
            p = os.path.join(root, f)
            if p == DICT:
                continue
            try:
                text = open(p, encoding="utf-8").read()
            except Exception:
                continue
            for n, line in enumerate(text.splitlines(), start=1):
                for m in ref.finditer(line):
                    out.setdefault(m.group(1), []).append(
                        "%s:%d" % (p.replace(SRC, "frontend/src").replace("\\", "/"), n))
    return out


def main():
    blocks, dict_lines = load_dictionary_blocks()
    names = sorted(blocks)
    if len(names) != 2:
        print(json.dumps({"ABORT": "DICTIONARY_BLOCKS_NOT_TWO", "found": names}))
        return 3
    a, b = blocks["en"], blocks["zhCN"]
    refs = references()
    missing_a = sorted(k for k in refs if k not in a)
    missing_b = sorted(k for k in refs if k not in b)
    missing_both = sorted(set(missing_a) & set(missing_b))

    walk = json.load(open(WALK, encoding="utf-8"))
    on_screen = {}
    for s in walk["screens"]:
        text = s.get("rendered_text_head") or ""
        for k in missing_both:
            if k in text:
                on_screen.setdefault(k, []).append(s["arm"])

    result = {
        "tool": "i18n_key_gap_r1",
        "dictionary_file": "frontend/src/i18n/LocaleContext.tsx",
        "dictionary_line_count": dict_lines,
        "table_block_names": names,
        "keys_in_en": len(a),
        "keys_in_zhCN": len(b),
        "referenced_key_count": len(refs),
        "referenced_keys_missing_from_en": len(missing_a),
        "referenced_keys_missing_from_zhCN": len(missing_b),
        "referenced_keys_missing_from_both": len(missing_both),
        "missing_from_both": [
            {"key": k, "call_sites": refs[k][:6],
             "on_screen_arms": on_screen.get(k, [])}
            for k in missing_both
        ],
        "missing_from_zh_only_falls_back_to_english": sorted(set(missing_b) - set(missing_a)),
        "missing_from_en_only": sorted(set(missing_a) - set(missing_b)),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(result, indent=2, ensure_ascii=False)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
