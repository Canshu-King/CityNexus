# -*- coding: utf-8 -*-
"""值守 14:56 · 「哪张单还没人接」探测器（只读）。

为什么夜里没这把尺、白天要：cron 在 11:00 到期 ⇒ 号令者不再每小时自动派单/收单，
而他 11:35 起用的是「车道自申报」——他在块里写一张不点名会话的单，谁认谁落块。
问题跟夜里那条一样：**冷车道不会自己重读账本**，所以自申报的单可能一整天没人接。
夜里我用的是「带 id 的派单行有没有被动手」（`_new_dispatch_r1.py`），那条不覆盖自申报单，
所以这里补一把：拿号令者块里出现的每个单号，去看远端有没有该单的枝、账本里有没有该单的交付块。

判据三条，全只读：
  ① 单号出现在 12:00 之后的号令者块里（`_processed/cmdr_*.inserted_*`）；
  ② 远端 `review/*` 里有没有含该单号的枝名（`ord04XX` 大小写都认）；
  ③ 账本里除号令者块之外，有没有车道块正文提到该单号。
两条都没有 ⇒ 标「无人接」，并把该单在块里的原文行摘出来（我转达时只用他写过的原话）。
"""
import glob
import io
import os
import re
import glob as _g
BASE_TX = "C:/Users/仓鼠王/.qoder/projects/D--moodle"
UNIVERSE = set(os.path.basename(x)[:8] for x in _g.glob(BASE_TX + "/*.jsonl"))
LANES = {"a68b0631":"rel","1d64acf5":"S4","9759f1ac":"N2","904a042d":"Q","bac10f40":"AI","3b65af59":"map","be19052c":"dt","e4f3490f":"道0370","49fe0d7b":"N3","8ac89982":"R0417","4033270f":"0383","1ba48dbf":"newlane","6a150e1e":"newlane2","9cc37e57":"0421","2d2d7428":"0441","a6b95d59":"DSH","8e5245f0":"道0369","da46954a":"新车道"}
import subprocess
import sys
import time

LC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../live_checks
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"D:\moodle\CityNexus"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = os.environ.get("UNCLAIMED_INBOX") or r"D:\moodle\_qoder_ledger_inbox"  # 03:13 加：给合成件测试用（只让 _lane_order_reading 与本尺能指到 patrol/_fixture_inbox，绝不指共享收件口）
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
SINCE = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0     # 往前看几小时的号令者块


def sh(args, t=600):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return ((p.stdout or "") + (p.stderr or "")).strip()


def tight_pairs(text):
    """从一枚块正文里按「紧配对」认收件会话，认四种形制：A `id`(ORD-N) / B 单头带 40 位 uuid /
    C 该行只有一枚 id 且句子里有 派·→·@·给·收件 / D 裁语行形制 `N. \\`id8\\`：……ORD-0xx……`（行里有「你」）。

    02:50 补 A/C 的原因：原尺只认 ±700 字里的**整 40 位 uuid**，而号令者 02:10 之后多写成 8 位短 id
    ⇒ 『收件会话已动』一律成「块里没点名」，无人接的张数随块被门排空而虚涨。身份只认 jsonl 文件名前 8 位。

    15:44 补 D 的原因（同一条坑的第二回）：他 15:30 那块是「十条裁语一次发清」，形制是
    `3. \\`82f55d8a\\`：①…开 ORD-0540…` ——单号在句中、收件人在行首，A/C 都不认，
    于是尺把 ORD-0540..0545 六张全报成「无人接」，明细还统一挂到同一行别的车道上（哨兵为此早退过一次）。
    限度照实写：D 是**行级**配对，裁语行里顺带提到的别的单号（例如同一行的「ORD-0538 已落」）也会被算给
    这一行的收件车道——那一行本来就是写给他的一句话，误配方向是「少报无人接」，所以要求行里必须有「你」才配。
    """
    out = {}
    for l in text.split(chr(10)):
        ids_all = [x for x in re.findall(r"\b([0-9a-f]{8})\b", l) if x in UNIVERSE]
        headD = re.match(r"^\s*\d+\.\s*`([0-9a-f]{8})`\s*[：:]", l)
        for m in re.finditer(r"ORD-0(\d{3})", l):
            num = "ORD-0" + m.group(1)
            got = []
            for d in re.finditer(r"`([0-9a-f]{8})`\s*[\(（]\s*" + num + r"\s*[\)）]", l):
                if d.group(1) in UNIVERSE:
                    got.append(d.group(1))
            for d in re.finditer(r"^### " + num + r"\s+车道\s+([0-9a-f]{40})", l, re.M):
                got.append(d.group(1)[:8])
            if not got and headD and u"你" in l and headD.group(1) in UNIVERSE:
                got = [headD.group(1)]
            if not got and len(ids_all) == 1 and re.search(u"派|→|@|给|收件", l):
                got = ids_all
            if got:
                out.setdefault(num, set()).update(got)
    return out



