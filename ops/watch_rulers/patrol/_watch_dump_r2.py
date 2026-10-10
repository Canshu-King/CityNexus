# -*- coding: utf-8 -*-
"""值守 07:18 · 长间隔现场汇总 v2：睡 N 秒后一次性打出八组只读读数（不发消息、不写账本、不删）。

替代 `_watch_dump_0712.py`：那一版 [7] 用 `df D:` 在 git-bash 下报 No such file，
本版改 `/d`；[6] 只看我敲过的三条，本版把**每条会话**的最后一段助手文本与流水静默分钟都打出来
（用户的原令是「检查工人工作要读取他们的任务」，所以要能逐条判「在干活 / 交完等派 / 停在裁语」）。

用法：python _watch_dump_r2.py [秒数]
"""
import io
import os
import re
import sys
import json
import glob
import time
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = sys.executable
INBOX = r"D:/moodle/_qoder_ledger_inbox"
LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
REPO = r"D:/moodle/CityNexus"
ENV = dict(os.environ, HTTPS_PROXY="", PYTHONIOENCODING="utf-8")
GATE = re.compile(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$")


def sh(args, timeout=600, cwd=None):
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=(cwd or HERE), env=ENV)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return "ERR %s: %s\n" % (type(e).__name__, e)


def last_texts(path, n_back=40):
    """这枚会话最后一段助手正文 + 流水文件静默分钟。"""
    p = path
    if not os.path.isfile(p):
        return None, None
    idle = (time.time() - os.path.getmtime(p)) / 60.0
    last = ""
    rows = []
    # 只读尾巴：这些流水单文件能到 10 MB 以上，整本读 20 条会白吃几百 MB
    size = os.path.getsize(p)
    with io.open(p, "rb") as f:
        f.seek(max(0, size - 400000))
        blob = f.read().decode("utf-8", errors="replace")
    rows = blob.split("\n")
    for line in reversed(rows[-n_back:]):
        try:
            r = json.loads(line)
        except Exception:
            continue
        m = r.get("message") or {}
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        if isinstance(c, list):
            t = " ".join(b.get("text", "") for b in c
                         if isinstance(b, dict) and b.get("type") == "text")
        else:
            t = c if isinstance(c, str) else ""
        if t.strip():
            last = t.strip()
            break
    return last, idle


