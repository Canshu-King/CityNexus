"""ORD-0407 点单一格 · main.tsx 那句硬码英文改读字典键的回归臂。

MUTUALLY_EXCLUSIVE_VARIANT: 指到未改动的同代树必须红。

用法：`python main_none_recorded_arm_r1.py [tree_root]`

它守五件事：那一行不再硬码且读的是点名的键；键在两臂都在、值逐字相同、在两臂共有序列
的同一位；那句英文在全树只剩字典那两行（屏上那枚不再抄着它）；两臂 main.* 各只多一枚
（没顺手清或加别的）；那处错位（unnamed 在 en 臂末、zh 臂首）还在原样，本件没挪它。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

KEY = "main.noneRecorded"
VALUE = "None recorded."
MISPLACED = "main.unnamedCommitmentServerGaveNoName"
ANCHOR = '"main.evidenceUnavailable"'
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
MAIN_REL = "frontend/src/main.tsx"
WALK = ["frontend/src", "frontend/e2e", "backend", "tools", "contracts", "review"]

if len(sys.argv) > 1:
    ROOT = Path(sys.argv[1]).resolve()
else:
    ROOT = Path(__file__).resolve().parents[2]

ROW = re.compile(r'^\s*"([A-Za-z0-9._-]+)"\s*:\s*"(.*)"\s*,?\s*$')


def arms_of(lines):
    marks = [i for i, ln in enumerate(lines) if re.match(r"^const (en|zhCN): Dict", ln)]
    if len(marks) != 2:
        raise SystemExit("dict blocks=%d" % len(marks))
    out = {}
    for idx, start in enumerate(marks):
        lang = re.match(r"^const (\w+):", lines[start]).group(1)
        stop = marks[idx + 1] if idx + 1 < len(marks) else len(lines)
        rows = []
        for i in range(start, stop):
            m = ROW.match(lines[i])
            if m:
                rows.append((m.group(1), m.group(2), i + 1))
        out[lang] = rows
    return out


def main() -> int:
    dlines = (ROOT / DICT_REL).read_text(encoding="utf-8").split("\n")
    arms = arms_of(dlines)
    mtext = (ROOT / MAIN_REL).read_text(encoding="utf-8")
    mlines = mtext.split("\n")
    checks = []

    def ck(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    site = [i + 1 for i, ln in enumerate(mlines) if "None recorded." in ln]
    ck("main.tsx 不再抄那句英文", not site, "硬码行现读 %s" % (site or "无"))
    called = [i + 1 for i, ln in enumerate(mlines) if 't("%s")' % KEY in ln]
    ck("那一处改读点名的键", len(called) == 1, "现读 %s" % (called or "无"))
    ck("取词函数在 LegacyApp 里就有", "const t = useT()" in mtext or "useT()" in mtext,
       "读自 %s" % MAIN_REL)

    pair = {}
    for lang, rows in arms.items():
        got = [(v, n) for k, v, n in rows if k == KEY]
        pair[lang] = got[0] if got else None
        ck("%s 臂有这枚键" % lang, bool(got), "行 %s" % (got[0][1] if got else "无"))
    if pair.get("en") and pair.get("zhCN"):
        ck("两臂值逐字相同", pair["en"][0] == pair["zhCN"][0] == VALUE,
           "en@%d=%r zh@%d=%r" % (pair["en"][1], pair["en"][0], pair["zhCN"][1], pair["zhCN"][0]))

    def common_pos(lang):
        seq = [k for k, _v, _n in arms[lang] if k.startswith("main.") and k != MISPLACED]
        return seq.index(KEY) + 1 if KEY in seq else -1

    pos = {lang: common_pos(lang) for lang in arms}
    ck("两臂共有序列同一位", pos["en"] > 0 and pos["en"] == pos["zhCN"],
       "en 第 %d 位、zh 第 %d 位" % (pos["en"], pos["zhCN"]))
    counts = {lang: sum(1 for k, _v, _n in arms[lang] if k.startswith("main.")) for lang in arms}
    ck("main.* 每臂各 22 枚（只多这一枚）", counts["en"] == 22 and counts["zhCN"] == 22,
       "en=%d zh=%d" % (counts["en"], counts["zhCN"]))
    anchor_rows = {lang: [n for k, _v, n in arms[lang] if ANCHOR.strip('"') == k] for lang in arms}
    nxt = {}
    for lang, rows in arms.items():
        seq = [k for k, _v, _n in rows if k.startswith("main.")]
        i = seq.index("main.evidenceUnavailable")
        nxt[lang] = seq[i + 1] if i + 1 < len(seq) else "(末尾)"
    ck("紧跟在 evidenceUnavailable 后同位插入",
       nxt["en"] == KEY and nxt["zhCN"] == KEY,
       "en 后一枚=%s zh 后一枚=%s" % (nxt["en"], nxt["zhCN"]))

    hits = {"dict": [], "product": [], "archive": []}
    for rel in WALK:
        base = ROOT / rel
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix not in {".ts", ".tsx", ".js", ".cjs", ".py", ".json", ".md"}:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            where = str(p.relative_to(ROOT)).replace("\\", "/")
            if where == "review/wenangong/main_none_recorded_arm_r1.py":
                continue
            for n, ln in enumerate(text.split("\n"), 1):
                if VALUE not in ln:
                    continue
                if where == DICT_REL:
                    hits["dict"].append("%s:%d" % (where, n))
                elif where.startswith("review/"):
                    hits["archive"].append("%s:%d" % (where, n))
                else:
                    hits["product"].append("%s:%d" % (where, n))
    ck("那句英文只剩字典两行", len(hits["dict"]) == 2 and not hits["product"],
       "字典 %d 行，产品码 %d 处 %s；review 存档另有 %d 处（别道抄的旧文件，不是呼点）"
       % (len(hits["dict"]), len(hits["product"]), hits["product"][:3] or "无", len(hits["archive"])))

    order = {lang: [k for k, _v, _n in arms[lang] if k == MISPLACED] and
             [i for i, (k, _v, _n) in enumerate([r for r in arms[lang] if r[0].startswith("main.")]) if k == MISPLACED][0]
             for lang in arms}
    ck("那枚错位的行还是原样（本件没挪）",
       order["en"] == 21 and order["zhCN"] == 0,
       "en 第 %d 位、zh 第 %d 位（0 是首枚）" % (order["en"], order["zhCN"]))

    width = max(len(n) for n, _o, _d in checks)
    bad = 0
    for name, ok, detail in checks:
        print("%s %-*s %s" % ("OK  " if ok else "FAIL", width, name, detail))
        bad += 0 if ok else 1
    print("checks=%d failed=%d" % (len(checks), bad))
    return 0 if bad == 0 else 1


sys.exit(main())
