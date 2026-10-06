# -*- coding: utf-8 -*-
"""一轮巡逻 = 一条命令：`python _bb_patrol_once_r1.py`

为什么合并：夜里我每轮要问的是同样六件事——谁停了、停了该不该敲、包工头积压多少、
收件口有没有压着、账本镜像跟没跟上、值守栈还在不在。分开跑要五条命令，
一个晚上就把 turn 花在"取数"上而不是"处置"上。合并之后一轮一次读数，省下的力气留给动作。

判"该不该敲"沿用这一夜量出来的规矩（一律读他们自己的流水，不信看板旗子）：
· 静默≥45 分 且 未取>0 且 不是额度墙/掉线 ⇒ 该敲（过档即敲，不等两拍）
· 静默≥45 分 但 未取=0、尾行自报"交完等点单" ⇒ **不该敲**，那是缺下一件，敲了只换来一句"在等点单"
· 在抑制名单里（带到期时刻）⇒ 不敲、不重复报
"""
import io
import json
import os
import re          # ⑨ 那格要正则读表首行的尖；先前我用了 re 却没导，三格全被 except 兜成「取不到」
import subprocess
import sys
import time
import urllib.request

BOARD = u"http://127.0.0.1:4820"
HUB = u"http://127.0.0.1:4799"
HERE = os.path.dirname(os.path.abspath(__file__))
QUIET = os.path.join(HERE, u"_quiet_list.txt")
INBOX = u"D:/moodle/_qoder_ledger_inbox"
CMDR = u"qoder:494abfd7"
TAILFORM = u"_lane_tailform_r1.py"   # 末态尺（20:13 形状闸的唯一判词来源）


def jget(url):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return json.loads(op.open(url, timeout=25).read().decode("utf-8", "replace"))


