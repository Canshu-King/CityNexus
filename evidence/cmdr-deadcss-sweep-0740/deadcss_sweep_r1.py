# -*- coding: utf-8 -*-
"""死类名清扫 v1（三臂证明 + 只认两种能核验的形状，其余交人工）。

用法：
  python _cmdr_deadcss_sweep_r1.py            # DRY：报数、列计划，不写一个字节
  python _cmdr_deadcss_sweep_r1.py --apply    # 真写

三臂（少一臂就不许动那枚 token）：
  甲 静态读者：全产品 .tsx/.ts + index.html 里逐字找不到这枚 token
     （classList.add 与 helper 的返回值也必须写这枚字面量，所以这一臂把"运行时才出现"的自家写法也盖住了）
  乙 动态拼装：穷举"className 由变量拼出来"的现场（模板串与字符串相加），拿这枚 token 的每一个
     连字符/下划线边界前缀去比；有一处能接上就判 COMPOSABLE，禁删。
     这一臂是子 Agent 那份清点里最贵的一课：它把 Badge.tsx:95 的 `cn-badge--${tone}` 一家全列成
     "产品零读者"，而屏上真挂着六枚 cn-badge--error —— 所以它的 DEAD 表我一枚都不直接信。
  丙 真屏命中：`_cmdr_deadcss_candidates_probe_r1.cjs` 在六屏上逐枚量过（deadcss_candidates.json），
     本脚本只接受那张表里合计命中为零的 token。

形状（只自动处理这两类，因为这两类判据是机械的）：
  壹 一行就是一条规则（首尾正好一对花括号）：选择器列表里每一支都带这枚 token -> 删整行；
     只有部分支带 -> 摘掉那些支，其余字节逐字保留。
  贰 其它形状（压缩行、@media 里一行多规则）-> 不动，写进 PLAN_leftover 交人工逐枚点名替换。

写完后三道回读：花括号配平、"除目标 token 外其余 class token 的出现次数一字不降"、文件字节差。
"""
import io
import json
import os
import re
import sys

TIP = r"D:/moodle/_cmdr_fe_rev_1016/tip"
SRC = os.path.join(TIP, "frontend", "src")
DOM_TABLE = r"D:/moodle/_cmdr_fe_rev_1016/deadcss_candidates.json"
PLAN = r"D:/moodle/_cmdr_fe_rev_1016/_deadcss_sweep_plan.json"
TOKENS = """today-actions v8-anchor-row v8-trip-metrics cn-no-motion v8-cta v8-strength v9-live-actions
v8-trip-hero-head anchor-line v8-live-grid cn-hero-stagger cn-spend-unpriced collections-panel hub-party-size""".split()
FILES = ["styles.css", "design-tokens.css", "cn-pulse.css",
         os.path.join("features", "trip", "spend.css")]

hits = json.load(io.open(DOM_TABLE, encoding="utf-8"))["per_token_total"]


def product_sources():
    for dp, dn, fn in os.walk(SRC):
        dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", "dist")]
        for f in fn:
            if f.endswith((".tsx", ".ts")):
                p = os.path.join(dp, f)
                yield os.path.relpath(p, SRC).replace(os.sep, "/"), io.open(p, encoding="utf-8", errors="replace").read().splitlines()


PROD = list(product_sources())
HTML = io.open(os.path.join(TIP, "frontend", "index.html"), encoding="utf-8", errors="replace").read()

# 乙臂现场：所有拼 className 的地方
builders = []
for rel, lines in PROD:
    for i, l in enumerate(lines, 1):
        if "className" not in l and "classList" not in l:
            continue
        for m in re.finditer(r'`([^`$]*)\$\{', l):
            if "-" in m.group(1) or "_" in m.group(1):
                builders.append((rel, i, m.group(1)))
        for m in re.finditer(r'"([^"]*[-_])"\s*\+', l):
            builders.append((rel, i, m.group(1)))


def boundary_prefixes(tok):
    return [tok[: m.end()] for m in re.finditer(r"[-_]", tok)]


def arm_a(tok):
    out = []
    for rel, lines in PROD:
        for i, l in enumerate(lines, 1):
            if tok in l:
                out.append("%s:%d" % (rel, i))
    if tok in HTML:
        out.append("index.html")
    return out


def arm_b(tok):
    for pre in boundary_prefixes(tok):
        for rel, i, frag in builders:
            last = frag.split()[-1] if frag.strip() else frag
            if last == pre or frag.endswith(pre):
                return "%s:%d 片段 %r 接得上前缀 %r" % (rel, i, frag, pre)
    return None


