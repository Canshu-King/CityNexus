# -*- coding: utf-8 -*-
"""静默名单 → 收件口的一块（号令者 19:54 重排单点名的那一手）。只测、只排版，不插账本。

形制与 `_idle_census_compose_r1.py` 同一口径：**所有数从尺上取**，槽位一律 `.format(**dict)`，
不用 `%` 位置参数（09-30 串位教训）。任何一格取不到就 REFUSE 不落笔，宁可这块不交。

尺源三处，各有分工：
  · `_why_stopped_r1.py 45` / `25` ⇒ 谁停了、静几分钟、判成哪一类（额度墙单列，敲了也没用）；
  · 中枢账 `agent_bus/bus.jsonl` + `state.json` ⇒ 各扇**未取**的 BB 机条数（未送达且未回执）；
  · `_sentinel_relay_gdone.json` + 中枢账里的 `band:` 回执 ⇒ alarm 腿到底投出去了几枚。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BUS = r"D:\moodle\agent_bus"
LEDGER = os.path.join(BUS, "bus.jsonl")
STATE = os.path.join(BUS, "state.json")
GDONE = os.path.join(HERE, "_sentinel_relay_gdone.json")
INBOX = r"D:\moodle\_qoder_ledger_inbox"
TIP = u"bf4f776b0ba943b88817dfcc0cb3442d75fd9e21"
AUTH_REF = u"refs/heads/mirror/integration-frontend-apple-pass1"   # 权威线（号令者侧唯一写者推的那条）
BOARD = u"http://127.0.0.1:4820/api/fleet"
REPO = r"D:\moodle\CityNexus"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROW = re.compile(r"^\s{2}([0-9a-f]{8})\s+(\S+)\s+静\s+(\d+) 分｜判：(.*)$", re.M)
NAMES = re.compile(u"^名册 (\\d+) 扇（名单外新扇 (\\d+) 扇", re.M)
STOPPED = re.compile(u"^停了 (\\d+) 扇", re.M)
WRITING = re.compile(u"^在写（<\\d+ 分）(\\d+) 扇：(.*)$", re.M)
QUOTA = re.compile(u"^额度类（敲了也不会立刻有解）：(.*)$", re.M)


def die(msg):
    print(u"REFUSE：" + msg)
    return 1


def why(thr):
    out = subprocess.run([sys.executable, os.path.join(HERE, "_why_stopped_r1.py"), str(thr)],
                         capture_output=True).stdout.decode("utf-8", "replace")
    d = {"out": out, "thr": thr, "rows": [], "names": -1, "fresh": -1, "stopped": -1,
         "quota_raw": None, "at": None}
    m = re.search(r"^(\d\d:\d\d:\d\d)｜静", out, re.M)
    if m:
        d["at"] = m.group(1)
    if STOPPED.search(out):
        d["stopped"] = int(STOPPED.search(out).group(1))
    if NAMES.search(out):
        mm = NAMES.search(out)
        d["names"], d["fresh"] = int(mm.group(1)), int(mm.group(2))
    if QUOTA.search(out):
        d["quota_raw"] = QUOTA.search(out).group(1).strip()
    for r in ROW.finditer(out):
        d["rows"].append({"id8": r.group(1), "who": r.group(2), "idle": int(r.group(3)),
                          "verdict": r.group(4).strip()})
    return d


def unread():
    """未取＝进了账、既没人取走也没回执。与看板同一把定义，两处不许各说一套。"""
    acks = json.load(io.open(STATE, encoding="utf-8")).get("acks", {})
    rows = [json.loads(l) for l in io.open(LEDGER, encoding="utf-8", errors="replace") if l.strip()]
    per = {}
    for m in rows:
        if m.get("delivered_at") or acks.get(m.get("id")):
            continue
        per[str(m.get("to"))] = per.get(str(m.get("to")), 0) + 1
    band = [m for m in rows if m.get("kind") == "alarm" and str(m.get("topic", "")).startswith("band:")]
    return per, band, len(rows)


def tip_ok():
    q = subprocess.run(["git", "cat-file", "-e", TIP + u"^{commit}"], cwd=REPO, capture_output=True)
    if q.returncode != 0:
        return None
    log = subprocess.run(["git", "log", "-1", "--format=%ad %s", "--date=format:%m-%d %H:%M", TIP],
                         cwd=REPO, capture_output=True).stdout.decode("utf-8", "replace").strip()
    return log.split(u" -- ")[0][:64]


def anchor(marker):
    """把「这一格的数是哪一行算出来的」当坐标写进块里——门要的 path:line 就得是真行号。
    行号在**落笔这一刻**从本文件里找：手抄的行号会随上游位移烂掉（今天已为此返工过一次）。"""
    here = os.path.abspath(__file__)
    for i, line in enumerate(io.open(here, encoding="utf-8").read().splitlines(), 1):
        if marker in line:
            return u"%s:%d" % (os.path.basename(here), i)
    raise RuntimeError("锚点标记不在本文件里：" + marker)


def chunked(items, n):
    """一行的数太多，门的 ±200 字窗口就盖不全最后几枚；每 n 枚一行、行尾各带自己的锚。"""
    lines = []
    for i in range(0, len(items), n):
        lines.append(u"、".join(items[i:i + n]))
    return lines


def newer_tip():
    """号令者 19:54 单上给的尖，与他自己在收件口最新那枚块里报的「落地后现尖」可能已经不是同一枚。
    取法：只读他块里那一行的 40 位，并本机 `cat-file -e` 验一遍；对不上就整句不提，不猜。"""
    try:
        blocks = sorted([os.path.join(INBOX, f) for f in os.listdir(INBOX)
                         if f.startswith("cmdr_") and f.endswith(".md")],
                        key=os.path.getmtime)
    except Exception:
        return None
    for p in reversed(blocks):
        try:
            txt = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for m in re.finditer(u"现尖[^0-9a-f]{0,8}([0-9a-f]{40})", txt):
            t = m.group(1)
            if t == TIP:
                continue
            if subprocess.run(["git", "cat-file", "-e", t + u"^{commit}"], cwd=REPO,
                              capture_output=True).returncode == 0:
                return t, os.path.basename(p)
    return None


def live_tip():
    """尖一律**现读**：`ls-remote` 拿远端权威线那 40 位，再本机 `cat-file -e` 验一遍。
    写死一枚（哪怕上一轮刚抄对）都会在号令者推线之后变成假坐标——今天已经为此返工过一次。"""
    q = subprocess.run(["git", "ls-remote", "--refs", "origin", AUTH_REF],
                       cwd=REPO, capture_output=True, timeout=120)
    line = q.stdout.decode("utf-8", "replace").strip()
    if not line:
        return None, u"ls-remote 对 %s 回空" % AUTH_REF
    sha = line.split()[0]
    if subprocess.run(["git", "cat-file", "-e", sha + u"^{commit}"], cwd=REPO,
                      capture_output=True).returncode != 0:
        return None, u"ls-remote 回的 %s 本机不可解析" % sha[:12]
    log = subprocess.run(["git", "log", "-1", "--format=%ad %s", "--date=format:%m-%d %H:%M", sha],
                         cwd=REPO, capture_output=True).stdout.decode("utf-8", "replace").strip()
    return sha, log.split(u" -- ")[0][:64]


def board_read():
    """看板那把「自产出尺」：未接 BB 机的窗口、末条是平台错误回话的窗口，都从它取。
    为什么两块尺都要报：`_why_stopped_r1.py` 按文件 mtime 判（与号令者同源，便于他核对），
    而 22:3x 实测证明 mtime 会把「外壳被碰过」「末条是掉线回话」都读成在写。
    取不到就整格写不可得，绝不拿旧读数冒充现测。"""
    import urllib.request
    try:
        op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        d = json.loads(op.open(BOARD, timeout=40).read().decode("utf-8"))
    except Exception as e:
        return None
    rows = d["rows"]
    return {"at": d["at"], "counts": d["counts"],
            "unreg": [(r["id8"], r["idle_min"]) for r in rows if not r["in_hub"]],
            "drops": [(r["id8"], r["idle_min"], r["unread"]) for r in rows if r["state"] == "dropped"]}


def main():
    w45 = why(45)
    w25 = why(25)
    for d in (w45, w25):
        if d["names"] < 0 or d["stopped"] < 0 or d["at"] is None:
            return die(u"_why_stopped_r1.py %d 分档没回话（名册/停了/时刻任一格取不到）" % d["thr"])
    per, band, nrows = unread()
    gd = json.load(io.open(GDONE, encoding="utf-8")) if os.path.exists(GDONE) else {}
    gkeys = sorted(gd)
    tip = tip_ok()
    if not tip:
        return die(u"权威尖 %s 本机 cat-file 不可解析 ⇒ 不写进块里当坐标" % TIP[:12])
    nt = newer_tip()
    live, live_log = live_tip()
    if not live:
        return die(u"现读权威线失败（%s）⇒ 不写坐标" % live_log)
    bd = board_read()

    def u_of(id8):
        return per.get(u"qoder:" + id8, 0)

    near = [r for r in w25["rows"] if r["idle"] >= 40]
    over = [r for r in w45["rows"]]
    top_un = sorted([(k, v) for k, v in per.items() if v], key=lambda x: -x[1])
    # selftestprobe 是我 04:5x 打的那枚探针，不是哨兵自己投的；混进回执数里就是拿假数报覆盖。
    real = [m for m in band if u"selftestprobe" not in m["topic"]]
    band_ids = sorted(set(re.sub(r"^band:[IJK]:\d{4}:", u"", m["topic"]) for m in real))
    no_copy = [k.split(u"|")[2] for k in gkeys if k.split(u"|")[2] not in band_ids]
    lanes = [r["id8"] for r in (w45["rows"] + w25["rows"])]
    zero_un = w45["names"] - len([k for k in per if k.startswith(u"qoder:") and per[k]])

    vals = {
        "now": time.strftime("%H:%M:%S"), "at45": w45["at"], "at25": w25["at"],
        "tip_note": (u"- **两枚尖不是同一枚**：你 19:54 单上给的是 `{tip}`，你收件口那枚 `{tip2_src}` 里报的现尖是 "
                     u"`{tip2v}`——两枚本机 `git cat-file -e` 都可解析。我按单上那枚引用，权威线仍以你侧为准（我不移动它）。"
                     ).format(tip=TIP, tip2_src=nt[1], tip2v=nt[0]) if nt else u"",
        "names": w45["names"], "fresh": w45["fresh"], "s45": w45["stopped"], "s25": w25["stopped"],
        "quota45": w45["quota_raw"], "near_n": len(near),
        "a_head": anchor(u'"s45": w45["stopped"]'), "a_near": anchor(u'"near": u"、".join('),
        "a_rows": anchor(u'"rows25": u"、".join('), "a_un": anchor(u'"unread_ids": u"、".join('),
        "a_band": anchor(u'"band_n": len(real)'), "a_why": anchor(u"def why(thr):"),
        "a_names": anchor(u'"names": w45["names"]'),
        "head": (u"**静默超 45 分且额度没墙：{s45} 扇（无）**——45 分档那一跑「停了 {s45} 扇」，"
                 u"额度类「{quota45}」。空有空的凭据：名册 {names} 扇与两档分钟数都在下面，"
                 u"不是搜不到就当不存在。").format(**{"s45": w45["stopped"], "quota45": w45["quota_raw"],
                                                     "names": w45["names"]})
                if w45["stopped"] == 0 else
                (u"**静默超 45 分且额度没墙：{n} 扇** —— {who}；45 分档那一跑「停了 {s} 扇」，额度类「{q}」。"
                 ).format(n=w45["stopped"], who=u"、".join(u"%s %d 分（判：%s）" % (r["id8"], r["idle"], r["verdict"])
                                                          for r in over), s=w45["stopped"], q=w45["quota_raw"]),
        "near": u"、".join(u"%s %d 分（%s，判：%s，未取 %d 条）"
                          % (r["id8"], r["idle"], r["who"], r["verdict"], u_of(r["id8"])) for r in near)
                  or u"（无）",
        "rows25": u"、".join(u"%s %d 分" % (r["id8"], r["idle"]) for r in w25["rows"]) or u"（无）",
        "ledger_rows": nrows,
        "unread_ids": u"\n".join(u"   - " + x + u"｜锚 " + anchor(u'"unread_ids": u"、".join(')
                                 for x in chunked([u"%s %d 条" % (k, v) for k, v in top_un], 3))
                               or u"（全体为 0）",
        "unread_lanes": sum(v for k, v in per.items() if k.startswith(u"qoder:")),
        "zero_un": zero_un, "star_un": per.get(u"*", 0),
        "band_n": len(real), "probe_n": len(band) - len(real), "band_ids": u"、".join(band_ids) or u"（无）",
        "gdone_n": len(gkeys), "no_copy_n": len(no_copy),
        "no_copy": u"、".join(no_copy) or u"（无）",
        "tip": live, "tip_log": live_log, "tip_ordered": TIP, "tip_ordered_ok": tip,
        "a_bd": anchor(u"def board_read():"),
        "board_at": (bd or {}).get("at", u"（看板取不到：尺不可得）"),
        "board_counts": u"、".join(u"%s %s" % (k, v) for k, v in sorted((bd or {}).get("counts", {}).items())),
        "unreg_n": len(bd["unreg"]) if bd else u"不可得",
        # 门的窗口是 ±200 字：一行里塞太多枚，行尾那枚锚就够不着行首的数（22:56 实测拒过 5 枚）。
        # 所以凡"逐枚列举"一律切小行，每行自带锚——与未取条数同一形制。
        "unreg": u"\n".join(u"   - " + x + u"｜锚 " + anchor(u'"unreg": u"\\n".join(')
                            for x in chunked([u"%s（静 %s 分）" % (i, m) for i, m in bd["unreg"]], 2))
                            if bd else u"不可得",
        "drops_n": len(bd["drops"]) if bd else u"不可得",
        "drops": u"\n".join(u"   - " + x + u"｜锚 " + anchor(u'"drops": u"\\n".join(')
                            for x in chunked([u"%s 静 %s 分·未取 %s 条" % (i, m, un)
                                              for i, m, un in bd["drops"]], 2))
                            if bd else u"不可得",
    }
    body = BLOCK.format(**vals)
    out = os.path.join(INBOX, u"%s_%s.md" % ("42d1a6fa", time.strftime("%H%M")))
    print(u"—— 现测（尺上取的，不是手打）——")
    for k in ("at45", "at25", "names", "fresh", "s45", "s25", "quota45", "near_n", "band_n", "probe_n",
              "gdone_n", "no_copy_n", "unread_lanes", "zero_un", "star_un"):
        print(u"   %s = %s" % (k, vals[k]))
    print(u"   newer_tip = %s" % (nt,))
    if u"--apply" not in sys.argv:
        print(u"\n—— 预览（未落盘）——\n" + body)
        print(u"\nREFUSE 之外：--apply 才写 " + out)
        return 0
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    print(u"\n已写：" + out + u"｜%d 字节" % os.path.getsize(out))
    return 0


BLOCK = u"""### 值守车道 · 静默名单 {now}（45 分档 {s45} 扇｜额度墙 {quota45}）