def quiet_ids():
    if not os.path.isfile(QUIET):
        return {}
    out = {}
    now = time.time()
    for ln in open(QUIET, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln or ln.startswith(u"#"):
            continue
        parts = [x.strip() for x in ln.split(u"|")]
        if len(parts) < 3:
            continue
        try:
            exp = time.mktime(time.strptime(u"%d-%s" % (time.localtime().tm_year, parts[1]), "%Y-%m-%d %H:%M"))
        except Exception:
            continue
        if now < exp:
            out[parts[0]] = parts[1]
    return out


CODEX_DB = os.path.expanduser(u"~/.codex/thread_history_1.sqlite")


def codex_side(hours=6.0):
    u"""第⑦格：Codex 那侧近 N 小时的轮次与失败成因。读不到返回 None（写不可得，不当绿）。"""
    try:
        import sqlite3
        import re as _re
        if not os.path.isfile(CODEX_DB):
            return None
        con = sqlite3.connect(u"file:%s?mode=ro" % CODEX_DB, uri=True, timeout=8)
        try:
            cur = con.cursor()
            cut = time.time() - hours * 3600
            st = dict(cur.execute(
                u"select status, count(*) from thread_turns"
                u" where coalesce(completed_at, started_at) >= ? group by status", (cut,)).fetchall())
            errs = [r[0] for r in cur.execute(
                u"select error_json from thread_turns"
                u" where status in ('failed','interrupted') and coalesce(completed_at, started_at) >= ?", (cut,))]
            act = cur.execute(
                u"select count(distinct thread_id) from thread_turns"
                u" where coalesce(completed_at, started_at) >= ?", (time.time() - 5400,)).fetchone()[0]
        finally:
            con.close()
        def cls(e):
            s_ = e or u""
            for pat, name in ((u"usageLimit|daily usage|rate limit", u"额度/限流"),
                              (u"network|Connection|timeout|reset", u"网络"),
                              (u"auth|token|401|403", u"鉴权")):
                if _re.search(pat, s_, _re.I):
                    return name
            return u"其他"
        from collections import Counter
        return {"states": st, "bad_causes": Counter(cls(e) for e in errs).most_common(),
                "bad": len(errs), "active_threads_90m": act}
    except Exception as e:
        say_note(u"⑦ Codex 侧读不动（%s: %s）⇒ 写不可得，不当绿" % (type(e).__name__, str(e)[:60]))
        return None


def cell11_backlog(here, runner=subprocess.run, emit=None):
    u"""第⑪格：把号令者名下「已送未拆」拆成两堆并打印三行。

    尺是现成那把 `_cmdr_backlog_split_r1.py`（实测跑 1.4 秒），这里只搬运它的输出，
    判据不在巡逻里复制第二份。runner/emit 是给自测留的注入位：
    喂一枚假尺（rc=1 或没有「甲类」）进去，就能验"坏的那一侧写成不可得、而不是没积压"。
    （emit 默认用内置 print；别写 globals().get("print")——那不是全局名，会取到 None。）
    """
    if emit is None:
        def emit(x):
            sys.stdout.write(x + chr(10))
    ruler = os.path.join(here, u"_cmdr_backlog_split_r1.py")
    try:
        sp = runner([sys.executable, ruler], capture_output=True, timeout=120, cwd=here,
                    env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        o = (sp.stdout or b"").decode("utf-8", "replace")
        if sp.returncode != 0 or u"甲类" not in o:
            emit(u"⑪ 验收口拆分：尺没答（rc=%d｜输出 %d 字符）⇒ 不可得，不许当'没积压'"
                 % (sp.returncode, len(o)))
        else:
            l1 = next((l for l in o.splitlines() if l.startswith(u"收件人")), u"")
            l2 = next((l for l in o.splitlines() if l.startswith(u"甲类")), u"")
            l3 = next((l for l in o.splitlines() if l.startswith(u"乙类")), u"")
            emit(u"⑪ %s" % l1[:110])
            emit(u"   %s" % l2[:110])
            emit(u"   %s" % l3[:110])
    except Exception as e:
        emit(u"⑪ 验收口拆分：取不到（%s）⇒ 不当零" % type(e).__name__)


def adoption_split(rows, spoken, took, nowt, wmin):
    u"""把在册的车道按 BB 机两条腿分四态（第⑩格用的就是这一份，别复制第二把尺）。

      A 在发        ：wmin 分钟内以 from 出现过
      B 发过但静默  ：出现过，但在 wmin 之外
      C 两腿全无    ：from 从没出现，且名下没有一条被取走过 ⇒ 真没接上，缺整段接入件
      C2 只收不发   ：from 从没出现，但名下有被取走的 ⇒ 收信腿是通的，缺的只有 send
    判据只吃现读的 from/delivered_at，不吃名册的 verified：那枚旗会把后者读成"已接上"。
    """
    A, B, C, C2 = [], [], [], []
    for r in rows:
        hid = u"qoder:" + r["id8"]
        t = spoken.get(hid, 0)
        if not t:
            (C2 if took.get(hid) else C).append(r["id8"])
        elif nowt - t <= wmin * 60:
            A.append(r["id8"])
        else:
            B.append((r["id8"], int((nowt - t) / 60)))
    return A, B, C, C2


def say_note(x):
    io.open(os.path.join(HERE, u"_patrol_notes.log"), "a", encoding="utf-8", newline=chr(10)
            ).write(time.strftime("[%m-%d %H:%M:%S] ") + x + chr(10))


def main():
    fleet = jget(BOARD + u"/api/fleet")
    rows = fleet["rows"]
    cnt = fleet["counts"]
    st = jget(HUB + u"/agents")
    q = quiet_ids()
    print(u"① 现测 %s｜在册 %d＋收班 %s｜在写 %d｜静默超45 %d｜额度墙 %d｜掉线 %d｜未接 BB 机 %s"
          % (fleet["at"], len(rows), cnt.get("retired", fleet.get("retired_n", 0)),
             cnt["writing"], cnt["quiet45"], cnt["quota"], cnt["dropped"],
             sum(1 for r in rows if not r.get("in_hub"))))

    knock, waiting, undecidable = [], [], []
    # 末态尺：每拍起一次子进程读那一扇的 jsonl 末三条（只读，0 发送）
    _shape_cache = {}

    def shape_of(id8):
        if id8 in _shape_cache:
            return _shape_cache[id8]
        try:
            p = subprocess.run([sys.executable, TAILFORM, id8],
                             capture_output=True, cwd=HERE, timeout=60,
                             env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            out = (p.stdout or b"").decode("utf-8", "replace")
            v = u"（读不到判词）"
            for _l in out.splitlines():
                if _l.strip().startswith(u"\u21d2"):
                    v = _l.strip()[1:].strip()
                    break
        except Exception:
            v = u"（读不到判词：%s）" % "子支起不来"
        _shape_cache[id8] = v
        return v
    for r in rows:
        if r["idle_min"] < 45:
            continue
        if r["id8"] in q:
            print(u"   抑制中（到 %s）：%s %s 静 %d 分 ⇒ 不敲不报" % (q[r["id8"]], r["id8"], r["name"], r["idle_min"]))
            continue
        if r["live"] in ("quota_wall", "dropped"):
            continue
        if (r.get("unread") or 0) <= 0:
            waiting.append(r)
            continue
        # 形状闸（20:13 装）：静默过档 **且** 末态判「断在半路」才算真该敲。
        # 原判据只有 idle+unread，看不见末态 ⇒ 19:55/20:08 两拍把"静完自己走回来的车"
        # 列成该敲（20:11 回读：两扇末条都在 1 分前）。判词由 _lane_tailform_r1.py 给，不另写一套。
        _v = shape_of(r["id8"])
        if _v == u"\u65ad\u5728\u534a\u8def" or u"断在半路" in _v:
            knock.append(r)
        elif _v.startswith(u"（读不到"):
            undecidable.append((r, _v))
        else:
            waiting.append(r)
    print(u"② 该敲（静默过档且信压着没取）%d 扇：%s"
          % (len(knock), u"、".join(u"%s %s 静%d 分/未取%d" % (x["id8"], x["name"], x["idle_min"], x["unread"])
                                    for x in knock) or u"无"))
    if undecidable:
        print(u"②b 末态不可判 %d 扇（形状闸读不到判词，**不列该敲也不列不该敲**）：%s"
              % (len(undecidable),
                 u"、".join(u"%s %s（%s）" % (x[0]["id8"], x[0]["name"], x[1]) for x in undecidable)))
    print(u"③ 不该敲（缺下一件，不是懒也不是卡）%d 扇：%s"
          % (len(waiting), u"、".join(u"%s %s 静%d 分" % (x["id8"], x["name"], x["idle_min"])
                                      for x in waiting) or u"无"))
    for x in waiting[:4]:
        print(u"     %s 尾行：%s" % (x["id8"], (x.get("last") or u"")[:74].replace("\n", u" ")))

    acks = json.loads(io.open(u"D:/moodle/agent_bus/state.json", encoding="utf-8").read()).get("acks", {})
    now = time.time()
    need = 0
    with io.open(u"D:/moodle/agent_bus/bus.jsonl", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                m = json.loads(line)
            except Exception:
                continue
            if str(m.get("to")) != CMDR or m.get("kind") not in ("deliver", "order", "ask", "ruling"):
                continue
            if m.get("delivered_at") or acks.get(m.get("id")):
                continue
            need += 1
    print(u"④ 包工头真要动的还压着 %d 条（deliver/order/ask/ruling 未取）｜BB 机名册 %d 枚" % (need, len(st)))

    pend = [x for x in os.listdir(INBOX) if x.endswith(u".md")]
    print(u"⑤ 收件口压着 %d 块：%s" % (len(pend), u"、".join(sorted(pend)) or u"无"))

    try:
        w = subprocess.run([sys.executable, os.path.join(HERE, u"_watch_stack_r1.py"), u"--check"],
                           cwd=HERE, capture_output=True, timeout=120,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        tail = (w.stdout or b"").decode("utf-8", "replace").strip().splitlines()[-1]
        print(u"⑥ 值守栈：%s" % tail[:120])
    except Exception as e:
        print(u"⑥ 值守栈：取不到（%s）⇒ 不当它完整" % type(e).__name__)

    cx = codex_side()
    if cx is None:
        print(u"⑦ Codex 侧：不可得（读不动那座库或文件不在）⇒ 这一格不许当绿")
    else:
        print(u"⑦ Codex 侧｜近 90 分活跃 thread %d 条｜近 6 小时轮次 %s｜失败或中断 %d 轮（成因 %s）"
              % (cx["active_threads_90m"], cx["states"] or u"无", cx["bad"],
                 u"、".join(u"%s×%d" % kv for kv in cx["bad_causes"]) or u"无"))
        _cx_ids = [a for a in st if a.startswith(u"codex:")]
        print(u"   名册里 codex 身份 %d 枚：%s｜两侧对不上就不猜，要接得主人或包工头点名"
              % (len(_cx_ids), u"、".join(_cx_ids) or u"无"))
        # 窗名指纹（20:24 装）：活跃 thread 不再只是一串 id。抽窗名是**附属**读数，
        # 起不来只写「窗名不可得」，不许把第⑦格其余读数一起拖成不可得。
        try:
            _w = subprocess.run([sys.executable, os.path.join(HERE, u"_codex_window_id_r1.py")],
                                cwd=HERE, capture_output=True, timeout=90,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            _wt = (_w.stdout or b"").decode("utf-8", "replace")
            _names = [l.strip() for l in _wt.splitlines() if u"自报窗名：" in l]
            if _names:
                print(u"   活跃窗自报名：%s"
                      % u"；".join(x.split(u"：", 1)[1] for x in _names))
            _par = [l.strip() for l in _wt.splitlines() if u"派生自" in l]
            if _par:
                print(u"   %s" % _par[0])
            # 缺口按**窗名**判（20:25 装）：原来按「活跃 thread 数 − 在册身份数」，
            # 会把「一枚已接的 bbfix1 ＋ 一枚未接的 Window R」减成 0 —— 数量对上≠接上了。
            _win = []
            for x in _names:
                _v = x.split(u"：", 1)[1].strip()
                if _v and not _v.startswith(u"**"):
                    _win.append(_v)
            if _win:
                _hit = [w for w in _win if any(w.lower() in a.lower() for a in _cx_ids)]
                _miss = [w for w in _win if w not in _hit]
                if _miss:
                    print(u"   **推广缺口 %d 扇（窗名在名册里没有同名身份）**：%s"
                          % (len(_miss), u"、".join(_miss)))
                    print(u"      名册现有：%s｜要接得主人或包工头点名，我不据窗名自动注册"
                          % (u"、".join(_cx_ids) or u"无"))
                else:
                    print(u"   按窗名对：活跃窗 %s 都能在名册里找到同名身份 ⇒ 缺口 0 枚" % u"、".join(_win))
            else:
                print(u"   **窗名不可读 ⇒ 推广缺口按未知报，不按 0 报**"
                      u"（原来那条「多 N 枚」是数差，不是缺口）")
        except Exception as e:
            print(u"   窗名不可得（%s）——**不拖第⑦格其余读数**，缺口照旧按活跃 thread 数报"
                  % type(e).__name__)
        # 10-05 16:3x 把这格从「只报缺口」升级成「缺口 + 出口」：看巡逻的人不该再去别处问「那要怎么接」。
        # 20:27 把**数差**那半句删了：它与上面的「按窗名判缺口」自相矛盾（数相等≠同一扇），
        # 两个互相抵消的错谓词比一个更危险。缺口数一律由窗名判据给；这里只留出口那半句。
        print(u"   接入件（可直接粘）：D:/moodle/agent_bus/INVITE_CODEX.txt")

    # ⑧：S「已送未拆」。这一格不在这里另算一遍——判据只该有一份，
    # 我从哨兵自己那一轮的总结行里把段取出来；取不到就写不可得，绝不拿「没读到」当「没有」。
    try:
        sl = io.open(os.path.join(HERE, u"_sentinel_relay_latest.log"),
                     encoding="utf-8", errors="replace").read().splitlines()
        seg = next((l for l in reversed(sl) if u"已送未拆" in l), None)
        if seg is None:
            print(u"⑧ 已送未拆：那一轮总结里没有这一段 ⇒ 不可得（不当零）")
        else:
            # 按 `｜` 切段、逐段**整段**打（20:32 装）。原来按 120 字硬砍，
            # 把第三扇的名字和段尾那半句「｜红」（＝这一轮哨兵判红）一起砍掉了——
            # 按字数砍句子＝按字数砍判语。超上限时截**段数**并明写还有几段没打，不腰斩。
            _i = seg.index(u"已送未拆")
            _parts = [p for p in seg[_i:].split(u"｜") if p.strip()]
            _MAXP = 6
            for _k, _p in enumerate(_parts[:_MAXP]):
                # 段尾那个「红」是哨兵本轮的判语，孤零零一行看不出是什么 ⇒ 单独标出来
                _tag = u"判语" if _p.strip() in (u"红", u"绿") else u""
                print(u"⑧%s %s" % ((u"（%s）" % _tag) if _tag else u"", _p.strip()))
            if len(_parts) > _MAXP:
                print(u"⑧ （还有 %d 段没打，见哨兵日志同名段）" % (len(_parts) - _MAXP))
    except Exception as e:
        print(u"⑧ 已送未拆：取不到（%s）⇒ 不当零" % type(e).__name__)

    # ⑨：落地顺序表的**有效期**。10-05 17:1x 实测过：尖一动，同批可落/必须分跳/代次过期三组数全变
    # （四对涨到十五对），所以「按旧表点单」比没表更坏。规矩不能只写在交接稿的散文里——
    # 装进巡逻这条命令：每张表首行都印了自己用的那枚尖，巡逻拿它跟现读尖对一次。
    try:
        import glob as _g
        arts = sorted(_g.glob(os.path.join(HERE, u"_landing_plan_*.txt")), key=os.path.getmtime)
        want = os.environ.get("PLAN_ART") or (arts[-1] if arts else None)
        if want is None:
            print(u"⑨ 落地表：一张都没有 ⇒ 不可得（不许当'不需要表'）")
        else:
            head = io.open(want, encoding="utf-8", errors="replace").readline()
            mt = re.search(u"现尖 `([0-9a-f]{12})`", head)
            if not mt:
                print(u"⑨ 落地表：%s 首行没有尖印 ⇒ 这张表不合格，重跑" % os.path.basename(want))
            else:
                tref = os.environ.get("PLAN_TIPREF",
                                      "refs/heads/mirror/integration-frontend-apple-pass1")
                lr = subprocess.run([u"git", u"-C", u"D:/moodle/CityNexus", u"ls-remote", u"origin", tref],
                                    capture_output=True, timeout=120,
                                    env=dict(os.environ, GIT_TERMINAL_PROMPT=u"0"))
                live = ((lr.stdout or b"").decode("utf-8", "replace").split() or [u""])[0][:12]
                if not live:
                    print(u"⑨ 落地表：现读尖不可得（ls-remote 空）⇒ 不判新鲜，也不判过期")
                elif live == mt.group(1):
                    print(u"⑨ 落地表：新鲜（表与现读同一枚尖 %s）｜用的哪张：%s"
                          % (live, os.path.basename(want)))
                else:
                    print(u"⑨ 落地表：**已过期**（表尖 %s ≠ 现读 %s）⇒ 点单前重跑 "
                          u"_landing_plan_r1.py，别按旧表落" % (mt.group(1), live))
    except Exception as e:
        print(u"⑨ 落地表：取不到（%s）⇒ 不当它新鲜" % type(e).__name__)

    # ⑩：推广（本机车道这一侧）。Codex 那侧是第⑦格，这两格合起来才是"给其他会话推广"的覆盖；
    # 判据与 agent_bus/_adoption_census_1006_0330.txt 同形：分母取板上在册的行，
    # 分子只看 bus.jsonl 里 from 自己出现的时刻——"我发过几次邀请"不作数（10-03 定过这条）。
    try:
        wmin = float(os.environ.get("ADM_WINDOW_MIN", "360"))
        nowt = time.time()
        spoken = {}
        led = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                           u"agent_bus", u"bus.jsonl")
        if os.path.isfile(led):
            for line in io.open(led, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    mm = json.loads(line)
                except ValueError:
                    continue
                f = str(mm.get("from") or u"")
                t = float(mm.get("ts") or 0)
                if t > spoken.get(f, 0):
                    spoken[f] = t
        # 收信那条腿也现读：只数 from 会把"一直在取信、只是不发消息"的车道误判成"没接"，
        # 那种格子会让人去发接入件，而它其实缺的只有第 2 步（send）。10-06 03:5x 实测到一例：
        # 6a150e1e 名下 15 条全取走、末次取信距今四十分钟，而 from 从没出现过。
        took = {}
        for line in io.open(led, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                mm = json.loads(line)
            except ValueError:
                continue
            if mm.get("delivered_at"):
                d = str(mm.get("to") or u"")
                tk = float(mm.get("delivered_at") or 0)
                if tk > took.get(d, 0):
                    took[d] = tk
        A, B, C, C2 = adoption_split(rows, spoken, took, nowt, wmin)   # 四态见这个函数
        if not os.path.isfile(led):
            print(u"⑩ 推广：BB 机账读不到 ⇒ 这一格不可得，不许当'都接上了'")
        else:
            print(u"⑩ 推广（分母在册 %d 扇｜窗口 %.0f 分）｜在发 %d｜发过但静默 %d｜两腿全无 %d｜只收不发 %d"
                  % (len(rows), wmin, len(A), len(B), len(C), len(C2)))
            print(u"   发过但静默最久：%s"
                  % (u"、".join(u"%s(%d 分)" % x for x in sorted(B, key=lambda y: -y[1])[:3]) or u"无"))
            if C:
                print(u"   两腿全无（要整段接入件）：%s｜GET %s/api/invite?agent=qoder:<id8>"
                      % (u"、".join(C), BOARD))
            if C2:
                print(u"   只收不发（接入件第 2 步 send 才是缺口）：%s ⇒ 别重发邀请，交活/问裁语时带 --kind"
                      % u"、".join(C2))
    except Exception as e:
        print(u"⑩ 推广：取不到（%s）⇒ 不当零" % type(e).__name__)

    cell11_backlog(HERE)          # ⑪ 验收口两堆（函数在这份文件里，判据只有这一份）

    # ⑫：车道"一轮要多长"的分布，每拍顺手落一份。为什么要它：五·二十七 那条规矩是
    # 改第②格 45 分门槛要连续几拍分布＋真停摆负对照，不能凭一拍就改。
    # 这条腿只读（各扇自己的 jsonl），失败不许掀掉这一轮巡逻。
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "_lane_round_len_census_r1.py"), "--append"],
                       capture_output=True, timeout=120, cwd=HERE,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    except Exception as e:
        print(u"⑫ 一轮时长分布：这一拍没落（%s）⇒ 攒数据慢一拍，不掀巡逻" % type(e).__name__)

    # 不可判**不算绿**（20:18 装）：②b 那几扇若不进结论行，待看档与下一班都会把它读成"全队都在动"
    # ——单向致盲：②b 看得见、结论行看不见。形状闸越界的那些扇不能没人看见。
    if knock:
        _concl = u"有扇该敲"
    elif undecidable:
        _concl = u"有 %d 扇末态不可判（判词读不到，不算绿）" % len(undecidable)
    elif waiting:
        _concl = u"没人该敲；缺单的那 %d 扇等包工头点" % len(waiting)
    else:
        _concl = u"全队都在动"
    print(u"结论：%s" % _concl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
