# -*- coding: utf-8 -*-
"""「断在半路」这把谓词到底靠不靠得住——拿过去 24 小时的真流水量它的误报率，再决定要不要为它开一档哨兵。

为什么先量再开档：判据没量过就开档，等于给自己造一枚假红机器。
我自己有过前科：09-26 那枚「0 fetch 的保守红」实测误报 3/4，差点据此把人退掉。
所以这里要的不是「有没有出现过死尾」，而是**出现死尾之后 60 分钟内它自己回来了没有**——
回来了就是「正常收拍/被我读错了」，没回来才是真停摆。

只读。输出：逐扇的死尾次数、其中多少在 60 分内复工、以及全体合起来的误报率。
"""
import io
import json
import os
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HOURS = 24.0
RECOVER_MIN = 60.0


def epoch_of(ts):
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        v = float(ts)
        return v / 1000.0 if v > 1e11 else v
    s = str(ts).strip()
    if s.endswith("Z"):
        import calendar
        for f in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return calendar.timegm(time.strptime(s[:-1], f))
            except Exception:
                continue
        return None
    return None


def nodes(path, kb):
    size = os.path.getsize(path)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        f.seek(max(0, size - kb * 1024))
        if size > kb * 1024:
            f.readline()
        data = f.read()
    out = []
    for line in data.split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        out.append(r)
    return out


def kinds(rec):
    """把一条记录压成 (类型, 是否有 tool_use, 是否有 tool_result, 是否有 assistant 正文)。"""
    m = rec.get("message") if isinstance(rec.get("message"), dict) else None
    has_u = has_r = has_a = False
    role = m.get("role") if m else None
    if m and isinstance(m.get("content"), list):
        for x in m["content"]:
            if not isinstance(x, dict):
                continue
            if x.get("type") == "tool_use":
                has_u = True
            elif x.get("type") == "tool_result":
                has_r = True
            elif x.get("type") == "text" and role == "assistant" and (x.get("text") or "").strip():
                has_a = True
    return role, has_u, has_r, has_a


def main():
    cutoff = time.time() - HOURS * 3600
    tot_dead = tot_rec = 0
    print(u"%s｜回看 %.0f 小时｜判活一律读流水；复工窗口 %.0f 分" % (
        time.strftime("%H:%M:%S"), HOURS, RECOVER_MIN))
    rows = []
    for p in sorted(os.listdir(PROJ)):
        if not p.endswith(".jsonl"):
            continue
        id8 = p[:8]
        path = os.path.join(PROJ, p)
        if os.path.getmtime(path) < cutoff:
            continue
        seq = []
        for r in nodes(path, 8000):             # 8 MB/扇：约 14 扇共 ~110 MB，一眼报进度免得看着像挂住
            e = epoch_of(r.get("timestamp"))
            if e is None or e < cutoff:
                continue
            role, hu, hr, ha = kinds(r)
            if role is None and not hu and not hr:
                continue          # active-leaf 这类书签记录不带正文，量形状时必须跳过（01:44 实测：每条 tool_use 之后紧跟的就是它）
            seq.append((e, role, hu, hr, ha))
        print(u"  … %s 尾部 8 MB：带戳且有内容的记录 %d 条" % (id8, len(seq)))
        if not seq:
            continue
        dead = 0
        recovered = 0
        for i, (e, role, hu, hr, ha) in enumerate(seq):
            if not hu:
                continue
            # 这枚 tool_use 后面：先遇到 tool_result ⇒ 正常；文件就此为止 ⇒ 不算死尾（可能还在跑）
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            if nxt is None:
                continue
            if nxt[3]:
                continue
            if (nxt[0] - e) / 60.0 <= 3.0:
                continue                        # 三分钟内就换别的东西了：多半是记录形状，不是断
            dead += 1
            after = [x for x in seq[i + 1:] if x[4] or x[3]]
            if after and (after[0][0] - e) / 60.0 <= RECOVER_MIN:
                recovered += 1
        if dead:
            rows.append((id8, dead, recovered, len(seq)))
        tot_dead += dead
        tot_rec += recovered
    for id8, dead, rec, n in sorted(rows, key=lambda x: -x[1]):
        print(u"  %-9s 死尾 %2d 次｜其中 %d 次在 %.0f 分内复工｜尾部记录 %d 条" % (id8, dead, rec, RECOVER_MIN, n))
    if not rows:
        print(u"  （这 %.0f 小时内没有任何一枚 tool_use 呈死尾形状）" % HOURS)
    fp = (tot_rec / float(tot_dead) * 100.0) if tot_dead else 0.0
    print(u"\n合计死尾 %d 次、其中 %d 次自己复工 ⇒ **误报率 %.0f%%**（分母 %s）" % (
        tot_dead, tot_rec, fp, tot_dead if tot_dead else u"0——分母是 0，不能说这把尺准"))
    print(u"用法：误报率高就别开档；真停摆占比高才值得开一档去叫人。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
