# -*- coding: utf-8 -*-
"""内联双语的第二把尺：把模板字面量也算进来。

仓库里那把 `_bilingual_count_r1.py` 只认 `'…'` 与 "…" 两种字面量，反引号包住的它不判——这不是它的错，
是它的口径。第廿六波换掉的正是三处模板字面量，所以那把尺的总数一个字都不会动（13 处仍是 13 处）。
要证明这一波确实把东西搬走了，得用一把看得见过引号的尺，并且当场说明两把尺的口径差别，
免得有人拿"总数没降"当成"没改"。

我自己新写的这把只加宽字面量的形状，判据不变：恰好一支含 CJK 才算一枚；注释行不算。
"""
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
CJK = re.compile(u"[\u3400-\u4dbf\u4e00-\u9fff]")
SINGLE = r"'(?:[^'\\\n]|\\.)*'"
DOUBLE = r'"(?:[^"\\\n]|\\.)*"'
BACKTICK = r"`(?:[^`\\]|\\.)*`"
LIT = "(" + "|".join([DOUBLE, SINGLE, BACKTICK]) + ")"
TERN = re.compile(r"\?\s*" + LIT + r"\s*:\s*" + LIT, re.S)
SUFFIX = (".ts", ".tsx")


def sh(args):
    p = subprocess.run(args, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise SystemExit("GIT_FAIL %s :: %s" % (args, p.stderr.decode("utf-8", "replace")[:200]))
    return p.stdout.decode("utf-8", "replace")


def count(sha):
    files = [f for f in sh(["git", "ls-tree", "-r", "--name-only", sha, "--", "frontend/src"]).splitlines()
             if f.endswith(SUFFIX)]
    if not files:
        raise SystemExit("NO_FILES at %s —— 清单为空，不许据此说没有" % sha[:10])
    total = 0
    per = {}
    for f in files:
        body = sh(["git", "show", "%s:%s" % (sha, f)])
        n = 0
        for m in TERN.finditer(body):
            a, b = m.group(1), m.group(2)
            if bool(CJK.search(a)) != bool(CJK.search(b)):
                n += 1
        if n:
            per[f] = n
        total += n
    return total, len(files), per


def main():
    old, new = sys.argv[1], sys.argv[2]
    ho, fo, po = count(old)
    hn, fn, pn = count(new)
    print("WIDE-RULER (ternary pairs, template literals included)")
    print("OLD %s files=%d pairs=%d" % (old[:10], fo, ho))
    print("NEW %s files=%d pairs=%d" % (new[:10], fn, hn))
    print("DELTA %d" % (ho - hn))
    for f in sorted(po):
        if po[f] != pn.get(f, 0):
            print("MOVED %s: %d -> %d" % (f, po[f], pn.get(f, 0)))
    top = sorted(pn.items(), key=lambda kv: -kv[1])[:8]
    print("TOP at new tip:", top)
    if ho == 0 or hn == 0:
        print("ABORT 零读数＝这把新尺瞎了，不是没有")
        return 3
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
