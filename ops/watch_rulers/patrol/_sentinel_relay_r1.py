# -*- coding: utf-8 -*-
"""值守哨兵 r1：把「该不该由我把话传到」这一判断装进脱离回合的循环里，而不是靠我下一班想起来。

为什么现在建（10-01 14:42）：用户要的是「车道停下的就把话传到，保证车队工作到 23:00」。
真判据只有三条，全部来自流水与账本收件口，不看进程也不看端口：
  A 无人接的单 > 0 张（`_unclaimed_orders_r1.py`，3 小时窗）——有单没人接才值得我敲门；
  B 叫醒后仍未回话 > 0 条，或「停在额度字样且没人接」> 0 条（`_restart_watch_r1.py`）；
  C 连续两拍「在写 0 条」（`_quota_roster_r1.py` 的名册第一行）——整队没人动，这才是停摆。
任何一条红就早退并打印现场，绿就按点续跑；本脚本 0 发送、0 写账本、0 上总线（只写自己那份日志）。

用法：PYTHONIOENCODING=utf-8 python _sentinel_relay_r1.py [总分钟数=480] [每轮秒数=900]
边界：A 那把尺自带 ls-remote，一轮约 30—60 秒；额度潮的叫醒归号令者（我抢发会让车道重做已交的部分），
所以 B 红只报「该谁动」，不由我代发。C 用的是名册那一刻的现值，两拍之间看不见；取不到数一律算红，不算绿。
判定本体在 pass_once()，所以 `_sentinel_selftest_r1.py` 能用合成读数逐条验它报不报得出红。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PYEXE = sys.executable
LOG = os.path.join(HERE, "_sentinel_relay_latest.log")
# G 档「同一枚块只报一次」的账要跨重启活下来：续跑器或一键起复把哨兵重起之后，
# 若不落盘，同一条我已经送过原话的块会再顶红一次 ⇒ 我会再敲一次同一扇窗（重复投递）。
GDONE = os.path.join(HERE, "_sentinel_relay_gdone.json")

def why_stopped_line(id8):
    u"""拿分类器 `_why_stopped_r1.py` 对这一扇的「判：…」原文。

    取不到返回 None（**不回退到手写成因**——20:35 那次假红就是手写那句造成的）。
    它每拍被调一次（子进程只读流水，秒级返回），所以只在 J 档真有候选时才问。
    """
    import subprocess
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "_why_stopped_r1.py")],
                           capture_output=True, cwd=HERE, timeout=180,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        txt = (r.stdout or b"").decode("utf-8", "replace")
    except Exception:
        return None
    for line in txt.splitlines():
        # 行首有两个空格（实测 20:40 那行："  1d64acf5  车道 …"）⇒ 必须 strip 后再比，
        # 直接 startswith(id8) 恒 False，取不到判词就一路 None（我 20:40 踩过）。
        _ls = line.strip()
        if not _ls.startswith(id8):
            continue
        m = re.search(u"判：(.*)$", line)
        if m:
            return m.group(1).strip()
    return None


def load_gdone():
    try:
        d = json.loads(io.open(GDONE, encoding="utf-8").read())
    except Exception:
        return {}
    today = time.strftime("%m%d")
    return dict((k, v) for k, v in d.items() if k.startswith(today + "|"))

def save_gdone(g):
    old = {}
    try:
        old = json.loads(io.open(GDONE, encoding="utf-8").read())
    except Exception:
        old = {}
    old.update(g)
    today = time.strftime("%m%d")
    keep = dict((k, v) for k, v in old.items() if k.startswith(today + "|"))
    try:
        io.open(GDONE, "w", encoding="utf-8", newline="\n").write(json.dumps(keep, ensure_ascii=False, sort_keys=True))
    except Exception:
        pass
HIT = os.path.join(HERE, "_sentinel_relay_HIT.txt")
REPO = r"D:\moodle\CityNexus"
LC = os.path.dirname(HERE)
GATE = os.path.join(LC, "claim_coordinate_check_r7.py")
TIPREF = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
D_TIP_MIN = 90          # 尖静止多少分钟算红
D_QUEUE_MIN = 8         # 同时队列至少几枚才算「互等停摆」
D_STREAK_EXIT = 3       # 连红几拍（3 拍 ≈ 45 分）就早退交人
F_DOOR_MIN = 20.0       # 待插最老到多少分钟算门停（只数「门绿真能插」那几枚）
G_BOLT_MIN = 40.0       # 一枚块被「第二道闸」拒到多少分钟就叫我（这一格的动作是送原话回车道，不是敲号令者）
I_WAIT_MIN = 45.0       # 车道尾条明写「等点单/等裁」到多少分钟就敲号令者（裁语只能他给）
I_GATE_WRITING = 6      # 只有名册「在写」<= 这个数才去逐扇读尾条：整队都在动时没必要扫 14 份流水
J_STALL_MIN = 40.0      # 车道断在半路（尾条是没回音的 tool_use）静到多少分钟才叫人
K_MODEL_MIN = 20.0      # 「等模型回包」到多少分钟算卡住：结果早回来了、模型没出下一句，那一轮不会自己回来
_BOARD_DENOM = {"rows": -1, "retired": -1}   # K/L 产出带分母用；-1＝这一拍没取到板（不写 0 冒充分母）
L_DROP_MIN = 15.0       # 末条是平台错误回话（掉线）到多少分钟就叫：这一类昨夜一次掐了七扇，没人报过
K_BOARD_URL = os.environ.get("SR_BOARD", "http://127.0.0.1:4820/api/fleet")
J_EXCLUDE = (u"494abfd7", u"42d1a6fa")   # 号令者与我：我们的死尾有已知良性成因（重启腰斩、上下文压缩），且叫醒他的动作本身就是一记敲门，会自我循环
B_STREAK_EXIT = 2        # B（没回声）连几轮才叫人
H_TIP_MIN = 150         # 尖静止多少分钟算「落地这一格没人推」（不看队列大小）
H_QUEUE_MIN = 3         # 配合上一枚：至少还有几枚候选在等
E_STREAK_EXIT = 2       # 同一枚块连几轮都被闸拒才叫醒我（单轮红只记不叫，见 pass_once 里那段实测）
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def run(script, arg=None, timeout=900):
    cmd = [PYEXE, os.path.join(HERE, script)] + ([arg] if arg else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=HERE, timeout=timeout)
        return (r.stdout or "") + (r.stderr or ""), r.returncode
    except Exception as e:
        return "%s: %s" % (type(e).__name__, str(e)[:160]), 99

def say(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    with io.open(LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    print(line)

def tip_age_min():
    """权威尖多久没动：读**本地镜像 ref** 的提交时刻（不 fetch，所以 ref 若滞后，分钟数只会偏大不会偏小）。"""
    try:
        r = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%ct", TIPREF],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        ct = (r.stdout or "").strip()
        return round((time.time() - int(ct)) / 60.0, 1) if ct.isdigit() else -1.0
    except Exception:
        return -1.0

def queue_depth():
    """已申报未落地的候选枚数（与自动轮同一口径：数 `_ready_not_landed_r1.py` 里带「只读预测=」的行）。"""
    q, rc = run("_ready_not_landed_r1.py", "150")
    n = len([x for x in q.split("\n") if "只读预测=" in x])
    return (n if n or rc == 0 else -1)

def pending_red(max_n=3, min_age_min=5.0):
    """E：收件口根目录里那些「已经写完、但入账闸会拒」的块——提前量出来才轮得到我把门的原话送给写它的那条车道。

    只数龄 >= 5 分钟的（更短说明车道还在写，红是瞬时的，不该报警）；每轮最多验 3 枚（门的 committed_path 那一臂要 ls-remote，太贵）。
    取不到判语（文件已被门排空、或门自己报错）一律算「读数不全」，不算红也不算绿。
    """
    INBOX = r"D:\moodle\_qoder_ledger_inbox"
    try:
        names = [f for f in os.listdir(INBOX) if f.endswith(".md") and os.path.isfile(os.path.join(INBOX, f))]
    except Exception:
        return [], "根目录读不到"
    rows = []
    for f in sorted(names, key=lambda x: os.path.getmtime(os.path.join(INBOX, x))):
        age = (time.time() - os.path.getmtime(os.path.join(INBOX, f))) / 60.0
        if age < min_age_min:
            continue
        if len(rows) >= max_n:
            break
        r = subprocess.run([PYEXE, GATE, "--text", os.path.join(INBOX, f), "--expect-clean"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           cwd=LC, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        m = re.search(r"overall Q43_GATE_(GREEN|RED)", out)
        if not m:
            rows.append((f, "读数不全", -1))
            continue
        nf = re.search(r"findings (\d+)", out)
        rows.append((f, m.group(1), int(nf.group(1)) if nf else -1))
    return rows, ""

CENSUS_RE = re.compile(
    u"积压分类：门拒 (\\d+) 枚 / 门绿但第二道闸拒 (\\d+) 枚 / 门绿真能插 (\\d+) 枚")
GREEN_RE = re.compile(u"BLOCK_GREEN (\\S+\\.md) 已等 (\\d+) 分钟")
BOLT_RE = re.compile(u"BLOCK_GREEN_BUT_BOLTED (\\S+\\.md) 已等 (\\d+) 分钟")
_CENSUS_TAIL = {"text": None}   # G 档要把硬闸那一行的逐字判语送进车道，得留着分类尺那一拍的原文：重跑一遍闸既贵、又会把分钟数换成另一个数


def parse_census(text):
    """从 round_watch.log 的一段里取「最后一拍的分类」。读不到就返回 None，让调用方退回旧计数。

    02:24 的反例：F 用「根目录 .md 计数」判门停，量到 4 枚、最老 66 分 ⇒ 报红并叫退场；
    而同一拍 inbox_check 的分类是「门拒 0 / 闸拒 1 / 真能插 0」——那 4 枚里 3 枚是 02:20-02:22 刚落口的，
    唯一超龄的那枚是**车道侧**被第二道闸拒的，敲门给号令者也没用（他插不进去）。
    所以 F 的分子只能数「门绿真能插」那几枚，龄也只数它们的龄。
    """
    m = None
    for m in CENSUS_RE.finditer(text):
        pass
    if not m:
        return None
    # 分类行是一拍的**最后一行**，绿块与闸拒行都排在它前面 ⇒ 窗口必须往回收到本轮的「===== [」，
    # 从分类行往后收会一律数到 0（自测第一跑就是这么把它自己抓的 BLOCK_ 行漏掉的）。
    lo = text.rfind("===== [", 0, m.start())
    lo = 0 if lo < 0 else lo
    hi = text.find("===== [", m.end())
    tail = text[lo: hi if hi > 0 else len(text)]
    ages = [int(x.group(2)) for x in GREEN_RE.finditer(tail)]
    bolts = [(x.group(1), int(x.group(2))) for x in BOLT_RE.finditer(tail)]
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), (max(ages) if ages else 0.0), bolts

def door_backlog():
    """F：门停了没有——返回 (可代插枚数, 其中最老一分钟, 门拒枚数, 闸拒枚数, 备注)。

    为什么单列一条：自动轮本来就有「门停探测器」和 15/60/150/300 分四档，但它响的是**总线贴**，
    而今天实测过两回——号令者那一轮的循环里没有读总线这一步，贴到不等于看到。
    这一条要求的是**叫醒我**，因为代插只能他跑、而能去敲他窗的是我（用户 15:22 起允许这一类传话）。
    """
    INBOX = r"D:\moodle\_qoder_ledger_inbox"
    LOG = os.path.join(HERE, "round_watch.log")
    try:
        size = os.path.getsize(LOG)
        with io.open(LOG, encoding="utf-8", errors="replace") as f:
            if size > 120000:
                f.seek(size - 120000)
                f.readline()
            text = f.read()
    except Exception:
        return -1, -1.0, -1, -1, u"分类尺读不到", []
    _CENSUS_TAIL["text"] = text
    got = parse_census(text)
    if got:
        rej, bolt, green, old, bl = got
        return green, float(old), rej, bolt, u"按分类", bl
    # 退回旧口径：只数根目录的 .md，并在备注里写清这是「没分类」的读数——不许当分类用
    try:
        names = [f for f in os.listdir(INBOX) if f.endswith(".md") and os.path.isfile(os.path.join(INBOX, f))]
    except Exception:
        return -1, -1.0, -1, -1, u"收件口读不到", []
    if not names:
        return 0, 0.0, 0, 0, u"退回根目录计数", []
    ages = [(time.time() - os.path.getmtime(os.path.join(INBOX, f))) / 60.0 for f in names]
    return len(names), max(ages), -1, -1, u"退回根目录计数(未分类)", []

def actionable(reds):
    """只有「我这班动得了」的红才让哨兵早退：A 无人接（轮到我敲门）、E 会被闸拒（轮到我送门原话）。

    00:20 那一退是反例：B 连两轮「停在额度且没人接 1 条」——那一格的动作权在号令者（额度潮叫醒归他），
    我醒了也做不了什么，反而让之后几小时没人盯。**报归报，退场只留给动得了的六格：A 无人接、E 会被第一道闸拒、
    F 门停（可代插的那几枚）、G 块卡在第二道闸、C 整队停摆（19:29 之后新加：整队在 0 时我必须醒，一段只叫一次）、
    I 车道明写等点单超龄（10-03 新加：动作是敲号令者递原话，我动得了）。**
    """
    return [x for x in reds if x[:2] in (u"A ", u"E ", u"F ", u"G ", u"C ", u"I ", u"J ", u"K ", u"L ", u"M ")]

def waiting_ruling():
    """谁在「等一句裁语」——跑 `_why_stopped_r1.py 25` 取它的判定，返回 [(id8, 静默分钟)]；取不到返回 None。

    None 与 [] 必须分开：[] 是「量到了，没人在等」，None 是「这把尺没回话」。
    把「读不到」当绿就是单向致盲（它只会把『有人等』读成『没人等』，然后诱导我少敲门）。
    原文顺手存进 _WHY：J 档（断在半路）与 I 档读的是**同一把尺的同一次输出**，不再扫第二遍流水。
    """
    out = _WHY.get("text")
    if out is None:
        return None
    m = re.search(u"该敲号令者（等裁语）：(.*)$", out, re.M)
    if not m:
        return None
    line = m.group(1).strip()
    if line == u"无":
        return []
    ids = [x.strip() for x in line.split(u"、") if re.match(r"^[0-9a-f]{8}$", x.strip())]
    return [(i, _why_age(out, i)) for i in ids]

_WHY = {"text": None, "rc": None}

# 车队全集从文件系统推（不硬编码 id）；路径用 expanduser 拼，免得中文用户名过管道被吃掉
PROJ_DIR = os.path.expanduser(u"~/.qoder/projects/D--moodle")

HUB = os.environ.get("SR_HUB", "D:/moodle/agent_bus")   # 用正斜杠：反斜杠+a 会被 heredoc 写成 BEL（同一个坑第二次）
CLOSING = os.environ.get("SR_CLOSING", os.path.join(os.path.dirname(HERE), u"CLOSING_LINE.txt"))
HUB_ON = os.environ.get("SR_HUB_OFF", "0") != "1"
# 投递总闸：三条外发腿（hub_alarm / push_gate_words / push_bolt_words）唯一的开关。生产默认开＝照发。
# 10-05 17:31 的教训：自测喂的是合成分类读数，我新加的 G 投递腿把它当成现网，真往正式总线投了一条给一条没交过那枚块的车道。
# 所以规矩装在写的那个工具里：自测把这里关掉即可，不靠每条测试自己记得换桩。
SEND = {"allow": True}

QUIET_LIST = os.path.join(HERE, u"_quiet_list.txt")


def quiet_hit(id8):
    u"""报警抑制名单：一行一枚 `id8|到期 月-日 时:分|原因`，到点自动失效。

    来源（号令者 10-04 23:3x）：6efab655 被平台日限额压着，名下两格等额度恢复再催，
    「哨兵不用重复报它」。这条如果写进代码或写进我脑子里，就成了"我记得"；写进带到期
    时刻的名单，才会自己过期——明天它额度恢复了还停着，报警照旧响。
    读不懂到期时刻 ⇒ 当它不存在：宁可多报，不可漏报。
    """
    if not os.path.isfile(QUIET_LIST):
        return None
    now = time.time()
    year = time.localtime(now).tm_year
    for ln in open(QUIET_LIST, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln or ln.startswith(u"#"):
            continue
        parts = [x.strip() for x in ln.split(u"|")]
        if len(parts) < 3 or parts[0] != id8:
            continue
        try:
            exp = time.mktime(time.strptime(u"%d-%s" % (year, parts[1]), "%Y-%m-%d %H:%M"))
        except Exception:
            say(u"抑制名单这行到期时刻读不懂（%s）⇒ 忽略它，照常报警" % parts[1])
            continue
        if now < exp:
            return parts[1], parts[2]
    return None


ACCEPT_LEG = os.path.join(HERE, u"_bb_cmdr_acceptance_queue_r1.py")


def acceptance_stalled():
    u"""Q 档：跑验收队列那条腿，取「交完活且已静默」的扇数与名单。

    返回 (扇数, 名单串)；取不到或读不懂结论行返回 None——None 一律写"不可得"，不许当绿。
    """
    try:
        p = subprocess.run([PYEXE, ACCEPT_LEG], cwd=HERE, capture_output=True, timeout=150,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = (p.stdout or b"").decode("utf-8", "replace")
        m = re.search(u"可能正等验收）：(\\d+) 扇：(.*)", out)
        if not m:
            say(u"Q 档读不懂那条腿的结论行 ⇒ 写不可得（rc=%d）" % p.returncode)
            return None
        n = int(m.group(1))
        return n, m.group(2).strip()
    except Exception as e:
        say(u"Q 档取数失败（%s: %s）⇒ 写不可得" % (type(e).__name__, str(e)[:70]))
        return None


PROJECTS_DIR = os.path.expanduser(u"~/.qoder/projects/D--moodle")
HUB_URL = u"http://127.0.0.1:4799"
NL_CHAR = chr(10)
ADOPT_RECENT_MIN = 30.0


def adoption_gap():
    u"""O 档：会话流水近 30 分钟在动，却不在 BB 机名册里 ⇒ 推广缺口。

    目标里那句「给其他会话推广你制作的通讯软件」不该靠我记得去敲：这一档每轮自己比，
    比出来就走 hub_alarm 那一扇门（因此同样受抑制名单与按天幂等键管着，不会刷屏）。
    """
    try:
        import urllib.request
        st = json.loads(urllib.request.urlopen(HUB_URL + u"/agents", timeout=8)
                        .read().decode("utf-8", "replace"))
    except Exception as e:
        say(u"O 档取不到 BB 机名册（%s）⇒ 这格写不可得，不当绿" % e)
        return u"推广缺口：不可得（BB 机名册没答话）"
    on = set()
    for aid in st:
        on.add(str(aid).split(u":")[-1][:8].lower())
    cut = time.time() - ADOPT_RECENT_MIN * 60
    try:
        names = [f for f in os.listdir(PROJECTS_DIR) if f.endswith(u".jsonl")]
    except Exception as e:
        say(u"O 档读不到会话目录（%s）⇒ 这格写不可得" % e)
        return u"推广缺口：不可得（项目会话目录读不到）"
    gaps = []
    for f in names:
        path = os.path.join(PROJECTS_DIR, f)
        try:
            mt = os.path.getmtime(path)
        except Exception:
            continue
        if mt < cut:
            continue
        key = f.split(u"-")[0][:8].lower()
        if key not in on:
            gaps.append((key, int((time.time() - mt) / 60)))
    if not gaps:
        return None
    gaps.sort(key=lambda x: x[1])
    text = (u"O 档：有 %d 枚会话流水近 %d 分钟在动、却不在 BB 机名册里（%s）。"
            u"这一格的动作是递一页纸 JOIN.txt，不是替它们注册——身份要它自己认领才算自证。"
            % (len(gaps), int(ADOPT_RECENT_MIN), u"、".join(u"%s 静 %d 分" % (k, m) for k, m in gaps[:6])))
    say(u"O 档推广缺口 %d 枚：%s" % (len(gaps), u"、".join(k for k, _ in gaps[:6])))
    hub_alarm(u"O", u"sessions", text)
    return u"推广缺口 %d 枚（近 %d 分钟在动却没接 BB 机）" % (len(gaps), int(ADOPT_RECENT_MIN))


def closing_line():
    """外发尾行的原件：逐字读，不手打。读不到或短得可疑 ⇒ 返回空串，调用方据此拒发。

    这条规矩以前只贴在通报腿（tell_cmdr 那侧）和我的散文里，报警这条腿整个漏了：
    10-05 02:3x 回读自己投的 alarm，正文 282 字节里没有那 83 字节原件 ⇒ 今天所有
    band: 档警报都缺尾行。规矩要装在执行写的那个工具里，不然是我说了算、不是尺说了算。
    """
    try:
        s = io.open(CLOSING, encoding="utf-8").read().strip()
    except Exception as e:
        say(u"收尾口令原件读不到（%s: %s）⇒ 当没有" % (type(e).__name__, str(e)[:80]))
        return u""
    if len(s.encode("utf-8")) < 60:
        say(u"收尾口令原件只有 %d 字节，不像那一整句 ⇒ 当没有" % len(s.encode("utf-8")))
        return u""
    return s


def hub_alarm(band, id8, text):
    """报红的同一时刻，往 BB 机投一枚 alarm：topic 带日期 ⇒ 中枢自己的幂等键就是"按天"。

    为什么两层都要（日志红 + 中枢 alarm）：日志红只有我回来看才看得见，而中枢那一条
    号令者会读（他 04:05 起在册）。上报失败**不许改变判定**，只记一行——红该红还是该红。
    """
    topic = u"band:%s:%s:%s" % (band, time.strftime("%m%d"), id8)
    if not SEND["allow"]:
        say(u"自测挡板（SEND=off）：%s 这枚不投——这一拍喂的是合成读数，不许写正式总线" % topic)
        return ("blocked", topic)
    q = quiet_hit(id8)
    if q:
        # 留一行日志再走 skip：抑制不是"没发生"，将来对账要能看出这几轮是被名单挡下的
        say(u"抑制中（到 %s）：%s ⇒ %s 档这轮不投 alarm｜原因：%s"
            % (q[0], id8, band, q[1]))
        return ("skip", topic)
    if not HUB_ON:
        return ("skip", topic)
    cl = closing_line()
    if not cl:
        say(u"收尾口令原件不可得 ⇒ %s 这枚 alarm 不投（外发必须带逐字尾行）；"
            u"红记在本日志，不当中枢没发生" % topic)
        return ("no_closing", topic)
    text = text.rstrip() + NL_CHAR + cl + NL_CHAR
    try:
        # 04:52 探针暴露：alarm 正文里的数（「已 56 分」、id 开头的 8）不带 evidence 会被中枢自己拒收——
        # 也就是说这条腿在真消息上永远投不出去。正确做法不是放宽规则，而是把**产生这些数的那条命令**交给中枢去跑。
        cmd = [PYEXE, os.path.join(HUB, "bus.py"), "send", "--from", u"qoder:42d1a6fa",
               "--to", u"qoder:494abfd7", "--kind", "alarm", "--topic", topic, "--body", text,
               "--evidence", u"census|python " + os.path.join(HERE, "_why_stopped_r1.py") + u" 25"]
        q = subprocess.run(cmd, capture_output=True, cwd=HUB, timeout=90,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = (q.stdout or b"").decode("utf-8", "replace")
        ok = u'"id"' in out and q.returncode == 0
        if not ok:
            say(u"BB 机 alarm 没投出去（%s）：%s" % (topic, out[:120] or (q.stderr or b"").decode("utf-8", "replace")[:120]))
        return ("sent" if ok else "failed", topic)
    except Exception as e:
        say(u"BB 机 alarm 抛错（%s）：%s" % (topic, e))
        return ("error", topic)

L_DROP_MIN = 15.0       # 末条是平台错误回话（掉线）到多少分钟就叫：这一类昨夜一次掐了七扇，没人报过
M_UNREAD_MIN = 45.0     # alarm 投出去到多少分钟仍没人取，就算「传话断了」：昨夜我自己压了四到五小时
M_UNREAD_KIND_MIN = 90.0   # deliver/order（派单与交付）压到多少分钟算断档。阈值不是拍的：10-04 14:1x
                           # 实测 90 分这一刀只切中 2 组共 5 条（最老的两组是 774 与 2126 分），
                           # 既不漏「压半天」的那类，也不会一夜之间多出一片红。note/ack 暂不进叫人口径
M_BUS = u"D:/moodle/agent_bus"

# 10-05 16:1x 副号令者·夜班具名要求的第一条 M 档口径装在这里：号令者两扇之间互递的复述件
# （一扇给另一扇的 deliver/ruling/note）不再算进「谁压着信没取」的分子——否则他回一条就多一条欠账，
# 越催越响，形状与我 00:2x 实测到的那 48% 自回声同一类。数不藏：单列 _M_RELAY，日志照写具名。
# 他要的第二条（被写盘门拒的车道块算 deliver 类堆积）我先量了它现在住在哪：F 档 door_backlog()
# 已经在数「门拒枚数／闸拒枚数」，且 F 属 actionable（会叫人）。同一件事在两档各报一次＝双报警，
# 所以那条交回他或号令者裁「并档还是换口径」，我不擅自再造一枚会重复咬人的锁。
CMDR_IDS = frozenset([u"qoder:494abfd7", u"qoder:6efab655"])
# S 档（已送达却没人拆）：阈值沿用 M 那把九十分钟，不新造一刀。
S_UNACKED_MIN = 90.0
# 只有这三枚手里压着会卡住全队（号令者两扇 = 验收与裁语，主人那枚 = 他亲口的话）。
# 车道自己没 ack 自己的 order 不叫 S 红——那一类由巡逻第②格（该敲）管，免得同一件事两处各报一次。
S_FOCUS = (u"qoder:494abfd7", u"qoder:6efab655", u"human:you01")

DISK_WARN_GB = 5.0     # C 剩到多少 GiB 报预警（10-04 18:2x 实测已在这条之下）
DISK_CRIT_GB = 3.0     # 剩到多少 GiB 算严重

def disk_free_gb(drive=u"C:/"):
    """现读盘余量（GiB）。取不到返回 None——读不到就写「不可得」，绝不当绿。

    为什么要新加这一档：值守原有的水位打点（autumn_watch 里那一段）只采 `/d`，也就是
    **一直在看 D**；而真正在缩、会先撑不住的是 C——10-02 就记下过这条结论，10-04 18:2x
    再实测仍是 C 少 D 多。C 清零不是"我看不见谁在干活"，是每一扇连自己的任务流水都写不进去，
    全线一起停，且这不是把尺修修能救的那种。
    """
    try:
        import ctypes
        a = ctypes.c_ulonglong(0); t = ctypes.c_ulonglong(0); f = ctypes.c_ulonglong(0)
        ok = ctypes.windll.kernel32.GetDiskFreeSpaceExW(drive, ctypes.byref(a), ctypes.byref(t), ctypes.byref(f))
        if not ok:
            return None
        return a.value / 2 ** 30
    except Exception as e:
        say(u"盘水位取不到（%s: %s）" % (type(e).__name__, str(e)[:80]))
        return None

GATE_WORDS_DIR = os.path.join(HERE, u"gate_words")

def push_gate_words(block_name, findings, streak):
    """把入账闸的逐字拒因**落盘**再送一句话给写它的那条车道。

    为什么要这条腿：E 档的动作是「送门原话回车道」，可它原先只写进 HIT 等我来读——
    我一旦被上下文压缩腰斩，夜里那几个小时就没有人送，车道只能反复撞同一道门。
    正文刻意不带任何待证的数（连「几条」都不写），逐字拒因放进落盘文件，
    消息里只给路径：这样它既过中枢那道「数要带出处」的闸，也不用拿一次非零退出码当出处。
    """
    lane = block_name.split(u"_")[0]
    rid = lane if lane.count(u":") else (u"qoder:" + lane[:8])
    if not SEND["allow"]:
        say(u"自测挡板（SEND=off）：%s 的门原话不落盘也不投" % block_name)
        return u"blocked"
    try:
        if not os.path.isdir(GATE_WORDS_DIR):
            os.makedirs(GATE_WORDS_DIR)
        path = os.path.join(GATE_WORDS_DIR, u"gate_words_" + block_name + u".txt")
        io.open(path, "w", encoding="utf-8", newline=chr(10)).write(chr(10).join([
            u"read_at=" + time.strftime("%Y-%m-%d %H:%M:%S"),
            u"block=" + block_name,
            u"lane=" + rid,
            u"连续判定轮数=" + str(streak),
            u"门逐字输出：" + str(findings)]) + chr(10))
    except Exception as e:
        say(u"门原话落盘失败（%s: %s）⇒ 这一条不投，只记" % (type(e).__name__, str(e)[:80]))
        return u"failed"
    body = (u"值守哨兵→写这块的车道：你这枚块连两轮都会被入账闸拒，所以我没等你自己再撞一次，"
            u"把门的逐字输出落盘了，路径就在下面这行；改哪几格看它最准，我这边不改你写的字。"
            u"（连续轮数与条数不写在正文里——那是需要出处的读数，都在落盘文件里。）"
            + chr(10) + path)

    cl = closing_line()
    if not cl:
        say(u"收尾口令原件不可得 ⇒ 门原话这条不投（%s）：外发必须带逐字尾行" % block_name)
        return u"no_closing"
    body = body.rstrip() + NL_CHAR + cl + NL_CHAR
    cmd = [PYEXE, os.path.join(HUB, "bus.py"), "send", "--from", u"qoder:42d1a6fa",
           "--to", rid, u"--kind", u"note", u"--topic",
           u"gate-words:%s:%s" % (time.strftime("%m%d"), block_name), u"--body", body]
    try:
        q = subprocess.run(cmd, capture_output=True, cwd=HUB, timeout=90,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = (q.stdout or b"").decode("utf-8", "replace")
        if q.returncode == 0 and u'"id"' in out:
            say(u"门原话已送车道：%s → %s（落盘 %s）" % (block_name, rid, path))
            return u"sent"
        say(u"门原话没投出去：%s → %s（%s）" % (block_name, rid, out[:140]))
        return u"failed"
    except Exception as e:
        say(u"门原话投递异常（%s: %s）⇒ 不记进重账" % (type(e).__name__, str(e)[:80]))
        return u"failed"


BOLT_WORDS_DIR = os.path.join(HERE, u"bolt_words")

def bolt_reason_lines(block_name):
    """从分类尺那一拍的原文里取这枚块被第二道硬闸拒的逐字行。

    取不到返回 None，并且调用方要在文件里写「不可得」——绝不能拿「我没读到」当「没有拒因」。
    """
    t = _CENSUS_TAIL.get("text")
    if not t:
        return None
    ls = [l.strip() for l in t.splitlines() if block_name in l and u"第二道闸" in l]
    # 只给最近那一拍的判语：日志里同一枚块会有 27/39/51 分好几行，全塞进落盘文件会让车道问「哪一行算数」。
    # 分钟数以最后一行为准，其余行留在日志里可对账，不必复制给收件人。
    return ls[-1:] or None


def push_bolt_words(block_name, age_min, lines):
    """把「门绿却被第二道硬闸拒」的逐字判语落盘，再送一句不带数的话给写它的那条车道。

    为什么不能只靠 E 那条腿：E 用的是第一道尺，这类块在它眼里是 GREEN（10-05 17:1x 实测
    pending_red() 对 1ba48dbf_1624.md 报 GREEN，而写盘工同一刻仍 rc=9 拒收），
    所以车道侧这一格只能由 G 送到。正文沿用 push_gate_words 的规矩：数只进落盘文件。
    """
    lane = block_name.split(u"_")[0]
    rid = lane if lane.count(u":") else (u"qoder:" + lane[:8])
    if not SEND["allow"]:
        say(u"自测挡板（SEND=off）：%s 的硬闸原话不落盘也不投" % block_name)
        return u"blocked"
    path = os.path.join(BOLT_WORDS_DIR, u"bolt_words_" + block_name + u".txt")
    try:
        if not os.path.isdir(BOLT_WORDS_DIR):
            os.makedirs(BOLT_WORDS_DIR)
        head = [u"read_at=" + time.strftime("%Y-%m-%d %H:%M:%S"),
                u"block=" + block_name,
                u"lane=" + rid,
                u"已等分钟=" + str(int(age_min)),
                u"第二道硬闸逐字判语（分类尺那一拍原文）:"]
        body_lines = lines or [u"（分类尺那一拍没有这枚块的原文 ⇒ 拒因不可得；要复算请跑 live_checks/patrol/inbox_check.py，别按我这条日志的分钟数动手）"]
        io.open(path, "w", encoding="utf-8", newline=chr(10)).write(chr(10).join(head + body_lines) + chr(10))
    except Exception as e:
        say(u"硬闸原话落盘失败（%s: %s）⇒ 这一条不投，只记" % (type(e).__name__, str(e)[:80]))
        return u"failed"
    msg = (u"值守哨兵→写这块的车道：你这枚块过了第一道入账门，却被写盘工的第二道硬闸"
            u"（坐标可取回闸）拒着，已到我这一档的分钟数门槛，所以我没等你再撞一次。"
            u"逐字判语与已等分钟都在下面这个文件里，改哪一行看它最准——我不动你写的字。"
            + chr(10) + path)

    cl = closing_line()
    if not cl:
        say(u"收尾口令原件不可得 ⇒ 硬闸原话这条不投（%s）：外发必须带逐字尾行" % block_name)
        return u"no_closing"
    msg = msg.rstrip() + NL_CHAR + cl + NL_CHAR
    cmd = [PYEXE, os.path.join(HUB, "bus.py"), "send", "--from", SENTINEL_ID,
           "--to", rid, "--kind", "note", "--topic",
           u"bolt-words:%s:%s" % (time.strftime("%m%d"), block_name), "--body", msg]
    try:
        q = subprocess.run(cmd, capture_output=True, cwd=HUB, timeout=90,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = (q.stdout or b"").decode("utf-8", "replace")
        if q.returncode == 0 and u'"id"' in out:
            say(u"硬闸原话已送车道：%s → %s（落盘 %s）" % (block_name, rid, path))
            return u"sent"
        say(u"硬闸原话没投出去：%s → %s（%s）" % (block_name, rid, out[:140]))
        return u"failed"
    except Exception as e:
        say(u"硬闸原话投递异常（%s: %s）⇒ 不记进重账" % (type(e).__name__, str(e)[:80]))
        return u"failed"


def bolt_alarms(bolts, g_done, reds):
    """G 档判定 + 两条腿（车道原话 / 总线 band:G 报警）。返回真投出去的枚数。

    为什么单拎成函数：旧写法只 reds.append 且先记 g_done ⇒ 判红只活在 HIT 文件里，
    总线今天整天 band:G 为 0 枚（实测），发送失败当天还不再试。现在与 M/S 同一形制：
    红照记、两条腿都发、只有 alarm 真出去了才记进重账（投不上下一轮再试）。
    """
    fired = 0
    for nm, ag in bolts:
        key = time.strftime("%m%d") + u"|" + nm
        if ag < G_BOLT_MIN or g_done.get(key):
            continue
        reds.append((u"G 有块卡在第二道闸 {a} 分：{n} ⇒ 归写它的那条车道（id8={i}），"
                     u"我把硬闸的逐字判语送回那扇窗；号令者这一侧插不进去").format(
            a=int(ag), n=nm, i=nm[:8]))
        st_note = push_bolt_words(nm, ag, bolt_reason_lines(nm))
        state, topic = try_alarm(u"G", nm[:8], (
            u"G 档：有一枚块过了第一道入账门、却被写盘工的第二道硬闸（坐标可取回闸）拒着，"
            u"已到我这一档的分钟数门槛 ⇒ 这一格的动作不在号令者（他这一侧插不进去），"
            u"而在写它的那条车道：硬闸的逐字判语已落盘，具名块与路径见哨兵日志与本条证据输出。"
            u"已等分钟与 abort 条数不写进本条正文——那条命令在中枢重跑那一刻会漂。"
            + chr(10) + os.path.join(BOLT_WORDS_DIR, u"bolt_words_" + nm + u".txt")))
        if state == u"sent":
            g_done[key] = int(ag)
            fired += 1
        else:
            say(u"G 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（%s：%s）" % (topic, state))
        if st_note != u"sent":
            say(u"G 档车道腿没送到：%s（%s）⇒ 只记日志；alarm 若已出去，耐久副本仍在，下一轮不重复发同一枚" % (nm, st_note))
    return fired

_M_DEAD = {"n": 0, "oldest": 0, "who": []}

_M_ECHO = {"n": 0, "oldest": 0}
_M_RELAY = {"n": 0, "oldest": 0}   # 号令者两扇互递的复述件：单独数，不进「未取」分母
SENTINEL_ID = u"qoder:42d1a6fa"


def is_own_alarm(m):
    u"""哨兵自己投出去的那类报警（topic 以 band: 开头）。它不该再当「信被压着」的证据。"""
    return (str(m.get("from")) == SENTINEL_ID and str(m.get("kind")) == u"alarm"
            and str(m.get("topic", u"")).startswith(u"band:"))


def bus_unread_alarms():
    """M 档取数：BB 机账上「投出但到档仍未被取走」的条数与最老龄。

    为什么要有这一档：耐久副本不等于送达。昨夜我把 alarm 投进账、也记了「已报」，
    而收件人（包括我自己那一扇）几小时没读——**系统看起来在跑，实际断在最后一公里**。
    返回 (条数, 最老分钟, 收件人列表)；账读不到返回 None，整格写不可得。

    10-04 14:1x 扩了一档口径：旧尺只看 `kind==alarm`，于是「派单/交付」这两类更要命的积压
    根本不在视野里——实测那一刻 `6efab655` 压着 deliver 三枚（最老 774 分）、`file:nightwatch`
    压着 order 两枚（最老 2126 分），板与哨兵都写「未取 alarm 0 条」。阈值按实测定（90 分那一刀
    只切中 2 组共 5 条，不制造大面积红），alarm 仍用 M_UNREAD_MIN。幂等键**故意不改**：
    board 那侧的看门狗写的是同一枚键形，改键会让两边各投一条。
    """
    try:
        rows = []
        with io.open(os.path.join(M_BUS, "bus.jsonl"), encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        stt = json.load(io.open(os.path.join(M_BUS, "state.json"), encoding="utf-8"))
        acks = stt.get("acks", {})
        forgotten = set((stt.get("forgotten") or {}).keys())
    except Exception as e:
        say(u"M 档取不到账（%s: %s）" % (type(e).__name__, str(e)[:90]))
        return None
    now = time.time()
    thr = {u"alarm": M_UNREAD_MIN, u"deliver": M_UNREAD_KIND_MIN, u"order": M_UNREAD_KIND_MIN}
    pend = [(m, (now - float(m.get("ts", now))) / 60.0) for m in rows
            if m.get("kind") in thr and not (m.get("delivered_at") or acks.get(m.get("id")))]
    # 收件人已具名作废的信：单独数，不进「谁压着信没取」的排名——那类信永远取不走，
    # 留在分母里只会把「最老」这一格污染成假堵点（00:0x 实测：2 条挂 2716 分的死信
    # 让板整夜写「最老 2693 分」）。数照样落日志与 _M_DEAD，不藏。
    dead = [(m, a) for m, a in pend if str(m.get("to")) in forgotten]
    # 自己的回声单独数：00:2x 实测号令者未取 29 条里 14 条（48%）是哨兵自己投的 band: alarm，
    # 再拿它当证据就是"你没读我的报警"→"又多一条我的报警"的自激环。
    echo = [(m, a) for m, a in pend if is_own_alarm(m) and a >= thr[m.get("kind")]]
    # 号令者两扇互递的复述件单独数（副号令者·夜班 10-05 具名要求）：这类信只有他们两扇能拆，
    # 留在「谁压着信没取」的分子里就是"他回一条 ⇒ 我又欠一条"，越催越响，与自回声同一形状。
    # 不藏数：照样落 _M_RELAY 与日志，只是不拿去叫车道人读。
    relay = [(m, a) for m, a in pend if str(m.get("from")) in CMDR_IDS
             and str(m.get("to")) in CMDR_IDS and a >= thr[m.get("kind")]]
    aged = [(m, a) for m, a in pend if str(m.get("to")) not in forgotten
            and not is_own_alarm(m) and (m, a) not in relay and a >= thr[m.get("kind")]]
    aged.sort(key=lambda x: -x[1])
    _M_DEAD["n"] = len(dead)
    _M_DEAD["oldest"] = int(max([a for _m, a in dead])) if dead else 0
    _M_DEAD["who"] = sorted(set(str(m.get("to")) for m, _a in dead))
    if dead:
        say(u"M 档死信 %d 条不计入分母（收件人已作废：%s，最老 %d 分）"
            % (len(dead), u"、".join(_M_DEAD["who"]), _M_DEAD["oldest"]))
    _M_ECHO["n"] = len(echo)
    _M_ECHO["oldest"] = int(max([a for _m, a in echo])) if echo else 0
    if echo:
        say(u"M 档自回声 %d 条不计入分母（哨兵自己投的 band: alarm，最老 %d 分）"
            u"⇒ 这类要人读，靠板子与日志，不靠再投一条 alarm"
            % (len(echo), _M_ECHO["oldest"]))
    _M_RELAY["n"] = len(relay)
    _M_RELAY["oldest"] = int(max([a for _m, a in relay])) if relay else 0
    if relay:
        say(u"M 档复述件 %d 条不计入分母（号令者两扇互递，最老 %d 分）"
            u"⇒ 只由他们两扇自己拆，不拿它去叫车道读"
            % (len(relay), _M_RELAY["oldest"]))
    return (len(aged), int(aged[0][1]) if aged else 0,
            sorted(set(str(m.get("to")) for m, _a in aged)))

def unacked_stalled():
    """S 档取数：**已送达却没人拆**的件（按收件人分组）。返回 {收件人: (条数, 最老分钟)}；账读不到返回 None。

    为什么必须另开一档（10-05 16:4x 现读，同一趟读数、口径写在下面）：
    M 档判的是「投出但还没被取走」，而中枢有一条送达探针会**周期性补 `delivered_at`**
    （车道 8ac89982 的勘误件已具名说过这个形状）。于是件一旦被探针标过送达，就从 M 的视野里消失，
    可它其实没人 ack——实测这一拍：`deliver/order/ask/ruling` 龄过九十分钟且从未 ack 的
    **已送未拆一百一十四**条 vs **未送达**只剩个位数。
    也就是说 M 档对「交完活卡在验收口」这一类是**单向致盲**的，而那一类正是全队最疼的（H/Q 档只能看到停着，
    看不到是谁手里压着没拆）。S 档就补这一格：按收件人分组，具名最老龄。
    阈值不新造：沿用 M 档那条九十分（实测 10-04 定过一刀，只切中真积压）。
    """
    try:
        rows = []
        with io.open(os.path.join(M_BUS, "bus.jsonl"), encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        acks = json.load(io.open(os.path.join(M_BUS, "state.json"), encoding="utf-8")).get("acks", {})
    except Exception as e:
        say(u"S 档取不到账（%s: %s）" % (type(e).__name__, str(e)[:90]))
        return None
    now = time.time()
    kinds = (u"deliver", u"order", u"ask", u"ruling")
    out = {}
    for r in rows:
        to = str(r.get("to"))
        k = r.get("kind")
        if k not in kinds or to in (u"*", u"", u"None"):
            continue
        if not r.get("delivered_at") or acks.get(r.get("id")):
            continue                       # 未送达那一类归 M；已 ack 的算拆过
        age = (now - float(r.get("ts", now))) / 60.0
        if age < S_UNACKED_MIN:
            continue
        c, old = out.get(to, (0, 0.0))
        out[to] = (c + 1, max(old, age))
    return out


def s_focus(su):
    """从全量分组里挑出「卡全队」那几枚：号令者两扇与主人。车道自己没 ack 归第②格敲门。
    单独成函数是为了让自测能打真身，而不是我在测试里另抄一遍同一行判断（抄的那份不叫判据）。"""
    return dict((k, v) for k, v in (su or {}).items() if k in S_FOCUS)


def board_states():
    """向那块板取一次全量行（K/L 两档共用，别一拍敲两次）。取不到返回 None。

    10-04 14:0x 补一格：板把「在册」（6 小时内动过）与「收班」（6–12 小时）分成两个桶，
    旧代码只读 rows 那一个桶 ⇒ 车队一旦集体收班满 6 小时，K/L 就整队看不见，零读数会被读成
    「没人卡着」——单向致盲的尺也算缺陷。这里两桶都取：判定用的还是板里同一把尺，没有第二份。
    """
    try:
        import urllib.request
        op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        d = json.loads(op.open(K_BOARD_URL, timeout=30).read().decode("utf-8"))
        # 号令者 18:0x 裁语：K/L 的新取数口要在产出里带分母（在册 N ＋ 收班 M）——
        # 「0 扇」必须能读出它是「两桶都扫过、确实没有」，不是「只扫了一个桶」。
        _BOARD_DENOM["rows"] = len(d["rows"])
        _BOARD_DENOM["retired"] = len(d.get("retired") or [])
        return list(d["rows"]) + list(d.get("retired") or [])
    except Exception as e:
        say(u"板子没答话（K/L 档整格写不可得：%s: %s）" % (type(e).__name__, str(e)[:90]))
        return None

def board_l():
    """L 档：末条是平台错误回话（掉线）≥ L_DROP_MIN 分的窗口，外加「还没接 BB 机」的名单。
    掉线这一类昨夜 22:2x 一次掐了七扇，而当时**没有任何一档报出来**（mtime 在动、尾条不是 tool_use、
    也没写等点单），所以整夜看不见＝这一档存在的唯一理由。未接名单只报不叫：那是派单方贴一行的事。"""
    rows = board_states()
    if rows is None:
        return None, None
    drop = [(r["id8"], float(r["idle_min"]), int(r.get("unread") or 0)) for r in rows
            if r.get("state") == u"dropped" and float(r["idle_min"]) >= L_DROP_MIN
            and r["id8"] not in J_EXCLUDE]
    # 10-06 17:4x 修：retired 桶里"久静不见"那批行**不带 idle_min/in_hub**（板子 17:07 加的分支），
    # 老写法 r["idle_min"] 直接 KeyError ⇒ 哨兵崩、被续跑器带回来、再崩（崩溃循环）。
    # 取不到就跳过这两枚，并按"不可判"计数，不崩、不编数。
    unreg = []
    unknown = []          # 缺字段 ⇒ 不可判。不崩，也不拿默认值冒充读数，
                          # 但**不许静默消失**——记下来报出去（同类：五·三十那记教训）
    for r in rows:
        if r.get("in_hub"):
            continue
        try:
            unreg.append((r["id8"], float(r["idle_min"])))
        except (KeyError, TypeError, ValueError):
            unknown.append(str(r.get("id8") or r.get("id") or "?"))
    if unknown:
        say(u"L 档：%d 枚行缺 idle_min（板上契约变了？）⇒ 记不可判、不计未接：%s"
            % (len(unknown), u"、".join(unknown)))
    return drop, unreg, len(unknown)

def board_k():
    """K 档取数：向那块人看的板要「等模型回包 ≥ K_MODEL_MIN 分」的窗口。
    为什么不在这里再写一把尺：板子已经持有『尾节点形状』那把尺（末条 tool_result 而后面没有
    自己的下一句＝等模型），哨兵当消费者；两处各写一份迟早分叉——今天 KW 词表分叉就咬过一次。
    取不到就返回 None，K 档整格写「不可得」，绝不把读不到当绿。
    10-04 14:0x：这里原本自己 urllib 读了一遍 d["rows"]（等于第二把尺 + 第二个取数口），
    现在改走 board_states()——它含收班名单，车队整队收班满 6 小时后 K 档不再瞎。"""
    rows = board_states()
    if rows is None:
        return None
    return [(r["id8"], float(r["idle_min"])) for r in rows
            if r.get("live") == u"awaiting_model" and float(r["idle_min"]) >= K_MODEL_MIN
            and r["id8"] not in J_EXCLUDE]

ALARM_BACKOFF_MIN = int(os.environ.get("ALARM_BACKOFF_MIN", "3"))
ALARM_TO = u"qoder:494abfd7"          # 与 hub_alarm 的 --to 写死值同源，改一处记得改两处
_M_BLOCK = {"n": 0, "band": u"", "to": u""}


def alarm_backoff(band, to_addr, rows=None, acks=None, now=None, unacked_min=45.0):
    u"""这一档该不该停投：收件人名下同档的"我自己投出且没被取走"已达上限 ⇒ 停。

    返回 (bool, 说明)。只认「自己投的、同档、超过未取阈值、至今没被取走」这四样同时成立的那批；
    别人投的、他已取的、别的档，都不计入——否则这一格会变成"他收件框里有多少条"那种无边界的账。
    """
    try:
        now = now if now is not None else time.time()
        if rows is None:
            rows = []
            with io.open(os.path.join(M_BUS, "bus.jsonl"), encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        if acks is None:
            acks = json.load(io.open(os.path.join(M_BUS, "state.json"),
                                    encoding="utf-8")).get("acks", {})
        band_s = u"band:%s" % band
        n = 0
        oldest = 0.0
        for m in rows:
            if str(m.get("kind")) != u"alarm":
                continue
            if str(m.get("to")) != to_addr:
                continue
            if not is_own_alarm(m):
                continue
            if not str(m.get("topic") or u"").startswith(band_s + u":"):
                continue
            if m.get("delivered_at") or acks.get(m.get("id")):
                continue
            age = (now - float(m.get("ts", now))) / 60.0
            if age < unacked_min:
                continue
            n += 1
            oldest = max(oldest, age)
        _M_BLOCK["n"], _M_BLOCK["band"], _M_BLOCK["to"] = n, band_s, to_addr
        if n >= ALARM_BACKOFF_MIN:
            return True, (u"%s 收件人 %s 名下已欠 %d 枚未取（最老 %d 分）⇒ 本拍停投；"
                          u"事实见板子 M 档那一格与日志，不往不读的收件框里加码"
                          % (band_s, to_addr, n, int(oldest)))
        return False, u""
    except Exception as e:
        # 闸门自己读不动账时**不许当成"可以投"**：宁可少投也不制造第二个自激环；
        # 也不抛出去掀掉这一轮判定。
        say(u"停投闸读不到账（%s: %s）⇒ 这一拍按'暂不投'处理" % (type(e).__name__, str(e)[:90]))
        return True, u"闸读不到账，本拍暂不投"


def try_alarm(band, id8, msg):
    """alarm 腿的任何异常都不许掀掉这一轮判定——红该红还是该红，只是这枚没投出去。
    返回 (state, topic)；调用方**只有在 state=="sent" 时才准记进重账**（06:55 那枚就是记了账却没投出去）。"""
    # alarm 只有一个收件人：hub_alarm 的 send 命令把 --to 写死成 qoder:494abfd7，
    # 所以"这条通道堵没堵"就等于"号令者名下我投的同档 alarm 欠没欠"。
    # 达上限就停投（事实落日志与板子那一格），别往不读的收件框里加第二遍——
    # 16:3x 现读：号令者名下 108 枚 alarm、31 枚他没取走，同一件被跨天重投了 25–39 次。
    blocked, why = alarm_backoff(band, ALARM_TO)
    if blocked:
        say(u"停投：%s" % why)
        return ("blocked", u"band:%s" % band)
    try:
        return hub_alarm(band, id8, msg)
    except Exception as e:
        say(u"BB 机 alarm 抛错（band:%s:…:%s）：%s: %s" % (band, id8, type(e).__name__, str(e)[:120]))
        return ("error", u"band:%s" % band)

def why_run_once():
    """本轮起一次 `_why_stopped_r1.py 25` 存进 _WHY；I/J 两档都从这份缓存取，绝不扫第二遍流水。"""
    _WHY["text"] = None
    _WHY["rc"] = None
    out, rc = run("_why_stopped_r1.py", "25")
    if rc != 0:
        return False
    _WHY["text"] = out
    _WHY["rc"] = rc
    return True

def idle_ids(mins, exclude=J_EXCLUDE):
    """只看 mtime 筛出静了 >= mins 的窗口（不读正文，所以每拍都跑得起）。

    这一筛专为补 J 档的洞：J 若只跟着「整队在写 <= 6」走，那** lone 一扇断在半路、别人都在忙**
    这种最常见的形状就永远看不见——整队安静本来就归 C 档管。静默筛独立跑，成本是十几次 os.stat。
    """
    out = []
    now = time.time()
    try:
        names = os.listdir(PROJ_DIR)
    except Exception:
        return out
    for nm in names:
        if not nm.endswith(".jsonl"):
            continue
        id8 = nm[:8]
        if id8 in exclude:
            continue
        try:
            mt = os.path.getmtime(os.path.join(PROJ_DIR, nm))
        except Exception:
            continue
        if (now - mt) / 60.0 >= mins:
            out.append((id8, int((now - mt) / 60.0)))
    return out

def _why_age(out, id8):
    for mm in re.finditer(u"^\\s{2}([0-9a-f]{8})\\s+\\S+\\s+静\\s+(\\d+) 分", out, re.M):
        if mm.group(1) == id8:
            return int(mm.group(2))
    return -1

def boot_epoch():
    """开机时刻（本地 epoch）——用来把「重启腰斩」那种死尾剔出去。拿不到就返回 None，J 档整格报不可得。"""
    try:
        import ctypes
        ms = ctypes.windll.kernel32.GetTickCount64()
        return time.time() - ms / 1000.0
    except Exception:
        return None

def mid_stalled():
    """谁「断在半路」（尾条是没回音的 tool_use）——从 I 档那次子进程输出里取，返回 [(id8, 静默分钟)]；不可得返回 None。

    这格值不值得开，是量过的不是猜的：`_stall_predicate_audit_r1.py` 在 24 小时真流水上数到死尾 5 次，
    其中 3 次 60 分钟内没自己复工（误报率 40%）——所以门槛取 40 分、一天一扇只报一次，且跳过号令者与我
    （我们的死尾有良性成因：重启腰斩、上下文压缩）。
    """
    out = _WHY.get("text")
    if out is None:
        return None
    m = re.search(u"该敲车道本人（卡闸/断在半路）：(.*)$", out, re.M)
    if not m:
        return None
    line = m.group(1).strip()
    if line == u"无":
        return []
    ids = [x.strip() for x in line.split(u"、")
           if re.match(r"^[0-9a-f]{8}$", x.strip()) and x.strip() not in J_EXCLUDE]
    return [(i, _why_age(out, i)) for i in ids]

def pass_once(zero_streak, d_streak=0, e_hist=None, b_streak=0, g_done=None):
    """跑一轮判定。返回 (红因列表, 新的连 0 拍数, 读数小结)。"""
    g_done = {} if g_done is None else g_done
    reds = []
    ua, rc_a = run("_unclaimed_orders_r1.py", "3")
    m = re.search(u"无人接的单 (\\d+) 张", ua)
    n_un = int(m.group(1)) if m else -1
    if n_un == -1:
        reds.append("A 尺取不到数（rc=%s）——不能当绿" % rc_a)
    elif n_un > 0:
        reds.append("A 无人接 %d 张" % n_un)
    rw, rc_w = run("_restart_watch_r1.py")
    mw = re.search(u"在场会话（最近 [\\d.]+ 分钟动过）(\\d+) 条｜被叫醒过 (\\d+) 条｜叫醒后已回话 (\\d+) 条｜"
                   u"叫醒后仍未回话 (\\d+) 条｜停在额度字样且没人接 (\\d+) 条", rw)
    if not mw:
        reds.append("B 尺取不到数（rc=%s）——不能当绿" % rc_w)
        pres = pending = nq = -1
    else:
        pres, _wakes, _replies, pending, nq = [int(x) for x in mw.groups()]
        # B 与 E 同形制：连两轮还在才算事。23:15 那一拍就是被单轮 1 条顶退的（那时有 15 条在写、根本不是停摆）。
        if pending > 0 or nq > 0:
            b_streak += 1
            if b_streak >= B_STREAK_EXIT:
                reds.append("B 连 %d 轮有车道没回声（未回 %d、停在额度且没人接 %d）⇒ 叫醒归号令者，该把这一格报给他" % (
                    b_streak, pending, nq))
        else:
            b_streak = 0
    qr, rc_q = run("_quota_roster_r1.py")
    mq = re.search(u"名册：停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", qr)
    if not mq:
        reds.append("C 尺取不到数（rc=%s）——不能当绿" % rc_q)
        writing = -1
    else:
        writing = int(mq.group(2))
        zero_streak = zero_streak + 1 if writing == 0 else 0
        # C 从「只报」改成「能叫一次」：19:29 那拍实测全队在 0（19:14 已经 0 一拍），旧版只会往日志里记一行，
        # 我根本不会醒——后来队活了是号令者自己派的（19:32:44 他自己往车道发消息的回执），属于运气不是覆盖。
        # 但也不能每拍都叫醒我：同一段停摆只叫一次，恢复在写之后清账，下一次停摆是新的 episode。
        ck = u"C|" + time.strftime("%m%d")
        if writing > 0:
            g_done.pop(ck, None)
        elif zero_streak >= 2 and g_done.get(ck) != u"fired":
            g_done[ck] = u"fired"
            reds.append(u"C 整队停摆：连续 %d 拍在写 0 条 ⇒ 我把『谁停了、停多久、缺的是活还是裁语』报到号令者面前"
                        u"（叫醒工人归他，传话归我）" % zero_streak)
        elif zero_streak >= 2:
            reds.append(u"C·续 停摆仍在继续（连 %d 拍；本段已叫过一次，不重复叫醒）" % zero_streak)
    # D：互等停摆——权威尖静止 >= D_TIP_MIN 分 且 未落地队列 >= D_QUEUE_MIN 枚（车道在等他裁/落，他在等车道交）
    tage = tip_age_min()
    qn = queue_depth()
    if tage < 0 or qn < 0:
        d_hit = False
        dtxt = "尖龄 %s / 队列 %s（不可得，不计红）" % (tage, qn)
    else:
        d_hit = (tage >= D_TIP_MIN and qn >= D_QUEUE_MIN)
        dtxt = "尖 %d 分没动、队列 %d 枚" % (int(tage), qn)
    if d_hit:
        d_streak += 1
    else:
        d_streak = 0
    if d_streak >= D_STREAK_EXIT:
        reds.append("D 互等停摆连 %d 拍：%s ⇒ 落地/裁语那一格长期没人推，需人动" % (d_streak, dtxt))
    # H：车道在等落地，而落地这一格没人推——尖静止很久但队列不大时，D（要队列>=8）不会响，
    # 15:00-16:00 那次互等就是这个形状：他等车道交、车道等他落。所以再加一枚不看队列大小的兜底。
    if tage >= H_TIP_MIN and qn >= H_QUEUE_MIN:
        reds.append("H 尖静止 %d 分（>=%d）且未落地队列 %d 枚（>=%d）⇒ 有车道卡在等落地，落地只能号令者做，该敲他窗" % (
            int(tage), H_TIP_MIN, qn, H_QUEUE_MIN))
    # 分类尺那一拍先取（E/F/G 三格共用同一份读数，也少一次日志读）
    ndoor, old, nrej, nbolt, note, bolts = door_backlog()
    bolt_names = set(nm for nm, _ag in bolts)
    # E：收件口里那几枚「写完但会被入账闸拒」的块（龄 >= 5 分才验，更短说明还在写）
    erows, eerr = pending_red()
    bad = [x for x in erows if x[1] == "RED"]
    unk = [x for x in erows if x[1] == "读数不全"]
    # E 这把尺只跑第一道闸，所以「门绿却被硬闸拒」在它眼里一律 GREEN——单向致盲必须点名，不能当零：
    # 10-05 17:1x 实测 pending_red() 给 1ba48dbf_1624.md 报 GREEN，同一枚块被写盘工连拒一个钟头。
    blind = [x for x in erows if x[1] == "GREEN" and x[0] in bolt_names]
    # E 的早退门槛：同一枚块**连续两轮**都判会被拒，才叫我。
    # 16:30 那一轮就是被单轮判红拖停的：`5a53846b_1622.md` 当时确实有 1 条 NUMBER_WITHOUT_COORDINATE，
    # 但车道 16:34:22 自己改完重交、门 16:34:44 就收进去了——我复跑那一版是 GREEN/findings 0。
    # 单轮红就退会让整面哨兵停摆（那一次停了 34 分钟没人盯），所以只有「没人修」的红才值得叫醒我。
    prev = dict(e_hist or {})
    e_hist = {}
    for n, _v, _f in bad:
        e_hist[n] = prev.get(n, 0) + 1
    if eerr:
        reds.append("E 根目录读不到（%s）——不能当绿" % eerr)
    else:
        for n, c in sorted(e_hist.items()):
            if c >= E_STREAK_EXIT:
                f_ = [f for m, _v, f in bad if m == n]
                reds.append("E 同一枚块连 %d 轮都会被入账闸拒：%s（findings %s 条）⇒ 车道没改、门会拒，该把门的原话送回写它的那条车道" % (
                    c, n, (f_[0] if f_ else "?")))
                # 不等我醒：这格的动作本来就是「送门原话回车道」，那就把它送出去。
                # 一枚块一天只送一次（键带日期与块名），避免每拍刷同一句话。
                gkey = time.strftime("%m%d") + u"|Ewords|" + n
                if not g_done.get(gkey):
                    if push_gate_words(n, (f_[0] if f_ else u"?"), c) == u"sent":
                        g_done[gkey] = int(c)
    etxt = ("待插验 {} 枚（红 {}、其中连两轮 {}、不可判 {}）｜".format(
        len(erows), len(bad), len([c for c in e_hist.values() if c >= 2]), len(unk))
        + (u"闸拒不可得（分类尺本轮未分类）" if nbolt < 0
           else u"门绿却硬闸拒 {} 枚（E 看不见，归 G 档）".format(len(blind))))
    # F：门停了——待插 >= 2 枚且最老 >= 20 分（代插只能号令者跑，所以这条叫醒的是我）
    if ndoor < 0:
        reds.append("F 收件口读不到（%s）——不能当绿" % note)
        ftxt = "门：不可得"
    else:
        bold = u"｜闸拒最老 %d 分" % int(max(a for _n, a in bolts)) if bolts else u""
        ftxt = "门可插 %d 枚（最老 %d 分）｜门拒 %d｜闸拒 %d%s｜%s" % (
            ndoor, int(old), nrej, nbolt, bold, note)
        # 两枚以上超 20 分，或一枚以上超两倍 SLA（40 分）都算门停——后者是 02:24 那拍的教训：
        # 计数口径把「刚落口 3 分钟」的也算进待插，于是一枚车道侧被闸拒的旧块就能把 F 顶红。
        if (ndoor >= 2 and old >= F_DOOR_MIN) or (ndoor >= 1 and old >= 2 * F_DOOR_MIN):
            reds.append("F 门停了：可代插 %d 枚、最老 %d 分（另有门拒 %d、闸拒 %d 不归他）"
                        "⇒ 只能号令者跑代插，该敲他窗" % (ndoor, int(old), max(nrej, 0), max(nbolt, 0)))
        # G：把「门绿但被第二道闸拒」那一格单独钉住。F 修好之后这类块不再进 F 的分子（它们本来就不该敲号令者），
        # 若不加这一格，一条车道交的块可以在闸拒状态上躺一整夜而没人送原话回去——那就是我 02:24 亲手挖的坑。
        # 判定与投递都在 bolt_alarms 里：这一格自测要能单独喂一份合成分类读数进去（见 _g_band_alarm_selftest_r1.py）
        bolt_alarms(bolts, g_done, reds)
    # I：车道尾条明写「等点单/等裁」且超龄——裁语只能号令者给，所以这一格的动作是敲他窗（不是敲那扇车道）。
    # 为什么整队都在动时不读尾条：14 份流水每拍扫一遍没有意义，等点单只在「没人干活」时才是拦路的那一格。
    itxt = u"等点单：未读（在写 %d > %d）" % (writing, I_GATE_WRITING)
    idle8 = idle_ids(J_STALL_MIN)
    i_gate = 0 <= writing <= I_GATE_WRITING
    j_gate = bool(idle8)
    ran = why_run_once() if (i_gate or j_gate) else False
    i_ran = False
    if i_gate and ran:
        i_ran = True
        w = waiting_ruling()
        if w is None:
            reds.append(u"I 尺取不到数（_why_stopped_r1.py 没回话）——不能当绿")
            itxt = u"等点单：不可得"
        else:
            ages_ok = [a for _i, a in w if a >= 0]
            itxt = u"等点单 %d 扇（最老 %d 分）" % (len(w), int(max(ages_ok)) if ages_ok else 0)
            for id8, ag in w:
                key = time.strftime("%m%d") + u"|I|" + id8
                if ag < I_WAIT_MIN or g_done.get(key):
                    continue
                # 两处今天真咬到人，都在这儿改：
                # ① 分钟数不进 alarm 正文——中枢要求正文每个数都出现在 evidence 输出里，而那条命令是在
                #    发送那一刻重跑的，同一格的分钟数会漂（06:55 那枚就是这么被拒的：正文 53、输出已 54）。
                # ② 投递失败不许记进重账——旧写法先记 key 再投，投不上就当天再也不试，
                #    等于「看着报过、其实没人收到」，那是最坏的一种静默。
                msg = (u"I 车道 %s 明写等号令者点单，已过我这一档的门槛 ⇒ 裁语只能他给，该敲他窗；"
                       u"我不敲这扇车道（它不是停在手活上）。分钟数以哨兵日志与证据输出为准，"
                       u"不写进本条正文：这条腿的数会在中枢重跑那一刻漂掉。" % id8)
                reds.append(msg + u"（实测 %d 分）" % int(ag))
                state, topic = try_alarm("I", id8, msg)
                if state == "sent":
                    g_done[key] = int(ag)
                else:
                    say(u"I 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（%s：%s）" % (topic, state))
    # J：车道断在半路（尾条是没回音的 tool_use）——重启腰斩那种不算，所以要求死尾发生在本次开机之后
    jtxt = u"断在半路：未读（无静 >= %d 分的窗口）" % int(J_STALL_MIN)
    if j_gate and ran:
        s = mid_stalled()
        if s is None:
            reds.append(u"J 尺取不到数（与 I 同一次子进程，见 _why_stopped_r1.py 的回话）——不能当绿")
            jtxt = u"断在半路：不可得"
        else:
            bt = boot_epoch()
            aged = [a for _i, a in s if a >= 0]
            jtxt = u"断在半路 %d 扇（最老 %d 分）" % (len(s), int(max(aged)) if aged else 0)
            for id8, ag in s:
                key = time.strftime("%m%d") + u"|J|" + id8
                if ag < J_STALL_MIN or g_done.get(key):
                    continue
                mt = time.time() - ag * 60.0
                if bt is not None and mt <= bt:
                    jtxt += u"｜%s 的死尾早于本次开机，剔掉" % id8
                    continue
                # 成因**从分类器原文取**（20:39 装）。原来这句手写的
                # 「断在半路（尾条是没回音的 tool_use）」会在分类器只判「卡闸/等裁语」时
                # 凭空造出"断在半路"——20:35:57 对 1d64acf5 就是这样假红了一次。
                _why = why_stopped_line(id8)
                if _why is None:
                    _cause = (u"分类器判词读不到 ⇒ **成因不可判**（不回退到手写那句："
                              u"那正是 20:35 假红的路）")
                elif u"断在半路" in _why:
                    _cause = u"断在半路（尾条是没回音的 tool_use）⇒ 它不会自己回来读账本"
                else:
                    _cause = (u"分类器判：**%s**（**非断在半路**）⇒ 该敲的是号令者点验收，"
                              u"不是叫醒这一扇" % _why)
                msg = (u"J 车道 %s %s；该敲号令者把它叫回这一手；"
                       u"叫醒与派单仍归他，我只把话送到。"
                       u"分钟数同 I 档：只进日志与证据输出，不进本条正文。" % (id8, _cause))
                reds.append(msg + u"（实测 %d 分）" % int(ag))
                state, topic = try_alarm("J", id8, msg)
                if state == "sent":
                    g_done[key] = int(ag)
                else:
                    say(u"J 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（%s：%s）" % (topic, state))
    # N：盘水位（C 才是车队写任务流水的那块盘）。**故意不进 actionable**——
    # 要清的是别人应用的数据，我动不了；按「只有本班动得了的红才早退」这条，只记不退场。
    cfree = disk_free_gb(u"C:/")
    dfree = disk_free_gb(u"D:/")
    if cfree is None:
        reds.append(u"N 尺读不到 C 盘余量（GetDiskFreeSpaceExW 没答话）——不能当绿")
        say(u"N 盘水位：不可得")
    else:
        band = u"严重" if cfree < DISK_CRIT_GB else (u"预警" if cfree < DISK_WARN_GB else u"绿")
        say(u"N 盘水位：C 剩 %.2f GiB｜D 剩 %s｜档=%s" % (
            cfree, (u"%.2f GiB" % dfree) if dfree is not None else u"不可得", band))
        if band != u"绿":
            key = time.strftime("%m%d") + u"|N|disk-" + band
            if not g_done.get(key):
                nmsg = (u"N 盘水位 %s：C 只剩这些，而各扇任务流水都写在 C 上 ⇒ 清零就是全线停摆（不是尺瞎）。"
                        u"可回收分档有现成取数口 live_checks/patrol/_c_headroom_r1.py（只数不删，删哪一档要人点）；"
                        u"这一格的动作归号令者或主人，我不自便。" % band)
                reds.append(nmsg)
                # 报警腿照旧：投出去才算报过，投不出去下一轮再试（耐久副本≠送达）
                state, topic = try_alarm("N", u"disk", nmsg)
                if state == u"sent":
                    g_done[key] = int(cfree * 100)
                else:
                    say(u"N 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（%s：%s）" % (topic, state))

    # K：等模型回包卡住（结果早回来了、下一句没来）——I/J 都读 mtime，这一类以前整夜看不见
    ktxt = u"等模型：不可得"
    k = board_k()
    if k is None:
        reds.append(u"K 尺取不到数（那块人看的板没答话）——不能当绿")
    else:
        ktxt = u"等模型 %d 扇（最老 %d 分）%s" % (
            len(k), int(max([a for _i, a in k])) if k else 0,
            (u"[分母 在册 %d＋收班 %d]" % (_BOARD_DENOM["rows"], _BOARD_DENOM["retired"])
             if _BOARD_DENOM["rows"] >= 0 else u"[分母 没取到]"))
        for id8, ag in k:
            key = time.strftime("%m%d") + u"|K|" + id8
            if ag < K_MODEL_MIN or g_done.get(key):
                continue
            msg = (u"K 车道 %s 那一轮的工包结果已回来、模型没出下一句 ⇒ 那一轮不会自己回来，"
                   u"要么重发要么换模型；分钟数以看板与证据输出为准，不写进本条正文（同 I 档的形制）。" % id8)
            reds.append(msg + u"（实测 %d 分）" % int(ag))
            state, topic = try_alarm("K", id8, msg)
            if state == "sent":
                g_done[key] = int(ag)
            else:
                say(u"K 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（%s：%s）" % (topic, state))
    # L：掉线待重发（末条是平台错误回话）+ 未接 BB 机名单
    ltxt = u"掉线：不可得"
    drop, unreg, unk_l = board_l()
    if drop is None:
        reds.append(u"L 尺取不到数（那块板没答话）——不能当绿")
    else:
        ltxt = u"掉线 %d 扇（最老 %d 分）｜未接 %d 扇｜%s" % (
            len(drop), int(max([a for _i, a, _u in drop])) if drop else 0, len(unreg or []),
            (u"分母 在册 %d＋收班 %d" % (_BOARD_DENOM["rows"], _BOARD_DENOM["retired"])
             if _BOARD_DENOM["rows"] >= 0 else u"分母 没取到"))
        for id8, ag, un in drop:
            key = time.strftime("%m%d") + u"|L|" + id8
            if ag < L_DROP_MIN or g_done.get(key):
                continue
            msg = (u"L 车道 %s 末条是平台错误回话（Unable to connect to the service…）⇒ 那一轮被链路掐断，"
                   u"不会自己回来，要重发那一轮；敲它没用。未取条数与分钟数以看板与证据输出为准，"
                   u"不写进本条正文（同 I/K 档形制）。" % id8)
            reds.append(msg + u"（实测 %d 分）" % int(ag))
            state, topic = try_alarm("L", id8, msg)
            if state == "sent":
                g_done[key] = int(ag)
            else:
                say(u"L 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（%s：%s）" % (topic, state))
        if unk_l:
            say(u"L 档那一格有 %d 枚不可判（不并进'未接 BB 机'，也不当零）" % unk_l)
        if unreg:
            reds.append(u"L 未接 BB 机 %d 扇：%s ⇒ 它们收不到 order/ack，点名只能靠敲窗口；"
                        u"贴一行 join 即可（认领＋读收件框一次做完）"
                        % (len(unreg), u"、".join(i for i, _a in unreg)))
    # M：alarm 投出去到档仍没人取 ⇒ 传话断在最后一公里，动作是"我去读/去敲门"，不是敲收件人
    mtxt = u"未取 alarm：不可得"
    mu = bus_unread_alarms()
    if mu is None:
        reds.append(u"M 尺取不到账（BB 机账读不到）——不能当绿")
    else:
        n, oldest, tos = mu
        mtxt = u"未取(alarm/deliver/order) %d 条（最老 %d 分）" % (n, oldest)
        # 幂等要包住 reds.append，不能只包住 alarm：这一档的红是「没人去读」，在有人读之前每拍都在，
        # 若每拍都 append 就会每拍早退交人——16:30 那次单轮红让整面哨兵停摆 34 分钟，同一个坑不能踩两遍。
        key = time.strftime("%m%d") + u"|M|unread-alarms"
        if n and not g_done.get(key):
            dead = sorted(set(t for t in tos if u":" in t and not t.startswith(u"qoder:")))
            reds.append(u"M BB 机上有 %d 条 alarm/deliver/order 到档仍未被取（最老 %d 分，收件人：%s%s）"
                        u" ⇒ 耐久副本不等于送达；这一档的动作在我：先读自己收件框，再替收件方敲门"
                        % (n, oldest, u"、".join(tos),
                           u"；其中不可寻址的死地址：%s（敲不动，只能由号令者裁定作废或改址）"
                           % u"、".join(dead) if dead else u""))
            state, topic = try_alarm(u"M", u"bus", u"M 档：账上有 alarm 到档未被取，具名收件人与条数见本拍日志与证据输出。")
            if state == "sent":
                g_done[key] = oldest
            else:
                say(u"M 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（%s：%s）" % (topic, state))
    # S：已送达却没人拆 ⇒ 这是「交完活卡在验收口」的那一类；M 看不见它（送达探针会补 delivered_at）
    stxt = u"已送未拆：不可得"
    su = unacked_stalled()
    if su is None:
        reds.append(u"S 尺取不到账（BB 机账读不到）——不能当绿")
    else:
        focus = s_focus(su)
        tot = sum(v[0] for v in su.values())
        ftot = sum(v[0] for v in focus.values())
        stxt = u"已送未拆 %d 条（其中 %s 名下 %d 条）" % (tot, u"号令者两扇与主人", ftot)
        if focus and ftot:
            # 「今天已经报过」不等于「干净」：这一句要给下一班看见真实状态，别把去重读成没事。
            stxt = u"已送未拆 %d 条（其中 %s 名下 %d 条，最老 %d 分｜今天已报过一次，仍在压着）" % (
                tot, u"号令者两扇与主人", ftot, int(max(v[1] for v in focus.values())))
        key = time.strftime("%m%d") + u"|S|unacked"
        if focus and not g_done.get(key):
            old = max([v[1] for v in focus.values()])
            reds.append(u"S 有 %d 条已送达却没人拆（收件人：%s，最老 %d 分）"
                        u" ⇒ 车道交完活停着的因在这一格：件送到了但没被拆，不是又投丢了"
                        % (ftot, u"、".join(sorted(focus)), old))
            state, topic = try_alarm(u"S", u"unacked",
                                     u"S 档：账上有已送达却没人拆的交付与派单，具名收件人、条数与最老龄见本拍日志与证据输出。")
            if state == "sent":
                g_done[key] = old
            else:
                say(u"S 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（%s：%s）" % (topic, state))
        elif focus:
            # 三态里最容易被写歪的一态：焦点名下**确实还压着**，只是今天已经报过一次。
            # 旧写法直接落到下面那条"都干净"的措辞，等于把去重读成没事——下一班会照着这句判断包工头不欠件。
            say(u"S 档读数：号令者两扇与主人 名下仍压着 %d 条（最老 %d 分）⇒ 今天已报过一次，"
                u"这一拍不重复投；这不是『干净』，分组：%s"
                % (ftot, int(max(v[1] for v in focus.values())),
                   u"、".join(u"%s×%d" % (k, v[0]) for k, v in sorted(focus.items()))))
        elif su:
            # 只有车道手里压着：照样把分组打进日志，不藏数，只是不报警（那一类归第②格敲门）
            say(u"S 档读数：全队已送未拆 %d 条，号令者两扇与主人都干净 ⇒ 不报，分组：%s"
                % (tot, u"、".join(u"%s×%d" % (k, v[0]) for k, v in sorted(su.items()))))
    summary = "无人接 %d｜在场 %d 未回 %d 额度无人接 %d｜在写 %d（连 0 拍 %d）｜%s｜%s｜%s｜%s｜%s｜%s｜%s｜%s%s" % (
        n_un, pres, pending, nq, writing, zero_streak, dtxt, etxt, ftxt, itxt, jtxt, ktxt, ltxt, mtxt,
        ("（D 连红 %d）" % d_streak) if (d_hit and d_streak < D_STREAK_EXIT) else "")
    summary = summary + u"｜" + stxt
    return reds, zero_streak, summary, d_streak, e_hist, b_streak, g_done

def main():
    total_min = int(sys.argv[1]) if len(sys.argv) > 1 else 480
    period = int(sys.argv[2]) if len(sys.argv) > 2 else 900
    deadline = time.time() + total_min * 60
    say("哨兵起来：总 %d 分钟、每 %d 秒一轮；判据 A 无人接>0｜B 未回>0 或 额度且没人接>0｜C 连续两拍在写=0｜"
        "D 尖静止>=%d 分且队列>=%d 枚连 %d 拍｜I 在写<=%d 时读尾条、等点单>=%d 分一扇只报一次｜"
        "J 同一把尺取『断在半路』>=%d 分（死尾早于本次开机的剔掉）一扇只报一次｜"
        "K 向那块人看的板取『等模型回包』>=%d 分一扇只报一次（板子没答就整格写不可得，不当绿）｜"
        "L 同一枚板取『末条是平台错误回话』>=%d 分一扇只报一次，另把未接 BB 机的名单每拍报出来｜"
        "M BB 机账上 alarm 投出>=%d 分仍未被取 ⇒ 耐久副本≠送达，动作在我先读自己收件框"
        u"｜P 代插腿插了块却拿不到镜像回执（远端不可证）⇒ 这一档由 _inbox_applier_r2 直接投，本腿登记口径并在板子上算进未取"
        "｜Q 谁交完活就停着（跑 _bb_cmdr_acceptance_queue_r1 那份算法，不重写第二把尺）；取不到写不可得"
        % (total_min, period, D_TIP_MIN, D_QUEUE_MIN, D_STREAK_EXIT, I_GATE_WRITING, I_WAIT_MIN,
           J_STALL_MIN, K_MODEL_MIN, L_DROP_MIN, M_UNREAD_MIN))
    zero_streak = 0
    d_streak = 0
    e_hist = {}
    g_done = load_gdone()
    b_streak = 0
    rounds = 0
    if g_done:
        say("G 档已报过的块（从 %s 读回，跨重启不重复敲门）：%s" % (
            os.path.basename(GDONE), u"、".join(sorted(g_done))))
    while time.time() < deadline:
        rounds += 1
        reds, zero_streak, summary, d_streak, e_hist, b_streak, g_done = pass_once(
            zero_streak, d_streak, e_hist, b_streak, g_done)
        save_gdone(g_done)
        # O 档挂在主循环而不是 pass_once 的返回值链上：它只加一条红因，
        # 且 O 不在 actionable 的 A/E/F/G 里 ⇒ 不会因为"有人没接入"就早退叫人。
        gap = adoption_gap()
        if gap:
            reds.append(gap)
            summary = summary + u"｜" + gap
        acc = acceptance_stalled()
        if acc is None:
            summary = summary + u"｜验收队列：不可得"
            reds.append(u"Q 尺取不到验收队列（那条腿没答话）——不能当绿")
        elif acc[0]:
            summary = summary + (u"｜交完活停着等验收 %d 扇（%s）" % (acc[0], acc[1]))
            reds.append(u"有 %d 扇交完活就停着，最可能卡在验收口：%s" % (acc[0], acc[1]))
            hub_alarm(u"Q", u"acceptance",
                      u"Q 档：这几扇是**交完活之后**停下来的，不是懒也不是缺单——"
                      u"先点它们比按时间往下读更省；压龄与静默分钟在那条腿的输出里，"
                      u"重算一条：python " + ACCEPT_LEG)
        else:
            summary = summary + u"｜交完活停着等验收 0 扇"
        say("轮 %d：%s｜%s" % (rounds, summary, "红" if reds else "绿"))
        if reds:
            for x in reds:
                say("  红因：" + x)
            if not actionable(reds):
                say("  （这一红不在我能落地的格子里（A/E/F/G）——只记不退场，下轮继续盯）")
                left0 = int(deadline - time.time())
                if left0 <= 0:
                    break
                time.sleep(max(30, min(period, left0)))
                continue
            io.open(HIT, "w", encoding="utf-8", newline="\n").write(
                u"哨兵于 %s 判红，需要人动：%s\n读数：%s\n边界：本哨兵 0 发送、0 上总线，红因只报事实与归属；"
                u"B 的叫醒权在号令者，A 才轮到我敲门。\n" % (
                    time.strftime("%Y-%m-%d %H:%M:%S"), "；".join(reds), summary))
            say("已落 _sentinel_relay_HIT.txt，早退交人")
            return 0
        left = int(deadline - time.time())
        if left <= 0:
            break
        time.sleep(max(30, min(period, left)))
    say("预算 %d 分钟跑满（%d 轮）且全程绿——没有人需要我传话" % (total_min, rounds))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
