# -*- coding: utf-8 -*-
u"""把 judge() 重写成"抽数字比较"版，并修两个自测抓到的错。

自测（19:12）抓到三处，全是真错：
  ① ` 0 扇` 这个空格是我凭空想的，实际是 `）0 扇` ⇒ 每一拍都判红（假红）。
  ② 我以为 ⑥ 是 U+2466，实际 ⑥ 是 U+2465（圈号是连续码位，0x2460＋序号）⇒ 抓到的是 ⑦ Codex 侧。
  ③ "该敲"那一格用 `in WATCH_CELLS` 兜着，而 WATCH_CELLS 里含 ③④ ⇒
     ④「还压着 51 条」被判成要人看（把常态当红）。
改法：格号**按序号推码位**（①0x2460＋n-1），判据**抽数字再比 0**，不靠空格、不靠 WATCH_CELLS 兜。

跑法：python _patch_judge_numcmp_r2.py
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_patrol_loop_r1.py")

NEW = u'''def _mark(n):
    u"""第 n 格的真圈号：①是 U+2460，圈号连续 ⇒ n 格 = U+2460+(n-1)。"""
    return unichr_(0x2460 + n - 1)


def unichr_(i):
    return chr(i)


def num_after(text, key):
    u"""抽 key 后第一个整数；抽不到返回 None（不许拿 0 冒充读数）。"""
    i = text.find(key)
    if i < 0:
        return None
    m = re.search(r"\\d+", text[i + len(key):])
    return int(m.group(0)) if m else None


def judge(text):
    u"""从一拍的正文推出 (红?, 理由行)。判据全部来自**这一拍读到的行**，解析不到就当红。"""
    concl = ""
    cells = {}
    for l in text.splitlines():
        ls = l.strip()
        if ls.startswith(u"\\u7ed3\\u8bba"):
            concl = ls
        for n in (1, 2, 3, 6, 10):
            if ls.startswith(_mark(n)):
                cells[n] = ls
    why = []
    if not concl:
        why.append(u"\\u6ca1\\u8bfb\\u5230\\u7ed3\\u8bba\\u884c")
    elif GREEN not in concl:
        why.append(concl)
    # ②该敲：n=2。抽 "扇" 前的数；行形是 `② 该敲（…）N 扇`
    v = cells.get(2)
    if v is not None:
        n = num_after(v, u"\\uff09")            # 全角右括号之后紧跟的那个数
        if n is None:
            why.append(v)
        elif n != 0:
            why.append(v)
    # ③不该敲：n=3，同样形制
    v = cells.get(3)
    if v is not None:
        n = num_after(v, u"\\uff09")
        if n is None:
            why.append(v)
        elif n != 0:
            why.append(v)
    # ①未接 BB 机：n=1
    v = cells.get(1)
    if v is not None and u"\\u672a\\u63a5 BB \\u673a" in v:
        n = num_after(v, u"\\u672a\\u63a5 BB \\u673a")
        if n is None:
            why.append(v)
        elif n != 0:
            why.append(v)
    # ⑥值守栈：n=6，只要这一格在，结论行以外还要求它说"栈完整"
    v = cells.get(6)
    if v is not None and u"\\u6808\\u5b8c\\u6574" not in v:
        why.append(v)
    elif v is None:
        why.append(u"\\u6ca1\\u8bfb\\u5230\\u503c\\u5b88\\u6808\\u90a3\\u4e00\\u683c")
    # ⑩推广：n=10，两腿全无/只收不发 都得是 0 才算真接上了
    v = cells.get(10)
    if v is not None:
        for k in (u"\\u4e24\\u817f\\u5168\\u65e0", u"\\u53ea\\u6536\\u4e0d\\u53d1"):
            n = num_after(v, k)
            if n is None:
                why.append(v)
                break
            if n != 0:
                why.append(v)
                break
    return (bool(why), why, concl, cells)
'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    i = t.index("def judge")
    j = t.index("def logline")
    old = t[i:j]
    new = t[:i] + NEW + u"\n\n" + t[j:]
    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    bak = SRC + u".bak_judgenum_1913"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"已重写 judge：旧 %d 字节 → 新 %d 字节（备份 %s）"
          % (len(old), len(NEW), os.path.basename(bak)))
    # 自证：新文件的 judge 能被 import，且圈号推得对
    sys.path.insert(0, HERE)
    import _patrol_loop_r1 as P
    marks = {n: P._mark(n) for n in (1, 2, 3, 6, 10)}
    bad = [n for n, c in marks.items() if ord(c) != 0x2460 + n - 1]
    if bad:
        print(u"FAIL：圈号推错 %s" % bad)
        return 1
    print(u"圈号自证：%s" % u" ".join(u"%d=%s" % (n, c) for n, c in sorted(marks.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())