"""Regression arm: ORD-0549 -- PlanWithAiSheet's five named rows read keys the
dictionary already had.

MUTUALLY_EXCLUSIVE_VARIANT: 把本臂指回现尖（未改动的同代树）必须红。

用法：`python i18n_0549_plan_ai_arm_r1.py [tree_root]`
冻结量在两份旁边文件里：i18n_0549_plan_ai_expect.json（五枚改前的两臂字面）与
i18n_0549_plan_ai_denoms.json（改前的全树分母与字典行数字）。都由脚本从现尖字节抄出。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BS = chr(96)
CJK = re.compile(r"[一-鿿]")
DQ = r'"((?:[^"\\\n]|\\.)*)"'
TPL = BS + r"((?:[^\n]|\\.)*)" + BS
STR = r"(?:" + DQ + r"|" + TPL + r")"
PAIR = re.compile(r"\?\s*" + STR + r"\s*:\s*" + STR, re.S)
SINGLE = re.compile(r'zh \? "')
KEY = re.compile(r'^\s*"([A-Za-z0-9._-]+)"\s*:\s*"(.*)"\s*,?\s*$')

SHEET = "frontend/src/features/planning/PlanWithAiSheet.tsx"
STRIP = "frontend/src/features/planning/PlanAiRunStrip.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"

HERE = Path(__file__).resolve().parent
EXPECT = json.loads((HERE / "i18n_0549_plan_ai_expect.json").read_text(encoding="utf-8"))
DEN = json.loads((HERE / "i18n_0549_plan_ai_denoms.json").read_text(encoding="utf-8"))

if len(sys.argv) > 1:
    ROOT = Path(sys.argv[1]).resolve()
else:
    ROOT = Path(__file__).resolve().parents[2]


def read(rel):
    p = ROOT / rel
    if not p.exists():
        raise SystemExit("missing %s under %s" % (rel, ROOT))
    return p.read_text(encoding="utf-8")


def unescape(v):
    return v.replace('\\"', '"').replace("\\\\", "\\")


def dict_blocks(text):
    lines = text.split("\n")
    marks = [i for i, ln in enumerate(lines) if re.match(r"^const (en|zhCN): Dict", ln)]
    if len(marks) != 2:
        raise SystemExit("dictionary blocks=%d" % len(marks))
    out, counts = {}, {}
    for idx, start in enumerate(marks):
        lang = re.match(r"^const (\w+):", lines[start]).group(1)
        stop = marks[idx + 1] if idx + 1 < len(marks) else len(lines)
        rows = 0
        for i in range(start, stop):
            m = KEY.match(lines[i])
            if m:
                rows += 1
                out.setdefault(m.group(1), {}).setdefault(lang, (m.group(2), i + 1))
        counts[lang] = rows
    return out, counts


def cjk_pairs(text):
    hits = []
    for m in PAIR.finditer(text):
        a = m.group(1) if m.group(1) is not None else m.group(2)
        b = m.group(3) if m.group(3) is not None else m.group(4)
        if CJK.search(a or "") and not CJK.search(b or ""):
            hits.append((a, b))
    return hits


def tree_pair_hits(key, row):
    """Where in frontend/src a pair with this row's exact two arms still sits."""
    out = []
    for p in sorted((ROOT / "frontend/src").rglob("*.ts*")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        text = p.read_text(encoding="utf-8", errors="replace")
        for a, b in cjk_pairs(text):
            if a == row["inline_zh"] and b == row["inline_en"]:
                out.append(rel)
    return out


def main() -> int:
    sheet = read(SHEET)
    strip = read(STRIP)
    arms, counts = dict_blocks(read(DICT))
    checks = []

    def ck(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sheet_pairs = cjk_pairs(sheet)
    ck("本屏内联双语对少掉正好五处",
       len(sheet_pairs) == DEN["__base_sheet_cjk__"] - 5,
       "现读 %d 处，改前 %d 处" % (len(sheet_pairs), DEN["__base_sheet_cjk__"]))
    ck("单行形制 zh ? \" 也少五处",
       len(SINGLE.findall(sheet)) == DEN["__base_sheet_single__"] - 5,
       "现读 %d 处，改前 %d 处" % (len(SINGLE.findall(sheet)), DEN["__base_sheet_single__"]))

    for key, row in EXPECT.items():
        call = 't("%s")' % key
        ck("%s 被问到" % key, call in sheet, "读自本屏")
        gone = [(a, b) for a, b in sheet_pairs if a == row["inline_zh"] and b == row["inline_en"]]
        ck("%s 那对字面已不在本屏" % key, not gone, "残留 %d 处" % len(gone))
        both = arms.get(key)
        ck("%s 两臂齐" % key, bool(both) and "en" in both and "zhCN" in both,
           "en@%s zh@%s" % (both.get("en", (None,))[1] if both and "en" in both else "缺",
                            both.get("zhCN", (None,))[1] if both and "zhCN" in both else "缺"))
        if both and "en" in both and "zhCN" in both:
            ck("%s 两臂仍逐字等于改前那两句" % key,
               unescape(both["zhCN"][0]) == unescape(row["inline_zh"])
               and unescape(both["en"][0]) == unescape(row["inline_en"]),
               "字典 zh@%d en@%d，改前写在本屏第 %d 行"
               % (both["zhCN"][1], both["en"][1], row["tip_line"]))

    ck("statusCopy 收了取词函数",
       "t: (key: string, params?: Record<string, string | number>) => string," in sheet,
       "签名第 4 参数")
    ck("planCount 不再带默认值形制", "planCount = 0," not in sheet and "planCount: number," in sheet,
       "两枚调用点都显式给了它")
    four = len(re.findall(r'statusCopy\([^;]*\?\? 0, t\)', sheet)) + len(re.findall(r'statusCopy\([^;]*\?\? 0, t\)', strip))
    three = len(re.findall(r'statusCopy\([^;]*\?\? 0\)', sheet)) + len(re.findall(r'statusCopy\([^;]*\?\? 0\)', strip))
    ck("两处调用都传满四枚实参", four == 2 and three == 0, "四参 %d 处，三参 %d 处" % (four, three))
    ck("条带上本来就有取词函数", "const t = useT();" in strip, "读自 PlanAiRunStrip")

    consumers = []
    for p in sorted((ROOT / "frontend/src").rglob("*.ts*")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if rel in (SHEET, STRIP):
            continue
        if "statusCopy(" in p.read_text(encoding="utf-8", errors="replace"):
            consumers.append(rel)
    ck("statusCopy 的消费者只这两处", not consumers, "别处现读 %s" % (consumers or "无"))

    for key, row in EXPECT.items():
        hits = tree_pair_hits(key, row)
        outside = [h for h in hits if h != SHEET]
        want = DEN[key]["outside_sheet"]
        ck("反控：%s 别处存活 %d 处" % (key, want), len(outside) == want,
           "现读 %d 处 %s" % (len(outside), outside[:3] or "无"))

    for lang in ("en", "zhCN"):
        ck("字典 %s 臂没被本件加行" % lang, counts[lang] == DEN["dict_rows"][lang],
           "现读 %d 行，改前 %d 行" % (counts[lang], DEN["dict_rows"][lang]))

    width = max(len(n) for n, _o, _d in checks)
    bad = 0
    for name, ok, detail in checks:
        print("%s %-*s %s" % ("OK  " if ok else "FAIL", width, name, detail))
        bad += 0 if ok else 1
    print("checks=%d failed=%d" % (len(checks), bad))
    return 0 if bad == 0 else 1


sys.exit(main())