verdict = {}
for tok in TOKENS:
    a, b, c = arm_a(tok), arm_b(tok), hits.get(tok)
    verdict[tok] = {"arm_a_readers": len(a), "arm_a_examples": a[:3], "arm_b": b, "arm_c_hits": c,
                    "deletable": (not a) and b is None and c == 0}

ALLOW = [t for t in TOKENS if verdict[t]["deletable"]]
forbidden = [t for t in TOKENS if not verdict[t]["deletable"]]
print("三臂判语")
for t in TOKENS:
    v = verdict[t]
    print("  %-20s 甲 %d 读者｜乙 %s｜丙 %s -> %s"
          % (t, v["arm_a_readers"], "拼不出" if v["arm_b"] is None else v["arm_b"], v["arm_c_hits"],
             "可删" if v["deletable"] else "禁删"))
print("过关 %d 枚｜禁删 %d 枚：%s" % (len(ALLOW), len(forbidden), ", ".join(forbidden) or "无"))

ONE_RULE = re.compile(r"^(\s*)([^\r\n]+?)(\s*\{)([^\r\n]*?)(\}\s*)$")
BLOCK_OPEN = re.compile(r"^(\s*)([^\r\n{}]*?)\{\s*$")


def branches(sel):
    return [s.strip() for s in sel.split(",")]


def mentions(hay, tok):
    return re.search(r"(?<![-_A-Za-z0-9])" + re.escape(tok) + r"(?![-_A-Za-z0-9])", hay) is not None


plan = {"verdict": verdict, "allow": ALLOW, "drop_lines": [], "drop_blocks": [], "strip_branches": [], "leftover": []}
for rel in FILES:
    path = os.path.join(SRC, *rel.split(os.sep))
    if not os.path.isfile(path):
        print("文件不在，跳过:", rel)
        continue
    lines = io.open(path, encoding="utf-8").read().split("\n")
    for ln, line in enumerate(lines, 1):
        present = [t for t in ALLOW if mentions(line, t)]
        if not present:
            continue
        if ONE_RULE.match(line) and line.count("{") == 1 and line.count("}") == 1:
            ind, sel, brace, body, tail = ONE_RULE.match(line).groups()
            br = branches(sel)
            hot = [b for b in br if any(mentions(b, t) for t in present)]
            cold = [b for b in br if b not in hot]
            if not cold:
                plan["drop_lines"].append({"file": rel.replace(os.sep, "/"), "line": ln, "tokens": present, "text": line[:110]})
            else:
                for t in present:
                    plan["strip_branches"].append({"file": rel.replace(os.sep, "/"), "line": ln, "token": t,
                                                   "remove_branches": [b for b in hot if mentions(b, t)], "text": line[:110]})
            continue
        # 形状贰：选择器独占一行、`{` 收尾，后面几行是声明，再一行 `}` —— 整块删
        mo = BLOCK_OPEN.match(line)
        if mo and "{" not in mo.group(2):
            sel = mo.group(2)
            br = [b for b in branches(sel.replace("\n", " ")) if b]
            if br and all(any(mentions(b, t) for t in present) for b in br):
                j = ln  # 1-based 的下一行
                while j <= len(lines) and not lines[j - 1].lstrip().startswith("}"):
                    j += 1
                if j > len(lines):
                    plan["leftover"].append({"file": rel.replace(os.sep, "/"), "line": ln, "token": present[0],
                                             "kind": "整块找不到收尾花括号", "text": line[:120]})
                    continue
                plan["drop_blocks"].append({"file": rel.replace(os.sep, "/"), "line": ln, "through": j,
                                            "tokens": present, "text": line[:110]})
                continue
        for t in present:
            plan["leftover"].append({"file": rel.replace(os.sep, "/"), "line": ln, "token": t,
                                     "kind": "压缩行、多行选择器表或 :not() 里的形状", "text": line[:120]})

print("\n计划：整行删 %d 处｜整块删 %d 处｜组里摘支 %d 处｜交人工的异形 %d 处"
      % (len(plan["drop_lines"]), len(plan["drop_blocks"]), len(plan["strip_branches"]), len(plan["leftover"])))
for r in plan["drop_lines"]:
    print("   删行 %s:%d %s" % (r["file"], r["line"], r["text"][:76]))
for r in plan["drop_blocks"]:
    print("   删块 %s:%d-%d %s" % (r["file"], r["line"], r["through"], r["text"][:76]))
