"""ORD-0554 回归臂 · detail.* 命名域四枚死键成对删除。

MUTUALLY_EXCLUSIVE_VARIANT: 把本臂指到未删的同代树（现尖）必须红。

用法：`python deadkey_detail_arm_r1.py [tree_root]`

它守三件事：
  一、这四枚在两臂都没了，且除它们之外两臂各只少四行（不许顺手清别的）；
  二、整枚键名与键名末段在全树零引用（含中英两臂文本本身），所以没有任何呼点会读空、
      没有任何屏或 e2e 钉着这两句话；
  三、安全网：全树「被代码点名而两臂缺定义」的键数与删前同数，本刀没有新增裸键。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TARGETS = [
    "detail.nearbyNoteClose",
    "detail.nearbyNoteFar",
    "detail.progressDayTotal",
    "detail.weekIndex",
]
TEXTS = {
    "detail.nearbyNoteClose": ["都在约 {n} 米范围内，按直线距离排列。", "All within about {n} m, ordered by straight-line distance."],
    "detail.nearbyNoteFar": ["这些是同一行程的其他停靠点，不一定是步行可达的邻近地点。", "These are other stops on the same trip"],
    "detail.progressDayTotal": ["共 {n} 天。", "{n} days."],
    "detail.weekIndex": ["第 {n} 周", "Week {n}"],
}
# 冻结量，取自本车道在现尖 ee8b9c6bb 上现读的那一遍
BASE = {"en": 1139, "zh": 1140, "detail_en": 39, "bare_before": 50}
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
KEY = re.compile(r'^\s*"([A-Za-z0-9._-]+)"\s*:\s*"(.*)"\s*,?\s*$')

if len(sys.argv) > 1:
    ROOT = Path(sys.argv[1]).resolve()
else:
    ROOT = Path(__file__).resolve().parents[2]

WALK = ["frontend/src", "frontend/e2e", "backend", "tools", "contracts"]
COMMENT = re.compile(r"^\s*(//|\*|/\*)")


def dict_rows(text):
    lines = text.split("\n")
    marks = [i for i, ln in enumerate(lines) if re.match(r"^const (en|zhCN): Dict", ln)]
    if len(marks) != 2:
        raise SystemExit("dict blocks=%d" % len(marks))
    out = {}
    for idx, start in enumerate(marks):
        lang = re.match(r"^const (\w+):", lines[start]).group(1)
        stop = marks[idx + 1] if idx + 1 < len(marks) else len(lines)
        rows = {}
        for i in range(start, stop):
            m = KEY.match(lines[i])
            if m:
                rows.setdefault(m.group(1), i + 1)
        out[lang] = rows
    return out


def sources():
    for rel in WALK:
        base = ROOT / rel
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix in {".ts", ".tsx", ".js", ".cjs", ".mjs", ".py", ".json"}:
                yield p, p.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    dict_text = (ROOT / DICT_REL).read_text(encoding="utf-8")
    arms = dict_rows(dict_text)
    body = list(sources())
    checks = []

    def ck(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    for key in TARGETS:
        ck("%s 两臂都无" % key, key not in arms["en"] and key not in arms["zhCN"],
           "en@%s zh@%s" % (arms["en"].get(key, "无"), arms["zhCN"].get(key, "无")))
        hits = []
        for p, t in body:
            for n, ln in enumerate(t.split("\n"), 1):
                if COMMENT.match(ln):
                    continue
                if re.search(r'\b%s\b' % re.escape(key), ln):
                    hits.append("%s:%d" % (str(p.relative_to(ROOT)).replace("\\", "/"), n))
        ck("%s 全树整枚零引用（代码行）" % key, not hits, "现读 %d 处 %s" % (len(hits), hits[:2] or "无"))
        tail = key.rsplit(".", 1)[-1]
        thits = []
        for p, t in body:
            for n, ln in enumerate(t.split("\n"), 1):
                if COMMENT.match(ln):
                    continue
                if re.search(r"\b%s\b" % re.escape(tail), ln):
                    thits.append("%s:%d" % (str(p.relative_to(ROOT)).replace("\\", "/"), n))
        ck("%s 末段 %s 全树零引用（代码行）" % (key, tail), not thits, "现读 %d 处 %s" % (len(thits), thits[:2] or "无"))
        stale = [i + 1 for i, ln in enumerate((ROOT / DICT_REL).read_text(encoding="utf-8").split("\n"))
                 if COMMENT.match(ln) and re.search(r"\b%s\b" % re.escape(key), ln)]
        ck("%s 不再被字典注释点名" % key, not stale, "注释残留行 %s" % (stale or "无"))
        for idx, frag in enumerate(TEXTS[key]):
            khits = []
            for p, t in body:
                rel = str(p.relative_to(ROOT)).replace("\\", "/")
                if rel == "frontend/src/features/trip/activityDetailCopy.ts":
                    continue  # 同文对家，本来就该在，不是这枚字典键的呼点
                for n, ln in enumerate(t.split("\n"), 1):
                    if COMMENT.match(ln):
                        continue
                    if frag in ln:
                        khits.append("%s:%d" % (rel, n))
            label = "中文句" if idx == 0 else "英文句"
            ck("%s 的%s全树不再出现" % (key, label), not khits,
               "现读 %d 处 %s" % (len(khits), khits[:2] or "无"))

    ck("en 臂只少四行", len(arms["en"]) == BASE["en"] - 4, "现读 %d 枚，基线 %d 枚" % (len(arms["en"]), BASE["en"]))
    ck("zhCN 臂只少四行", len(arms["zhCN"]) == BASE["zh"] - 4, "现读 %d 枚，基线 %d 枚" % (len(arms["zhCN"]), BASE["zh"]))
    live_detail = [k for k in arms["en"] if k.startswith("detail.")]
    ck("detail.* 存活 35 枚", len(live_detail) == BASE["detail_en"] - 4,
       "现读 %d 枚，基线 %d 枚" % (len(live_detail), BASE["detail_en"]))
    for keep in ("detail.hoursProvided", "detail.hoursProviderText", "detail.rawFactsHeading", "detail.receiptLabel"):
        ck("反控存活 %s" % keep, keep in arms["en"] and keep in arms["zhCN"], "同域别枚没被顺手清")
    twin = (ROOT / "frontend/src/features/trip/activityDetailCopy.ts")
    ck("反控：同文对家仍在自己模块里", twin.exists() and "activity.otherStopsNote" in twin.read_text(encoding="utf-8"),
       "该屏读的是 activityDetailCopy 那枚，不是字典这枚")

    ns = {k.split(".", 1)[0] for k in arms["en"]} | {k.split(".", 1)[0] for k in arms["zhCN"]}
    refs = set()
    for p, t in body:
        if p.name == "LocaleContext.tsx":
            continue
        for m in re.finditer(r'"([a-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_-]+)+)"', t):
            if m.group(1).split(".", 1)[0] in ns:
                refs.add(m.group(1))
    bare = sorted(k for k in refs if k not in arms["en"] or k not in arms["zhCN"])
    ck("被点名而缺定义的键数与删前同数", len(bare) == BASE["bare_before"],
       "现读 %d 枚，基线 %d 枚；本刀新增 %d 枚" % (len(bare), BASE["bare_before"], len([k for k in bare if k in TARGETS])))

    width = max(len(n) for n, _o, _d in checks)
    bad = 0
    for name, ok, detail in checks:
        print("%s %-*s %s" % ("OK  " if ok else "FAIL", width, name, detail))
        bad += 0 if ok else 1
    print("checks=%d failed=%d" % (len(checks), bad))
    return 0 if bad == 0 else 1


sys.exit(main())
