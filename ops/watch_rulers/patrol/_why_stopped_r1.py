# -*- coding: utf-8 -*-
"""谁停了、为什么停——只读流水尾巴做分类，不发消息、不动任何人的东西。

为什么要它：objective 是「停下的就把话传到」，但**话有两种**：
  · 等裁语/等单 ⇒ 该敲号令者（他自己给过承诺：清单送到他就裁）；
  · 卡在第一/第二道闸 ⇒ 该敲那扇车道本人，把拒绝原话递回去；
  · 额度停 ⇒ 谁都不能立刻解决，敲了也没用（昨夜实测：等回血不能当计划）；
  · 结尾是没回音的 tool_use ⇒ 那是真断了，属于「叫一下就会回来」的那一类。
以前我只能看 autumn_watch 的名册（它只分「停在额度」和「静默非闸」两格，粒度不够），
所以自己拍脑袋敲错扇窗过。这一版把**尾条原文**贴出来，判断留给我，但证据是它现读的。

尾部只读 240 KB/扇；时间戳三形制都认。分不出来的就写「分不出」，不许猜成某一类。
"""
import io
import json
import os
import re
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FLEET = [
    ("494abfd7", u"号令者"), ("42d1a6fa", u"我"),
    ("6a150e1e", u"车道"), ("da46954a", u"车道"), ("5a53846b", u"车道"),
    ("8ac89982", u"车道"), ("2d2d7428", u"车道"), ("e766b154", u"车道"),
    ("6a773af1", u"车道"), ("0afdb49b", u"车道"), ("1ba48dbf", u"车道"),
    ("82f55d8a", u"车道"), ("1d64acf5", u"车道"), ("cff87c64", u"车道"),
]

# 名单是死的、车队是活的：夜里会冒出新车道（10-01 的「newlane」「新车道472」都不在这张表里）。
# 所以名册一律从文件系统推——凡最近 DISCOVER_MIN 分钟内动过流水的 id 都算在册，
# 表里有的照表给花名，表外新出现的标成「名单外新扇」，绝不因为搜不到名字就当它不存在。
DISCOVER_MIN = 360.0


def discover():
    now = time.time()
    rows = list(FLEET)
    known = set(p for p, _w in FLEET)
    extra = []
    for p in os.listdir(PROJ):
        if not p.endswith(".jsonl"):
            continue
        id8 = p[:8]
        if not re.match(r"^[0-9a-f]{8}$", id8) or id8 in known:
            continue
        mt = os.path.getmtime(os.path.join(PROJ, p))
        if (now - mt) / 60.0 <= DISCOVER_MIN:
            extra.append((id8, u"名单外新扇"))
    for x in sorted(extra):
        rows.append(x)
    return rows, len(extra)

QUOTA = (u"额度", u"配额", u"credits", u"quota", u"用完", u"撞墙")
# 01:21 那遍把「两道闸都干净」「逐枚可 cat-file」这种**自证清白**的句子按关键词读成了「卡闸」（7 扇误标）。
# 收窄：必须出现被拒的形制，且同一句里不能有清白声明；只提一下闸/`cat-file` 的算「提闸」，不当状态。
GATE = (u"REFUSED", u"ABORT", u"Q43_GATE_RED", u"rc=9", u"rc=1\n", u"闸拒", u"不可解析",        u"门拒", u"被拒", u"拒 1", u"拒 2")
CLEAN = (u"都干净", u"两道闸都干净", u"GREEN", u"WOULD-LAND", u"WOULD CARRY", u"可插", u"rc=0",
         u"inserted", u"已插")
MENTION = (u"cat-file", u"闸", u"Q43")
RULING = (u"等裁", u"待裁", u"等号令者", u"等一句", u"PARKED", u"parked", u"等派单", u"无裁语", u"等点单", u"你点单",
          # 10-03 06:14 现形：车道**主动请裁**的那一格词面是「请裁的三个形状（我推荐甲）」与「候裁项」「请裁形状」，
          # 旧词表只认「等/待」开头的被动形，于是「已经把手伸到你面前等你点」这一形会整格漏掉。
          # 6a150e1e 的 undelete 甲乙丙与 82f55d8a 的归属撞车报备都是这一形。
          u"请裁", u"候裁", u"请号令者", u"等一句裁", u"请点单", u"等这一句")
