"""ORD-0553 arm, lane short-tiler (duanwagong).

Static arm over one product file: the batch-receipt row used to print the server's ISO instant
with the offset sliced off (`row.start_at.slice(0, 16).replace("T", " ")`).  It now goes through
the existing wrapper `formatWhen`.  Nothing here asserts a pixel; it asserts the reading path,
the timezone口径 declared at the call site, and that no dictionary key was invented for it.

The dictionary arm (A6) is the ORD-0533 B1 criterion lifted into this file: every key the panel
passes to `t()` must exist in BOTH books, with the denominator counted from the panel on every
run, so a sibling order adding a key cannot leave a stale hand-copied count behind.

Usage:
  python datefmt_0553_discovery_arm_r1.py                     # against this worktree
  python datefmt_0553_discovery_arm_r1.py --panel <path> --dict <path>   # negative control
Exit 0 = all assertions hold; exit 1 = at least one red; exit 2 = the ruler itself could not
read its inputs (that is not a pass).
"""
import argparse
import os
import re
import sys

PANEL_DEFAULT = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"
DICT_DEFAULT = "frontend/src/i18n/LocaleContext.tsx"

RAW_SLICE = re.compile(r'start_at\.slice\(0,\s*16\)\.replace\("T"')
FORMAT_WHEN_CALL = re.compile(
    r'formatWhen\(\s*row\.start_at\s*,\s*\{\s*zh:\s*locale\.startsWith\("zh"\)\s*,\s*'
    r'pending:\s*t\("inbox\.timePending"\)\s*\}'
)
DAYS_GROUP = re.compile(r'item\.start_at\.slice\(0,\s*10\)')
TITLE_ROW = re.compile(r'<b>\{row\.title\}</b>')
ID_ROW = re.compile(r'<small>\{row\.activity_id\}</small>')
ROW_TESTID = re.compile(r'data-testid="v13-discovery-batch-row"')
IMPORT_LINE = re.compile(r'^import \{ formatWhen \} from "\.\./\.\./lib/formatWhen";$', re.M)
T_CALL = re.compile(r'\bt\("([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)"')


def read(path):
    if not os.path.isfile(path):
        sys.stdout.write("RULER_CANNOT_READ: %s\n" % path)
        sys.exit(2)
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def dict_blocks(text):
    """Split LocaleContext.tsx into its two books by the declarations themselves."""
    start_en = text.index("const en: Dict = {")
    end_en = text.index("\n};", start_en)
    start_zh = text.index("const zhCN: Dict = {")
    end_zh = text.index("\n};", start_zh)
    return text[start_en:end_en], text[start_zh:end_zh]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=PANEL_DEFAULT)
    ap.add_argument("--dict", default=DICT_DEFAULT)
    args = ap.parse_args()

    panel = read(args.panel)
    books = read(args.dict)
    en_book, zh_book = dict_blocks(books)

    checks = []

    def add(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    panel_lines = panel.split("\n")

    # A1 -- the render path calls the wrapper.
    add("A1 row renders through formatWhen(row.start_at, ...)",
        bool(FORMAT_WHEN_CALL.search(panel)),
        "line %s" % (1 + next((i for i, l in enumerate(panel_lines) if FORMAT_WHEN_CALL.search(l)), 0)))

    # A2 -- the raw ISO slice no longer reaches the screen.
    add("A2 raw ISO slice off the screen path (count)",
        len(RAW_SLICE.findall(panel)) == 0,
        "hits=%d" % len(RAW_SLICE.findall(panel)))

    # A3/A4 -- both halves of the wrapper's口径 are stated at the call site, not assumed.
    add("A3 call site declares zh: locale.startsWith(\"zh\")",
        'zh: locale.startsWith("zh")' in panel)
    add("A4 call site names the fallback key inbox.timePending",
        'pending: t("inbox.timePending")' in panel)

    # A5 -- the wrapper really is the shared one, and it is imported, not re-declared here.
    add("A5 formatWhen imported from ../../lib/formatWhen",
        bool(IMPORT_LINE.search(panel)))

    # A6 -- ORD-0533 B1, applied to every key this panel reads.
    keys = sorted(set(T_CALL.findall(panel)))
    absent_en = [k for k in keys if '"%s":' % k not in en_book]
    absent_zh = [k for k in keys if '"%s":' % k not in zh_book]
    add("A6 every key this panel calls exists in both books",
        not absent_en and not absent_zh,
        "keys=%d missing_en=%s missing_zh=%s" % (len(keys), absent_en or "none", absent_zh or "none"))

    # A7 -- the inbox key the fallback uses exists in both books (it is reused, not minted).
    add("A7 inbox.timePending present in both books",
        '"inbox.timePending":' in en_book and '"inbox.timePending":' in zh_book)

    # A8 -- scope guard: the day grouping above the receipt was NOT touched.
    add("A8 day grouping still computed by slice(0, 10) (untouched)",
        len(DAYS_GROUP.findall(panel)) == 1,
        "hits=%d" % len(DAYS_GROUP.findall(panel)))

    # A9 -- the row's other two children and its test id are where they were.
    add("A9 row keeps title and activity id children plus its test id",
        len(TITLE_ROW.findall(panel)) == 1
        and len(ID_ROW.findall(panel)) == 1
        and len(ROW_TESTID.findall(panel)) == 1)

    # A10 -- no inline bilingual was introduced while moving the value.
    add("A10 no new inline zh-ternary on the time row",
        not re.search(r'zh \? "[^"]*" : "[^"]*"\s*\}\s*</span>', panel))

    red = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        sys.stdout.write("%s  %s%s\n" % ("PASS" if ok else "FAIL", name,
                                         ("  [%s]" % detail) if detail else ""))
    sys.stdout.write("ARM_SUMMARY total=%d red=%d\n" % (len(checks), len(red)))
    sys.stdout.write("DATEFMT0553_ARM_GREEN\n" if not red else "DATEFMT0553_ARM_RED\n")
    sys.exit(0 if not red else 1)


if __name__ == "__main__":
    main()
