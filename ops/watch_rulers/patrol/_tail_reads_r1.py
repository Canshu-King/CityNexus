# -*- coding: utf-8 -*-
"""读一扇窗最后一段「它自己说出来的话」（assistant text），用于把停下的原话递给该递的人。

为什么单独一支：传话必须带**对方自己的收尾原话**，不能我只看关键词就替它下结论——
01:21 那遍 `_why_stopped_r1.py` 就把「两道闸都干净」这种句子读成了「卡闸」（关键词命中≠状态），
所以判定要收窄，而**原文**永远单独取一次再看。

用法：python _tail_reads_r1.py <id8> [尾部KB=200] [打印字数=900]
"""
import glob
import io
import json
import os
import sys

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    if len(sys.argv) < 2:
        print(u"用法: python _tail_reads_r1.py <id8> [尾部KB] [字数]")
        return 2
    pre = sys.argv[1]
    kb = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    shown = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    cands = glob.glob(os.path.join(PROJ, pre + "*.jsonl"))
    if not cands:
        print(u"REFUSE：找不到 %s 的流水（前缀不对还是删了？）" % pre)
        return 1
    path = cands[0]
    size = os.path.getsize(path)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        f.seek(max(0, size - kb * 1024))
        if size > kb * 1024:
            f.readline()
        data = f.read()
    texts = []
    for line in data.split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        m = r.get("message") if isinstance(r.get("message"), dict) else None
        if not m or m.get("role") != "assistant":
            continue
        c = m.get("content")
        if isinstance(c, str):
            if c.strip():
                texts.append(c)
        elif isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "text" and (x.get("text") or "").strip():
                    texts.append(x["text"])
    if not texts:
        print(u"%s：尾部 %d KB 内没有 assistant 正文（只有工具调用？——别替它编一句收尾）" % (pre, kb))
        return 0
    print(u"%s｜尾部 %d KB 内 assistant 正文 %d 段｜取最后一段：\n" % (pre, kb, len(texts)))
    print(texts[-1][-shown:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
