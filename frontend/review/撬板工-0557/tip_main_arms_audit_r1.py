# -*- coding: utf-8 -*-
u"""只读勘查：新尖上 main.* 那批键的两臂，与 ORD-0557 块里那句「中文侧照抄屏上现字」对不对得上。

为什么量它：这单的边界写死了「不许换措辞」，而 legacy 那屏今天不分语言取词——
若中文臂写的是新译的词，那落地那一笔就把中文屏上的字改了，那是另一档决定，不归搬运。
本脚本只读 git 对象，不动任何树。退出码：0 取到数。
"""
from __future__ import annotations

import io
import re
import subprocess
import sys

REPO = r"D:\moodle\CityNexus"
TIP = sys.argv[1] if len(sys.argv) > 1 else "2039df0430c5b310fa24874f2f2e7aa8fd3b5816"
OUT = r"D:\moodle\_qoder_qiaobangong_0557\tip_main_arms_audit.txt"
KEY = re.compile(u'^\\s*"([^"]+)":\\s*"((?:[^"\\\\]|\\\\.)*)"\\s*,?\\s*$')


def blob(rel):
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (TIP, rel)], capture_output=True)
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace").split("\n")


def section(lines, a, b):
    ia = next(i for i, l in enumerate(lines) if l.startswith(a))
    ib = next(i for i, l in enumerate(lines) if l.startswith(b))
    d = {}
    for l in lines[ia:ib]:
        m = KEY.match(l)
        if m:
            d[m.group(1)] = m.group(2)
    return d


def main():
    dic = blob("frontend/src/i18n/LocaleContext.tsx")
    mn = blob("frontend/src/main.tsx")
    if dic is None or mn is None:
        sys.stdout.write(u"新尖对象取不到 ⇒ 不报数\n")
        return 2
    en = section(dic, "const en: Dict", "const zhCN: Dict")
    zh = section(dic, "const zhCN: Dict", "const dictionaries")
    mk = sorted([k for k in en if k.startswith("main.")])
    same = [k for k in mk if en[k] == zh.get(k)]
    diff = [(k, en[k], zh.get(k)) for k in mk if en[k] != zh.get(k)]
    lines = [
        u"新尖 %s｜字典里 main. 键：en 侧 %d 枚、zh 侧 %d 枚" % (
            TIP, len(mk), len([k for k in zh if k.startswith("main.")])),
        u"两臂逐字相同 %d 枚｜两臂不同 %d 枚" % (len(same), len(diff)),
        u"main.tsx 里 t(\"main.*\") 调用现读 %d 处" % len([l for l in mn if re.search(u't\\("main\\.', l)]),
    ]
    for k, a, b in diff:
        lines.append(u"   两臂不同：%s｜en=「%s」｜zh=「%s」" % (k, a, b if b is not None else u"（zh 侧没有这枚键）"))
    text = u"\n".join(lines) + u"\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