# 「等裁」这四个字也会出现在**反面**句子里。10-03 05:59 现形：5a53846b 尾条逐字是
# 『停等裁语已照做』（它照号令者『停止等裁语』那一句去做了），旧尺按词面抓到「等裁」⇒ 判成在等裁语，
# 我就会去敲号令者一记不存在的需求。先把这些反形剥掉再比词。
RULING_NEG = (u"停止等裁", u"停等裁", u"不再等裁", u"不等裁", u"勿等裁", u"已停止等", u"无需等裁")
DONE = (u"已交", u"已投递", u"落地", u"inserted", u"closed", u"收件口")
# 意图句：话说出去了、下一只手没落。判这一档时必须同句里没有 DONE 那批词，
# 否则「我先…，已经交了」那种收尾会被误抓成半路停（10-03 05:44 拿 16 扇现流校过）。
INTENT = (u"我先", u"我再", u"接下来", u"下一步", u"回头", u"马上", u"同时在", u"再读一遍", u"先去", u"待我")


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
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return time.mktime(time.strptime(s[:19], f))
        except Exception:
            continue
    return None


def texts_of(rec):
    """把一条记录里的可读文本都取出来（assistant text / tool_use 名 / tool_result 头部）。"""
    out = []
    m = rec.get("message") if isinstance(rec.get("message"), dict) else None
    if m:
        c = m.get("content")
        if isinstance(c, str):
            items = [{"type": "text", "text": c}]
        elif isinstance(c, list):
            items = c
        else:
            items = []
        for x in items:
            if not isinstance(x, dict):
                continue
            t = x.get("type")
            role = unicode_s(m.get("role"))
            if t == "text":
                out.append((u"text:" + role, x.get("text") or u""))
            elif t == "tool_use":
                inp = x.get("input")
                s = json.dumps(inp, ensure_ascii=False)[:160] if inp else u""
                out.append((u"tool_use", unicode_s(x.get("name")) + u" " + s))
            elif t == "tool_result":
                cc = x.get("content")
                head = cc if isinstance(cc, str) else json.dumps(cc, ensure_ascii=False)
                out.append((u"tool_result", head[:160]))
    at = rec.get("attachment")
    if isinstance(at, dict):
        pr = at.get("prompt")
        if isinstance(pr, list):
            for x in pr:
                if isinstance(x, dict) and x.get("text"):
                    out.append((u"queued_command", x["text"]))
        elif isinstance(pr, str):
            out.append((u"queued_command", pr))
    return out


def unicode_s(v):
    return v if isinstance(v, str) else str(v)