def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    now = time.time()
    blocks = [f for f in glob.glob(os.path.join(INBOX, "_processed", "cmdr_*.inserted_*"))
              + glob.glob(os.path.join(INBOX, "cmdr_*.md"))
              if now - max(os.path.getmtime(f), os.path.getctime(f)) <= SINCE * 3600]
    blocks.sort(key=os.path.getmtime)
    refs = sh(["git", "ls-remote", "origin", "refs/heads/review/*"])
    ledger = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    # 车道块正文（含已入账的）里提到的单号，算「有人接了」
    lane_text = []
    for f in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")) + glob.glob(os.path.join(INBOX, "*.md")):
        if os.path.basename(f).lower().startswith("cmdr"):
            continue
        try:
            lane_text.append(io.open(f, encoding="utf-8", errors="replace").read())
        except Exception:
            pass
    lane_blob = "\n".join(lane_text)
    PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"

    def moved_after(sid8, when_epoch):
        """被点名的那条会话，在派单块写完之后有没有再动过自己的流水（只读 mtime）。"""
        g = glob.glob(os.path.join(PROJ, sid8 + "*.jsonl"))
        if not g:
            return False
        return os.path.getmtime(g[0]) > when_epoch

    orders = {}
    for f in blocks:
        t = io.open(f, encoding="utf-8", errors="replace").read()
        tp = tight_pairs(t)
        wfm = max(os.path.getmtime(f), os.path.getctime(f))
        lines = t.split("\n")
        for m in re.finditer(r"ORD-0(\d{3})", t):
            num = "ORD-0" + m.group(1)
            ln = t[:m.start()].count("\n") + 1
            line = lines[ln - 1].strip() if ln - 1 < len(lines) else ""
            ctx = t[max(0, m.start() - 700):m.start() + 700]
            ids = [x[:8] for x in re.findall(r"\b([0-9a-f]{8})-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", ctx)]
            ids += tp.get(num, [])
            # 14:57 修的第一版缺陷：单号在**块头**也被提一次，而我原来只取「第一次出现」周围的上下文，
            # 于是 §五/§六 里真正点名收件人的那一行被丢掉了 ⇒ 0465/0466 被我误报成「无人接」。
            orders.setdefault(num, []).append((os.path.basename(f), ln, line[:300], wfm, sorted(set(ids))))
    print("最近 %.1f 小时的号令者块 %d 枚，里面点到 %d 个单号" % (SINCE, len(blocks), len(orders)))
    unclaimed = []
    for num, occs in sorted(orders.items()):
        key = num.lower().replace("-", "")          # ord0461
        has_branch = bool(re.search(key, refs, re.I))
        in_lane_block = num in lane_blob
        ids = sorted(set(i for _, _, _, _, lst in occs for i in lst))
        t0 = min(o[3] for o in occs)
        woke = [i for i in ids if moved_after(i, t0)]
        # 「有没有人接」的第四路证据：收件会话在派单块之后自己动过流水。
        # 少了这一路会把「正在写、还没交块」的单误报成没人接（14:56 第一跑就把 0461/0464/0465/0466 报了）。
        claimed = has_branch or in_lane_block or bool(woke)
        pick = [o for o in occs if re.search(u"派给|下发|车道|自申报|开单|并入|折进", o[2])] or occs
        bf, ln, line = pick[0][0], pick[0][1], pick[0][2]
        if not claimed:
            unclaimed.append((num, bf, ln, line))
        print("  %-9s 枝名=%-2s 车道块=%-2s 收件会话已动=%-26s ⇒ %s"
              % (num, "是" if has_branch else "否", "是" if in_lane_block else "否",
                 (",".join(x[:8] for x in woke) if woke else ("否" if ids else "块里没点名")),
                 "已有人接" if claimed else "**无人接**"))
    print("\n**无人接的单 %d 张**" % len(unclaimed))
    for num, bf, ln, line in unclaimed:
        # 派单行往往不在块标题里：拿整枚块找『同一行内单号与 8 位 id 相距 <=16 字』那行，
        # 再报该收件车道的现况（闸上/在写/静默）——否则『无人接』会一直把『收件车没油』误读成『没人派到』。
        ctx = line
        note_tag = ""
        ids = [x for x in re.findall(r"\b([0-9a-f]{8})\b", line) if x in LANES]
        try:
            fp = next((z for z in blocks if os.path.basename(z) == bf), None)
            body = io.open(fp, encoding="utf-8", errors="replace").read() if fp else ""
        except Exception:
            body = ""
        for bl in body.split(chr(10)):
            if num not in bl:
                continue
            for m in re.finditer(r"\b([0-9a-f]{8})\b", bl):
                if m.group(1) in UNIVERSE and abs(bl.find(num) - m.start()) <= 16:
                    ids.append(m.group(1))
                    ctx = bl.strip()
        if not ids:
            # 号令者常把收件人写在**小节正文**里而单号只在**小节标题**上（19:10 那块的『派给车道 a6b95d59』就是这种）。
            # 所以退回第二条规则：按小节切块，取含该单号的那一节里的 id，并明说是『同节』而不是『同行相邻』。
            secs = []
            cur = []
            for bl in body.split(chr(10)):
                if bl.startswith("**") or bl.startswith("## ") or bl.startswith("### "):
                    secs.append(cur)
                    cur = [bl]
                else:
                    cur.append(bl)
            secs.append(cur)
            for sec in secs:
                if not any(num in x for x in sec):
                    continue
                for bl in sec:
                    for m in re.finditer(r"\b([0-9a-f]{8})\b", bl):
                        if m.group(1) not in UNIVERSE:
                            continue
                        # 03:14 合成件抓到的毛病：同一节里**别的单**那行会被挂到本单上
                        # （ORD-0997 没有可认的收件人，却被报了『道0369 在写』）。
                        # 同行若把这枚 id 紧配对到别的单号，它就不是本单的收件人。
                        dm = re.search(u"`" + m.group(1) + u"`\\s*[\\(（]\\s*(ORD-0\\d{2,3})", bl)
                        if dm and dm.group(1) != num:
                            continue
                        ids.append(m.group(1))
                        ctx = bl.strip()
                        note_tag = "（同节点名，不是同行相邻）"
        ids = sorted(set(ids))
        note = ""
        if ids:
            try:
                import _dispatch_delivery_r1 as DD
                note = "｜收件车道现况：" + "、".join("%s %s" % (LANES.get(i, "未登记·" + i), DD.state(i, time.time())) for i in ids)
            except Exception as e:
                note = "（收件现况取不到：%s）" % type(e).__name__
        else:
            note = "｜块内找不到『单号与车道 id 同行相邻』的派单行（可能只写在标题或靠窗口敲门）"
        print("  !! %s（出自 %s 第 %d 行）：%s%s%s" % (num, bf[:34], ln, ctx[:200], note_tag, note))
    print("边界：只读（ls-remote + 读块），0 次写账本、0 次派单、0 次改动任何人的枝。"
          "「无人接」不等于「该派给我转达」——自申报单归号令者裁，我只把事实报出来。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