def main():
    wait = int(sys.argv[1]) if len(sys.argv) > 1 else 780
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    time.sleep(wait)
    print("=== 值守现场 %s（睡了 %d 秒）===" % (time.strftime("%H:%M:%S"), wait))

    print("\n[1] 自动轮 last 12")
    for l in io.open(os.path.join(HERE, "autumn_watch.log"), encoding="utf-8",
                     errors="replace").read().rstrip().split("\n")[-12:]:
        print("   " + l[:190])

    print("\n[2] 两把闸的只读复算（预测，不是门判）")
    print(sh([PY, os.path.join(HERE, "bolt_replica.py")])[-700:])

    print("\n[3] 收件箱按命名门的待插块")
    for p in sorted(glob.glob(os.path.join(INBOX, "*.md"))):
        b = os.path.basename(p)
        if GATE.match(b):
            print("   %-26s %7d B  %.1f min" % (b, os.path.getsize(p),
                  (time.time() - os.path.getmtime(p)) / 60.0))

    print("\n[4] 账本与落地门")
    sz = os.path.getsize(LEDGER)
    print("   %d B  mtime=%s（%.1f min 前）" % (sz, time.strftime("%H:%M:%S",
          time.localtime(os.path.getmtime(LEDGER))), (time.time() - os.path.getmtime(LEDGER)) / 60.0))
    ins = len(glob.glob(os.path.join(INBOX, "_processed", "*inserted*")))
    print("   _processed 里带 inserted 标记的 %d 枚；入账总数(全部) %d 枚"
          % (ins, len(glob.glob(os.path.join(INBOX, "_processed", "*")))))

    print("\n[5] 权威线现尖（只读 ls-remote）")
    print("   " + sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin",
                      "refs/heads/mirror/integration-frontend-apple-pass1"], 180,
                     cwd=REPO).strip())

    print("\n[6] 申报对远程逐枚核对（枝尖紧贴申报 + 40 位可取回）")
    print(sh([PY, os.path.join(HERE, "_claims_vs_remote_r1.py")], 900)[-800:])

    print("\n[7] 每条会话最后在说什么（读他们自己的任务，不靠进程端口）")
    files = sorted(glob.glob(os.path.join(PROJ, "*.jsonl")), key=os.path.getmtime, reverse=True)
    for p in files[:20]:
        sid = os.path.basename(p)[:8]
        txt, idle = last_texts(p)
        if txt is None:
            continue
        head = txt.replace("\n", " ")[:150]
        print("   %s 静默%5.1f分 | %s" % (sid, idle or 0.0, head))

    print("\n[8] 盘（git-bash 用 /d 这种路径）")
    print(sh(["df", "-B", "1G", "/c", "/d", "/e"])[:420])

    print("\n[9] 每条车道现在为什么没在写字（按它自己最后一句话分类，不靠猜）")
    import re as _re
    RULING = _re.compile(u"请裁|待裁|归你|你点|你判|一行授权|放行|等你|请你|需要您|要的一句|裁语|"
                        u"waiting for (you|the command)|your call|needs a ruling|awaiting|"
                        u"tell me which|please (rule|decide)|need one line", _re.I)
    DISPATCH = _re.compile(u"待派|不自造活|没有新单|没人给我新单|下次叫我|"
                           u"awaiting (a )?(new )?(order|dispatch)|no order yet|"
                           u"don'?t invent|assign me|next time you ask", _re.I)
    SELF = _re.compile(u"没改善|仍欠|下一步|未收口|还没做|没做完|"
                       u"not re-?run|still owed|left undone|not done|remaining|"
                       u"i did not (run|re-?run)", _re.I)
    cnt = {}
    for p2 in files[:20]:
        sid2 = os.path.basename(p2)[:8]
        txt2, idle2 = last_texts(p2)
        if txt2 is None:
            continue
        t2 = txt2.replace("\n", " ")
        if RULING.search(t2):
            why = u"等裁语"
        elif DISPATCH.search(t2):
            why = u"等派单"
        elif SELF.search(t2):
            why = u"自己点名还欠一格"
        elif (idle2 or 0) < 6:
            why = u"在跑（流水还在写）"
        else:
            why = u"已交付，无明确下一步"
        cnt[why] = cnt.get(why, 0) + 1
        print("   %s 静默%5.1f分  %-24s | %s" % (sid2, idle2 or 0.0, why, t2[:90]))
    print("   分类合计：%s" % ", ".join(u"%s=%d" % kv for kv in sorted(cnt.items())))

    print("\n[10] 号令者写了哪些派单、车道动没动（`_new_dispatch_r1.py`，从 02:00 起）")
    dd = sh([PY, os.path.join(HERE, "_new_dispatch_r1.py"), "2", "0"], 900)
    # 计数只取扫描自己那行结论，别拿「正文里出现未动二字的行」当条数——
    # 上一版就是这么读的，把「未动 0 条」和扫描结论「未动 1 条」同时打出来，看着像互相矛盾。
    for x in (dd or "").split("\n"):
        s = x.strip()
        if s.startswith("09-29") or s.startswith("未动") or s.startswith("  ORD-"):
            if (s.startswith("  ORD-") and "未动" in s) or not s.startswith("  ORD-"):
                print("   " + s[:200])

    print("\n[11] 车道表与撞号尺（各只留结论行，细节在 md 文件里）")
    ft = sh([PY, os.path.join(HERE, "_fleet_table_r1.py")], 900)
    for l in (ft or "").split("\n"):
        st = l.strip()
        if st.startswith("!!") or st.startswith("未登记前缀") or st.startswith("写好"):
            print("   " + st[:200])
    # 10:03 换尺：r1 只对三枚热文件算三侧 blob，会漏报「只动注册表/新建目录」那类枝
    # （`backend/app/main.py`、`frontend/src/design-tokens.css` 都实测咬过）。
    # r2 把同一判据扩到**每枚枝自己动过的每一枚文件**，并自带分类器自测与 ls-tree 双通道自证。
    hc = sh([PY, os.path.join(HERE, "_hotfile_contention_r2.py")], 900)
    hl = [x.rstrip() for x in (hc or "").split("\n")]
    head = [x for x in hl if x.strip().startswith(u"现尖")]
    summ = [x for x in hl if x.strip().startswith(u"小结")]
    risk = [x for x in hl if u"两侧都改过" in x and u"两侧都改过 0 枚" not in x]
    print(u"   [争用尺 r2] " + (head[0].strip()[:170] if head else u"读数不全"))
    for x in (summ[:1] + [r.strip() for r in risk]):
        print("      " + x[:220])
    if not risk:
        print("      （本轮没有一枚活枝被判两侧都改过）")
    oc = sh([PY, os.path.join(HERE, "_order_collisions_r1.py")], 900)
    for l in (oc or "").split("\n"):
        st = l.strip()
        if "跨车道同号" in st or st.startswith("ORD-"):
            print("   " + st[:180])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
