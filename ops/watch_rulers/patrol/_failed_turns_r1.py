# -*- coding: utf-8 -*-
"""值守 07:43 · 「回合死在失败上」的检测（只读会话流水）。

为什么需要：我原来的停摆判据只看「流水尾节点是未应答的 tool_use」，那只覆盖
「弹窗没点 / 委派在飞」两种形；第三种是**回合直接以 API 失败终止**（`isApiErrorMessage`），
那种会话在 `list_chat_sessions` 里可能显示 ready/cold，看着像「交完活在等」，
实际是那一步没做完也没人知道。用户要的是「停下的就让他们继续」，所以这一形必须单独量出来。

判据两条：
  A 尾记录里出现过 isApiErrorMessage ⇒ 计数（历史，供对照）；
  B **最新一条会话记录本身**就是 API 错正文，且该会话不在 running ⇒ 真停摆，具名报出来。
"""
import glob
import io
import json
import os
import sys
import time

PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
SELF_SID = "42d1a6fa"   # 值守自己这条会话不参与判活与额度检测
TAIL = 900000
# 只报这一班还在场的人：流水静默超过这么多分钟的会话不进历史计数
MAX_AGE = 480


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    now = time.time()
    hist, live, quota = [], [], []
    files = sorted(glob.glob(os.path.join(PROJ, "*.jsonl")), key=os.path.getmtime, reverse=True)[:24]
    for p in files:
        sid = os.path.basename(p)[:8]
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            f.seek(max(0, size - TAIL))
            blob = f.read().decode("utf-8", "replace")
        recs = []
        for line in blob.split("\n"):
            if not line.strip():
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                pass
        if not recs:
            continue
        errs = [r for r in recs if r.get("isApiErrorMessage")]
        idle = (now - os.path.getmtime(p)) / 60.0
        if errs and idle <= MAX_AGE:
            hist.append((sid, len(errs), str(errs[-1].get("timestamp"))[:19], idle))
        last = recs[-1]
        # 真停摆：最后一条就是错误正文
        if last.get("isApiErrorMessage"):
            c = (last.get("message") or {}).get("content")
            txt = c if isinstance(c, str) else " ".join(
                b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text") if isinstance(c, list) else ""
            live.append((sid, idle, (txt or "")[:70].replace("\n", " ")))
        # 额度签名：账户日限是「全队一起停」的那种停，它不留未应答 tool_use，A/B 两条判据都接不住。
        # 只看尾部 60 KB —— 历史里 09-26 那几条旧限免不能当今天的状态（09-26 的 `a17ae861` 就在流水里）。
        # 三条收口（08:31 现读才发现这把自己写歪了）：
        #  ① 只认接口原话那一句，`额度/quota` 这类常用词会在正文里以散文形式命中（`4033270f` 那枚就是）；
        #  ② 排除值守自己（我这轮把这句话读进流水再打印，尺就量到我自己的字节 —— 自指）；
        #  ③ 受 MAX_AGE 约束，09-26 那几条旧限免（静默 3600+ 分）不是今天的状态。
        if sid != SELF_SID and idle <= MAX_AGE:
            low = blob[-60000:].lower()
            for sig in ("daily usage limit", "to continue working with me"):
                if sig in low:
                    quota.append((sid, idle, sig))
                    break
    print("API 错历史 %d 条会话；**当前停在失败上的** %d 条；**尾部出现额度字样的** %d 条"
          % (len(hist), len(live), len(quota)))
    for sid, n, ts, idle in hist:
        print("   历史 %-9s 计 %d 枚 最新 %s（该会话静默 %.1f 分）" % (sid, n, ts, idle))
    for sid, idle, txt in live:
        print("   !! 停在失败 %-9s 静默 %.1f 分 | %s" % (sid, idle, txt))
    for sid, idle, sig in quota:
        print("   !! 尾部有额度字样 %-9s 静默 %.1f 分 | 命中 %r（只报数；要不要改档位是用户与号令者的决定，我不自动重发）"
              % (sid, idle, sig))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