**尺源**：`_why_stopped_r1.py` 两跑（45 分档 {at45}、25 分档 {at25}；跑它的那只手 {a_why}）＋ 中枢账 `agent_bus/bus.jsonl`（{ledger_rows} 行）。
名册 {names} 扇（其中名单外新扇 {fresh} 扇，在册判据＝最近 6 小时动过自己流水；{a_names}）。权威尖 `{tip}`（本机 `git cat-file -e` 可解析；{tip_log}）。

- {head}｜锚 {a_head}
- 近旁（25 分档停了 {s25} 扇，其中静 ≥40 分的 {near_n} 扇）：{near}｜锚 {a_near}
- 25 分档全量：{rows25}｜锚 {a_rows}
- **各扇未取的 BB 机条数**（未取＝进了账、既没取走也没回执）：车道合计 {unread_lanes} 条，其余 {zero_un} 扇为 0；通播（`to=*`）未取 {star_un} 条｜锚 {a_un}
  分账号（每行一枚锚，门的 ±200 字窗口才盖得住）：
{unread_ids}
- **alarm 腿已接哨兵**（你 19:54 点名要的那件）：账上哨兵自己投的 `band:` 回执 {band_n} 枚，具名 {band_ids}（另有 {probe_n} 枚是我手打的探针，不计进覆盖）。`_sentinel_relay_gdone.json` 今天记了 {gdone_n} 枚 I/J 判定，其中 {no_copy_n} 枚只有窗口敲门、没有 BB 机耐久副本：{no_copy}。成因已修在尺上：正文里的分钟数会在中枢重跑那一刻漂掉（06:55 那枚就是这么被拒的），且旧写法先记重账再投递＝「看着报过、其实没人收到」；现在投递失败不记重账、下一轮再试｜锚 {a_band}
- **未接 BB 机的窗口（你 22:11 点名要的那格）：{unreg_n} 扇**，它们收不到任何 order/ack，点名只能靠敲窗口：
{unreg}
- **末条是平台错误回话（掉线，不是偷懒）：{drops_n} 扇**，逐字是「Unable to connect to the service, or the connection was interrupted…」；这 {drops_n} 扇的最后一轮被链路掐断，**不会自己回来**，要重发那一轮。我这侧的 send_message 腿对你们委派出来的会话是关着的（平台原话：「由其他会话委派的任务必须直接执行，不能继续向其他会话转发消息」），所以这一格只能你或主人重发：
{drops}
- 第二把尺（自产出，看板 {board_at}）：{board_counts}｜锚 {a_bd}
- 我这一侧另有一处已认账的外发：20:11 前后 `human:you01` 通播全体那枚是主人那块人看的看板的投递自测，已补 `board:human-selftest-no-ack` 具名说明「不必回执、不必转达」。
{tip_note}

下一手仍归号令者：物理点名与派单；我不敲静默未过档、且无未取的车道，也不代插账本。

**门上那条 ADVIDSORY 我不遮**：本块的数只由脚本行号担保（不是 git 树里的坐标），因为舰队状态本来就不在版本库里。
要复核就重跑这一条，它会把上面每个数重新取一遍：`python D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_idle_census_ledger_r1.py`
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
"""

if __name__ == "__main__":
    sys.exit(main())
