# -*- coding: utf-8 -*-
"""谁停在了「点名在自己之前」：账本里给某条工人点的单，落笔比那条工人最后一次动笔还晚 ⇒ 他根本没看见。

为什么值得有这一枚：A 档量的是「这单没人接」，量不到「这单点了名、可被点的那扇窗三天前就停了」。
 ready/cold 的会话不会自己回来读账本（这项目反复踩过），所以对那扇窗来说，那一句点名等于没发生。

两处形状坑（第一版都踩过，都被这版堵上）：
 ① 块标题里的时刻有两种形：`### CMDR 07:57`（只有时分，属于今天）与 `... @2026-09-21 00:2x`（带完整日期）。
    只按时分解释会把 09-21 的老块算成今天 19 点 ⇒ 报出「晚了 14804 分钟」这种十日鬼话。
 ② 正文里提到某个 8 位 id ≠ 那一句是点给它的。只认**行首 60 字内**的点名形（`### id8`、`SESSION=id8`、`` `id8`：``、`id8 你…`）。
"""
import io
import os
import re
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
LOOKBACK_H = float(os.environ.get("DNN_HOURS", "16"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FULL = re.compile(r"@(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})")
HM = re.compile(r"(?:^###\s*CMDR\s*|^##\s*CMDR\s*|\*\*值守\s*)(\d{2}):(\d{2})")
STRIP = re.compile(u"^[\\s>#*\\-\\.、0-9)）(（（）「」`'\\\"\\[\\]【】·•—–\\|]+")
SESSIONID = re.compile(r"^(?:SESSION=|车道\s*)?([0-9a-f]{8})\b")


def head_id(l):
    """行首点名：先把列表号、引用符、反引号、括号都剥掉，再看剩下是不是以 8 位 id 开头。
    第一版没剥反引号，`4. `6a150e1e`：…` 这种最主流的派单形全被漏掉（237 枚只认得 1 枚）——那叫尺瞎，不叫干净。"""
    s = STRIP.sub("", l, count=1)
    m = SESSIONID.match(s)
    return m.group(1) if m else None
ADDR = re.compile(u"派给|下发给|接这单|下一手|：派|请你|你接|你名下|领这单"
                  u"|你\\*\\*：|你：\\*\\*")


def day_of(y, mo, d, h, mi):
    try:
        return time.mktime(time.strptime("%04d-%02d-%02d %02d:%02d" % (y, mo, d, h, mi), "%Y-%m-%d %H:%M"))
    except Exception:
        return 0.0


def hm_today(h, mi):
    """只有时分 ⇒ 归今天；若解释出来比现在晚一小时以上，退一天（夜里写的块不能算到明天）。"""
    t = day_of(*time.localtime()[:3], h, mi)
    if t > time.time() + 3600:
        t -= 86400
    return t


def main():
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split(chr(10))
    cur_t = 0.0
    best = {}
    for l in lines:
        mf = FULL.search(l[:200])
        if mf:
            cur_t = day_of(*[int(x) for x in mf.groups()])
        else:
            mh = HM.search(l[:60])
            if mh:
                cur_t = hm_today(int(mh.group(1)), int(mh.group(2)))
        if not l.strip() or cur_t <= 0:
            continue
        i = head_id(l)
        if not i:
            continue
        if not ADDR.search(l[:160]):
            continue
        if i not in best or cur_t > best[i][0]:
            best[i] = (cur_t, l.strip()[:150])

    cutoff = time.time() - LOOKBACK_H * 3600
    rows = []
    for fn in os.listdir(PROJ):
        if not fn.endswith(".jsonl"):
            continue
        i = fn[:8]
        if i not in best:
            continue
        t, line = best[i]
        if t < cutoff:
            continue                      # 太久以前的点名不算「今天漏读」
        mt = os.path.getmtime(os.path.join(PROJ, fn))
        if mt + 5 * 60 < t:
            rows.append((i, t, mt, line))
    rows.sort(key=lambda r: r[2])
    print(u"%s 行首点名形制的派单共 %d 扇；其中**停在自己那一笔点名之前**、且点名落在近 %d 小时内的 %d 扇：" % (
        time.strftime("%m-%d %H:%M:%S"), len(best), int(LOOKBACK_H), len(rows)))
    for i, dt, mt, line in rows:
        print(u"  %-9s 窗最后动笔 %s｜点名落笔 %s（晚 %d 分）｜%s" % (
            i, time.strftime("%m-%d %H:%M", time.localtime(mt)), time.strftime("%m-%d %H:%M", time.localtime(dt)),
            int((dt - mt) / 60.0), line[:130]))
    if not rows:
        print(u"  ⇒ 没有『点名晚于停笔』的窗 ⇒ 停着的窗不是漏读点名，而是手上确实没活；要它们继续动，得由号令者新派。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
