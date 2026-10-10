# -*- coding: utf-8 -*-
"""内联双语普查尺 r2（两臂，认跨行的对象对） -- lane 加闸工, ruling requested at 账本那块「要点名的一把尺的形制」.

Why this exists.  The broadcast census ruler `live_checks/_bilingual_count_r1.py:14` recognises one
shape only: a ternary `? "中文" : "English"`.  A 车道 that actually shipped eight pairs was counted six,
and said so: the two it lost are pairs written as `{ zh: "…", en: "…" }`, which are not ternaries at all,
and when the two arms sit on separate lines even the ternary regex has nothing to match.  The number that
drives the per-file 通播 is therefore short by a whole family, so lanes get an incomplete余面账.

Two arms, reported separately so the sum is auditable instead of merged into one word:

  arm A  ternary pairs -- the commander's own judgement, kept byte-for-byte in behaviour:
         `? LIT : LIT` where exactly one side carries CJK.
  arm B  object pairs -- `zh:` and `en:` literals inside the same pair, in either key order, with the
         two arms on one line or spread over lines; exactly one side must carry CJK, same rule.
         B is split into B_same_line and B_over_lines, because B_over_lines is precisely the shape the
         old ruler could not see at all.

A quoted-key table (`"zh": "中文"` … `"en": "English"` inside LocaleContext's two dictionaries) is NOT
counted: those are the dictionary itself, already on both sides -- counting them would inflate the
"still inline" figure with the very copy the migration moves things INTO.  Comments are masked first,
so a doc comment that shows an example pair is not counted as an inline pair.

Refusals, in the order's own style: an empty file list, or an arm that returns zero everywhere, is
ABORT -- "不许据此说没有".
"""

import io
import json
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
CJK = re.compile(r"[㐀-鿿]")
SUFFIX = (".ts", ".tsx")

# the commander's own literal grammar (his line 13), kept identical
LIT = r"(\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*')"
TERN = re.compile(r"\?\s*" + LIT + r"\s*:\s*" + LIT, re.S)
# object pair: zh: <lit> , en: <lit>  (either order, any whitespace/newlines between)
PAIR = re.compile(r"\b(?:\"|')?(zh|en)(?:\"|')?\s*:\s*" + LIT + r"\s*,\s*(?:\"|')?(zh|en)(?:\"|')?\s*:\s*" + LIT, re.S)


