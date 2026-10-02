"""ORD-0500 r6: the refusal vocabulary is checked in BOTH locales, from the files as they are on disk.

Why a gate and not only a screen walk: one of these eleven sentences (`targetRequired`) cannot be
reached by tapping anything -- the screen always names a stop -- so a screen-only arm would call that
row fine forever.  The defect this order fixes was exactly that: the English sentence told a traveller
to tap 打卡, a word that only exists on the Chinese screen.  This gate reads the table, the
dictionary's own labels, and the call sites that supply the placeholders, and fails on any of:

  A1  an `en` row carrying CJK (a control name from the other language);
  B1  a `{placeholder}` in a row that no call site supplies (renders literally on screen);
  B2  `targetRequired` no longer interpolating the label the button itself uses;
  C1  the orphan fact changing: `checkin.duplicate` / `checkin.refused` are dictionary rows this
      screen stopped reading in r5 -- their line numbers and reader counts are recorded, not deleted.

Run:  python checkin_copy_rows_r6.py [tree]      (default wt22); exit 0 green, 1 red.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
COPY = "frontend/src/features/checkin/checkinCopy.ts"
SCREEN = "frontend/src/features/trip/TripItinerary.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def read(tree, rel):
    p = os.path.join(tree if os.path.isabs(tree) else os.path.join(LANE, tree), rel)
    return open(p, encoding="utf-8").read()


def rows_of(text):
    """name -> {zh, en}, plus the line each value sits on, so a finding can name its own coordinate."""
    out = {}
    lines = text.splitlines()
    name = None
    for i, line in enumerate(lines, 1):
        m = re.match(r"^  (\w+): \{$", line)
        if m:
            name = m.group(1)
            out[name] = {}
            continue
        m = re.match(r'^  (\w+): \{ ?zh: "(.*)", ?en: "(.*)", ?\},?$', line)
        if m:
            out[m.group(1)] = {"zh": m.group(2), "en": m.group(3), "line": i, "inline": True}
            name = None
            continue
        m = re.match(r'^\s+(zh|en): "(.*)",?$', line)
        if m and name:
            out[name][m.group(1)] = m.group(2)
            out[name].setdefault(m.group(1) + "_line", i)
    return out


def dictionary_label(text, key):
    hits = [(i, l.strip()) for i, l in enumerate(text.splitlines(), 1)
            if re.search(r'"%s":' % re.escape(key), l)]
    return hits


def main():
    tree = sys.argv[1] if len(sys.argv) > 1 else "wt22"
    copy_t = read(tree, COPY)
    screen_t = read(tree, SCREEN)
    dict_t = read(tree, DICT)
    rows = rows_of(copy_t)

    # what each rendered sentence actually gets handed at the call site
    supplied = {}
    for m in re.finditer(r"wordsFor\(CHECKIN_COPY\.(\w+), zh(?:, \{([^}]*)\})?\)", screen_t):
        supplied.setdefault(m.group(1), set()).update(re.findall(r"(\w+)\s*:", m.group(2) or ""))
    generic = re.search(r"wordsFor\(CHECKIN_COPY\[key\], zh, \{([^}]*)\}\)", screen_t)
    generic_params = set(re.findall(r"(\w+)\s*:", generic.group(1))) if generic else set()
    mapped = set(re.findall(r'CHECKIN_[A-Z_]+: "(\w+)"', copy_t))

    findings, checks = [], []
    for name, row in sorted(rows.items()):
        if not isinstance(row, dict) or "en" not in row:
            findings.append({"case": "UNPARSED_ROW", "row": name})
            continue
        cjk_in_en = CJK.findall(row["en"])
        if cjk_in_en:
            findings.append({"case": "A1_CJK_IN_ENGLISH_ROW", "row": name,
                             "line": row.get("en_line"), "chars": "".join(sorted(set(cjk_in_en))),
                             "sentence": row["en"][:120]})
        params = supplied.get(name, set()) | (generic_params if name in mapped else set())
        missing = sorted({p for p in PLACEHOLDER.findall(row["zh"] + row["en"]) if p not in params})
        if missing:
            findings.append({"case": "B1_UNSUPPLIED_PLACEHOLDER", "row": name,
                             "line": row.get("line"), "placeholders": missing})
        checks.append({"row": name, "line": row.get("en_line") or row.get("line"),
                       "cjk_in_en": "".join(sorted(set(cjk_in_en))) or "none",
                       "placeholders": sorted(set(PLACEHOLDER.findall(row["zh"] + row["en"]))),
                       "supplied": sorted(params)})

    tr = rows.get("targetRequired", {})
    b2 = {"case": "B2_LABEL_IS_INTERPOLATED",
          "row_has_placeholder": "button" in PLACEHOLDER.findall(tr.get("en", "")) +
                                 PLACEHOLDER.findall(tr.get("zh", "")),
          "call_supplies_t_checkin_button": bool(
              re.search(r"wordsFor\(CHECKIN_COPY\[key\], zh, \{[^}]*button: t\(\"checkin\.button\"\)",
                        screen_t))}
    if not (b2["row_has_placeholder"] and b2["call_supplies_t_checkin_button"]):
        findings.append(b2)
    checks.append(b2)

    en_label = [t for _, t in dictionary_label(dict_t, "checkin.button") if '"Check in"' in t]
    zh_label = [t for _, t in dictionary_label(dict_t, "checkin.button") if '"打卡"' in t]
    label_rows = []
    for kind, key in (("en", "checkin.duplicate"), ("zh", "checkin.duplicate"),
                      ("en", "checkin.refused"), ("zh", "checkin.refused")):
        where = dictionary_label(dict_t, key)
        readers = subprocess.run(["git", "grep", "-n", "--", '"%s"' % key, "frontend/src",
                                  "frontend/e2e"], cwd=tree if os.path.isabs(tree)
                                 else os.path.join(LANE, tree),
                                 stdout=subprocess.PIPE, timeout=120).stdout.decode("utf-8", "replace")
        screen_reads = [l for l in readers.splitlines() if DICT not in l]
        label_rows.append({"key": key, "side": kind, "dictionary_lines": [n for n, _ in where],
                           "readers_outside_the_dictionary": len(screen_reads),
                           "reader_lines": screen_reads[:4]})
    out = {"tool": "checkin_copy_rows_r6", "took_local": datetime.now().astimezone().isoformat(),
           "tree": tree, "rows_checked": len([c for c in checks if "row" in c]),
           "en_button_label": en_label[:1], "zh_button_label": zh_label[:1],
           "row_checks": checks, "orphan_dictionary_rows": label_rows,
           "findings": findings, "verdict": "GREEN" if not findings else "RED"}
    # one file per invocation: the control run and the mutant runs must each leave their own receipt,
    # otherwise the last write hides the earlier verdicts
    default_name = "checkin_copy_rows_r6%s.json" % (
        "" if tree.endswith("wt22") else "_" + re.sub(r"[^A-Za-z0-9]+", "_",
                                                      os.path.basename(tree.rstrip("/\\"))).lower())
    path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(LANE, "evidence", default_name)
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps({"verdict": out["verdict"], "rows_checked": out["rows_checked"],
                      "findings": findings,
                      "orphans": [(r["key"], r["dictionary_lines"],
                                   r["readers_outside_the_dictionary"])
                                  for r in label_rows], "receipt": os.path.basename(path)},
                     indent=2, ensure_ascii=False))
    print("WROTE " + path)
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