def main():
    idle_min = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0
    now = time.time()
    fleet, n_extra = discover()
    rows = []
    for pre, who in fleet:
        cands = [p for p in os.listdir(PROJ) if p.startswith(pre) and p.endswith(".jsonl")]
        if not cands:
            rows.append((pre, who, None, None, u"流水不在", u""))
            continue
        path = os.path.join(PROJ, cands[0])
        mt = os.path.getmtime(path)
        size = os.path.getsize(path)
        with io.open(path, encoding="utf-8", errors="replace") as f:
            f.seek(max(0, size - 240000))
            if size > 240000:
                f.readline()
            data = f.read()
        recs = []
        for line in data.split(chr(10)):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
        flat = []
        for r in recs:
            for k, t in texts_of(r):
                e = epoch_of(r.get("timestamp"))
                flat.append((e, k, t))
        last_asst = next(((e, t) for e, k, t in reversed(flat) if k.startswith(u"text:assistant")), (None, u""))
        last_any = flat[-1] if flat else (None, u"?", u"")
        ends_on_tool = bool(recs) and any(k == u"tool_use" for e, k, t in flat[-3:])
        has_result_after = False
        for e, k, t in reversed(flat):
            if k == u"tool_result":
                has_result_after = True
                break
            if k == u"tool_use":
                break
        hay = (last_asst[1] or u"") + u" " + last_any[2]
        clean_now = any(w in hay for w in CLEAN)
        tags = []
        if any(w in hay for w in QUOTA):
            tags.append(u"额度")
        if any(w in hay for w in GATE) and not clean_now:
            tags.append(u"卡闸")
        elif any(w in hay for w in MENTION):
            tags.append(u"提闸")
        hay_pos = hay
        for w in RULING_NEG:
            hay_pos = hay_pos.replace(w, u"")
        if any(w in hay_pos for w in RULING):
            tags.append(u"等裁语")
        if any(w in hay for w in DONE):
            tags.append(u"谈交付")
        if not tags:
            # 新增一档（10-03 05:44 现形）：尾条是自己写下的**意图句**（「我先看…同时在 day25 上把三屏再读一遍」），
            # 那句之后 0 枚工具调用、也没有交付陈词就断了。旧版把这归进「分不出」⇒ 一晚上只有我肉眼读出来，
            # 尺子看不见就等于不会去敲。它与「结尾是 tool_use 无回音」是两种断法：那一种是工具没回音，这一种是话说出去了手没落下来。
            tail_txt = last_asst[1] or u""
            if ends_on_tool and not has_result_after:
                tags = [u"结尾是 tool_use 无回音"]
            elif any(w in tail_txt for w in INTENT) and not any(w in tail_txt for w in DONE):
                tags = [u"意图句后就停了"]
            else:
                tags = [u"分不出"]
        verdict = u"、".join(tags)
        rows.append((pre, who, mt, last_asst[0], verdict, (last_asst[1] or last_any[2]).replace(chr(10), u" ⏎ ")[:170]))

    print(u"%s｜静 >= %.0f 分算停" % (time.strftime("%H:%M:%S", time.localtime(now)), idle_min))
    print(u"名册 %d 扇（名单外新扇 %d 扇；在册判据＝最近 %.1f 小时动过自己流水）" % (
        len(fleet), n_extra, DISCOVER_MIN / 60.0))
    stopped = [r for r in rows if r[2] is not None and (now - r[2]) / 60.0 >= idle_min]
    alive = [r for r in rows if r[2] is not None and (now - r[2]) / 60.0 < idle_min]
    print(u"在写（<%.0f 分）%d 扇：%s" % (idle_min, len(alive), u"、".join(r[0] for r in alive)))
    print(u"停了 %d 扇：\n" % len(stopped))
    for pre, who, mt, _le, verdict, snippet in sorted(stopped, key=lambda x: x[2]):
        print(u"  %-9s %-4s 静 %3d 分｜判：%s" % (pre, who, int((now - mt) / 60), verdict))
        print(u"          尾：%s" % snippet)
    # 汇总：这一拍到底该敲谁
    need_cmdr = [r[0] for r in stopped if u"等裁语" in r[4]]
    need_lane = [r[0] for r in stopped if (u"卡闸" in r[4] or u"结尾是 tool_use 无回音" in r[4]
                                         or u"意图句后就停了" in r[4])]
    need_quota = [r[0] for r in stopped if u"额度" in r[4]]
    unk = [r[0] for r in stopped if r[4] == u"分不出"]
    print(u"\n该敲号令者（等裁语）：%s" % (u"、".join(need_cmdr) or u"无"))
    print(u"该敲车道本人（卡闸/断在半路）：%s" % (u"、".join(need_lane) or u"无"))
    print(u"额度类（敲了也不会立刻有解）：%s" % (u"、".join(need_quota) or u"无"))
    print(u"分不出（要人工看尾巴，别乱敲）：%s" % (u"、".join(unk) or u"无"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