def sh(args):
    p = subprocess.run(["git", "-C", REPO] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise SystemExit("CODE_FAIL %s :: %s" % (args, p.stdout.decode("utf-8", "replace")[:400]))
    return p.stdout.decode("utf-8", "replace")


def strip_comments(text):
    out = []
    i, n = 0, len(text)
    state = None
    quote = ""
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state is None:
            if c == "/" and nxt == "/":
                state = "line"
                i += 2
                continue
            if c == "/" and nxt == "*":
                state = "block"
                out.append("\n")
                i += 2
                continue
            if c in "\"'`":
                state, quote = "str", c
            out.append(c)
            i += 1
            continue
        if state == "line":
            if c == "\n":
                state = None
                out.append(c)
            i += 1
            continue
        if state == "block":
            if c == "*" and nxt == "/":
                state = None
                i += 2
                continue
            if c == "\n":
                out.append(c)
            i += 1
            continue
        if state == "str":
            out.append(c)
            if c == "\\":
                if i + 1 < n:
                    out.append(text[i + 1])
                i += 2
                continue
            if c == quote:
                state = None
            i += 1
            continue
    return "".join(out)


def one_cjk(a, b):
    return bool(CJK.search(a)) != bool(CJK.search(b))


def count_ternary(text):
    hits = []
    for m in TERN.finditer(text):
        if one_cjk(m.group(1), m.group(2)):
            hits.append((text[:m.start()].count("\n") + 1, "A", m.group(0)[:60].replace("\n", " ")))
    return hits


def count_pairs(text):
    hits = []
    for m in PAIR.finditer(text):
        order, a, b = m.group(1), m.group(2), m.group(4)
        zh = a if order == "zh" else b
        en = b if order == "zh" else a
        if not one_cjk(zh, en):
            continue
        spanned = "\n" in m.group(0)
        hits.append((text[:m.start()].count("\n") + 1, "B_over_lines" if spanned else "B_same_line",
                     m.group(0)[:60].replace("\n", " ")))
    return hits


def census(sha):
    files = [l.strip() for l in sh(["ls-tree", "-r", "--name-only", sha, "--", "frontend/src"]).splitlines()
             if l.strip().endswith(SUFFIX)]
    if not files:
        raise SystemExit("NO_FILES at %s -- 现取清单为空，不许据此说没有" % sha[:10])
    per = {}
    totals = {"A": 0, "B_same_line": 0, "B_over_lines": 0}
    for f in files:
        raw = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (sha, f)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode("utf-8", "replace")
        body = strip_comments(raw)
        rows = count_ternary(body) + count_pairs(body)
        if rows:
            per[f] = rows
            for _, arm, _s in rows:
                totals[arm] += 1
    if sum(totals.values()) == 0:
        raise SystemExit("ZERO_TOTAL at %s -- 两臂全零是要 ABORT 的形状，不是结论" % sha[:10])
    return {"sha": sha, "files_with_inline_pairs": len(per), "totals": totals, "per_file": per}


def selftest():
    """The four shapes that must be separated, plus the two that must not be counted."""
    cases = [
        ("ternary one line", 'const a = zh ? "执行游标" : "the execution cursor";', {"A": 1, "B_same_line": 0, "B_over_lines": 0}),
        ("object pair same line", 'const P = { basis: { zh: "行程起点", en: "the start" } };', {"A": 0, "B_same_line": 1, "B_over_lines": 0}),
        ("object pair over lines", 'const Q = {\n  x: {\n    zh: "台上没有场景",\n    en: "no scenario on stage",\n  },\n};', {"A": 0, "B_same_line": 0, "B_over_lines": 1}),
        ("en first still one pair", 'const R = { y: { en: "no frozen evidence", zh: "这趟没有冻结证据" } };', {"A": 0, "B_same_line": 1, "B_over_lines": 0}),
        ("both sides CJK is not a pair", 'const S = { z: { zh: "中文", en: "还是中文" } };', {"A": 0, "B_same_line": 0, "B_over_lines": 0}),
        ("neither side CJK is not a pair", 'const T = { w: { zh: "latin", en: "latin too" } };', {"A": 0, "B_same_line": 0, "B_over_lines": 0}),
        ("a doc comment example is not a pair", '/* zh: "例子", en: "example" */\nconst u = 1;', {"A": 0, "B_same_line": 0, "B_over_lines": 0}),
        ("dictionary rows are not inline pairs", 'const D = { "k.zh": "键", "k.en": "key" };', {"A": 0, "B_same_line": 0, "B_over_lines": 0}),
    ]
    bad = []
    for label, src, expected in cases:
        body = strip_comments(src)
        got = {"A": 0, "B_same_line": 0, "B_over_lines": 0}
        for _, arm, _s in count_ternary(body) + count_pairs(body):
            got[arm] += 1
        if got != expected:
            bad.append("%s: expected %s got %s" % (label, expected, got))
    return bad


def main():
    if "--selftest" in sys.argv:
        bad = selftest()
        print("SELFTEST assertions=8 failures=%d" % len(bad))
        for line in bad:
            print("  FAIL " + line)
        return 1 if bad else 0
    sha = sys.argv[1] if len(sys.argv) > 1 else sh(["rev-parse", "origin/mirror/integration-frontend-apple-pass1"]).strip()
    if "--fetch" in sys.argv:
        sh(["fetch", "--quiet", "origin", sha])
    res = census(sha)
    t = res["totals"]
    print("sha=%s files_with_inline_pairs=%d total=%d | arm_A_ternary=%d arm_B_same_line=%d arm_B_over_lines=%d" % (
        res["sha"][:10], res["files_with_inline_pairs"], sum(t.values()), t["A"], t["B_same_line"], t["B_over_lines"]))
    print("the shape the old ruler could not see: B_over_lines=%d, B_total=%d, so a ternary-only census reports %d of %d" % (
        t["B_over_lines"], t["B_same_line"] + t["B_over_lines"], t["A"], sum(t.values())))
    top = sorted(res["per_file"].items(), key=lambda kv: -len(kv[1]))[:12]
    for f, rows in top:
        kinds = {}
        for _, arm, _s in rows:
            kinds[arm] = kinds.get(arm, 0) + 1
        print("   %-72s %s" % (f, " ".join("%s=%d" % (k, v) for k, v in sorted(kinds.items()))))
    if "--json" in sys.argv:
        io.open("bilingual_census_r2_%s.json" % res["sha"][:10], "w", encoding="utf-8", newline="").write(
            json.dumps(res, ensure_ascii=False, indent=1))
        print("json=bilingual_census_r2_%s.json" % res["sha"][:10])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