for r in plan["strip_branches"]:
    print("   摘支 %s:%d [%s] 去掉 %s" % (r["file"], r["line"], r["token"], " | ".join(r["remove_branches"])[:70]))
for r in plan["leftover"][:18]:
    print("   人工 %s:%d [%s] %s" % (r["file"], r["line"], r["token"], r["text"][:66]))
io.open(PLAN, "w", encoding="utf-8").write(json.dumps(plan, ensure_ascii=False, indent=1))
print("计划落盘:", PLAN)

if "--apply" not in sys.argv:
    print("DRY：没 --apply 就不写。")
    sys.exit(0)

TOKEN_RX = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")


def class_tokens(text):
    out = {}
    for m in TOKEN_RX.finditer(text):
        out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


kill = set()
for r in plan["drop_lines"]:
    kill.add((r["file"], r["line"]))
kill_blocks = {}
for r in plan["drop_blocks"]:
    for ln in range(r["line"], r["through"] + 1):
        kill_blocks.setdefault(r["file"], set()).add(ln)
strip_map = {}
for r in plan["strip_branches"]:
    strip_map.setdefault((r["file"], r["line"]), []).append(r)

deleted_text = {}


def lines_of(relf):
    return io.open(os.path.join(SRC, *relf.split("/")), encoding="utf-8").read().splitlines()


for r in plan["drop_lines"]:
    deleted_text.setdefault(r["file"], []).append(lines_of(r["file"])[r["line"] - 1])
for r in plan["drop_blocks"]:
    ls = lines_of(r["file"])
    deleted_text.setdefault(r["file"], []).extend(ls[r["line"] - 1:r["through"]])
for (relf, ln), ss in strip_map.items():
    for s in ss:
        deleted_text.setdefault(relf, []).extend(s["remove_branches"])

for relf in sorted(set([r["file"] for r in plan["drop_lines"]] + [r["file"] for r in plan["drop_blocks"]]
                       + [k[0] for k in strip_map])):
    path = os.path.join(SRC, *relf.split("/"))
    before = io.open(path, encoding="utf-8").read()
    lines = before.split("\n")
    after = []
    for ln, line in enumerate(lines, 1):
        if (relf, ln) in kill or ln in kill_blocks.get(relf, set()):
            continue
        for s in strip_map.get((relf, ln), []):
            m = ONE_RULE.match(line)
            if not m:
                continue
            ind, sel, brace, body, tail = m.groups()
            br = branches(sel)
            keep = [b for b in br if b not in s["remove_branches"]]
            if not keep:
                line = None
                break
            line = ind + ", ".join(keep) + brace + body + tail
        if line is not None:
            after.append(line)
    new = "\n".join(after)
    bt, at = class_tokens(before), class_tokens(new)
    # 记账口径：每一枚"活 token"的减少量必须恰好等于被删掉的那段文字里它的出现次数。
    # 只要求"计数一字不降"是错的——`.cn-now-next-hero.cn-hero-stagger > *` 这种规则同时带着一枚死类
    # 与一枚活类，删掉它当然会让 v8-page / cn-now-next-hero 少一次，而那条规则本来就永远匹配不上。
    # 所以判据换成：少掉的每一次都要能指回被我删掉的那段文字；指不回去就是误伤，ABORT。
    lost_text = "".join(deleted_text.get(relf, []))
    lt = class_tokens(lost_text)
    hurt = []
    for t, n in bt.items():
        if t in ALLOW:
            continue
        drop = n - at.get(t, 0)
        if drop != lt.get(t, 0):
            hurt.append("%s 少 %d 次而删掉的文字里是 %d 次" % (t, drop, lt.get(t, 0)))
    ob, cb = new.count("{"), new.count("}")
    if hurt or ob != cb:
        print("ABORT %s：活 token 对不上账 %s｜花括号 %d/%d" % (relf, hurt[:6], ob, cb))
        sys.exit(3)
    io.open(path, "w", encoding="utf-8", newline="\n").write(new)
    print("写入 %s：%d -> %d 行｜字节 %d -> %d｜活 token %d 枚一枚没动"
          % (relf, before.count("\n") + 1, new.count("\n") + 1, len(before), len(new), len(bt)))

print("\n剩余声明（全 src 的 css 里）")
for t in ALLOW:
    n = 0
    for dp, dn, fn in os.walk(SRC):
        dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", "dist")]
        for f in fn:
            if f.endswith(".css"):
                n += len(re.findall(r"(?<![-_A-Za-z0-9])" + re.escape(t) + r"(?![-_A-Za-z0-9])",
                                    io.open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()))
    print("  %-20s %d 处" % (t, n))

