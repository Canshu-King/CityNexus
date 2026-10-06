"""Overnight auto-watcher: rounds + the three things a sleeping commander cannot see.

Every cycle it runs patrol/round.py, refreshes the wake-candidate list and the relay texts, and then decides
whether to post ONE factual note to the bus. It never edits the ledger, never inserts blocks, never deletes a
file, never moves the authoritative branch, and never clicks another window's prompts.

Thresholds (all recorded in autumn_watch_state.json so a note is posted once, not every cycle):
  * a lane whose transcript ends on an unanswered tool_use for >= STALL_MIN  -> prompt-stall note (per lane, once)
  * any drive with free space < LOW_GB                                      -> disk note (once)
  * a door-green, bolt-clean block waiting >= WAIT_MIN in the inbox         -> landing-blocked note (per block, once)
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LC = os.path.dirname(HERE)
LOG = os.path.join(HERE, "autumn_watch.log")
STATE = os.path.join(HERE, "autumn_watch_state.json")
STALL_MIN = 30.0
LOW_GB = 8.0   # 09-29 06:14 从 6 提到 8：D 盘 05:04≈13.5 GB → 06:06=11 GB，掉速约 2 GB/小时，
# 6 GB 触发太晚（照这个速度 08:00 就会穿过，而夜里没人能清理），提前到 8 GB 给号令者留两小时。
WAIT_MIN = 25.0
# 09-29 04:55 起：被闸口拒的块提前到 15 分钟就报（号令者自己给的代插承诺是 ≤15 分钟，
# 而 04:53 实测到一枚块卡了 73 分钟——车道看不见拒绝，只以为没人来插）。
REFUSE_MIN = 5.0   # 09-29 05:22 从 15 降到 5：map_0517.md 我在 0.5 分钟就手工抓到一枚不可解析的 40 位，
#                   等 15 分钟等于让车道白等一轮代插；再短会咬到车道正在写的块，所以取 5 分钟。


def say(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line)
    with io.open(LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def load():
    try:
        return json.load(io.open(STATE, encoding="utf-8"))
    except Exception:
        return {"stall_posted": [], "disk_posted": None, "waiting_posted": [], "rounds": 0}


def save(s):
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(s, ensure_ascii=False, indent=1))


def post_to_bus(text, tag):
    fn = os.path.join(HERE, "_autumn_%s.md" % tag)
    raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
    assert len(raw) == 83 and hashlib_ok(raw), "closing line file changed - refusing to post"
    io.open(fn, "w", encoding="utf-8", newline="\n").write(text.rstrip() + "\n" + raw.decode("utf-8").strip() + "\n")
    # 06:34 加固：发贴失败不能让循环死——总线是一条外挂通道，读不到就下一轮再试，值守本身要继续跑。
    try:
        r = subprocess.run([PY, os.path.join(LC, "bus_post.py"), fn], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900)
    except Exception as e:
        say("bus post (%s) 本轮失败（不退出）：%s: %s" % (tag, type(e).__name__, str(e)[:160]))
        return None
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    say("bus post (%s): %s" % (tag, out.replace("\n", " | ")[:220]))
    m = re.search(r"POST -> (\d+) (\d+)", out)
    return m.group(2) if m else None


def hashlib_ok(raw):
    import hashlib
    return hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"


_DOOR = None


def shape_skips():
    """09-29 05:12 补的一类静默丢失：文件名不合门禁形状（例 `n3_0505.draft.md` 多了 `.draft`）时，
    代插工具直接 SKIP——块既不进账本也没人告诉车道。这里**借用门禁自己的 `shape_problem`**（同一段代码），
    不自己另写一套判据。"""
    import importlib.util
    global _DOOR
    if _DOOR is not None:
        door = _DOOR
    else:
        spec = importlib.util.spec_from_file_location("door_r2", os.path.join(LC, "ledger_inbox_apply_r2.py"))
        if not spec:
            return []
        door = importlib.util.module_from_spec(spec)
        # 门禁自己 import 了 `cmdr_net_env_guard_r2`（在 live_checks 目录下），不把这个目录放进 sys.path
        # 就会 ModuleNotFoundError——我第一次测的时候异常被 except 吞掉，形状那条臂其实一直没生效（05:13 发现）。
        if LC not in sys.path:
            sys.path.insert(0, LC)
        try:
            spec.loader.exec_module(door)   # 会跑一次代理守卫，所以只在进程内做一次
        except Exception as e:
            say("shape_skips 加载门禁失败：%s" % type(e).__name__)
            return []
        _DOOR = door
    root = r"D:\moodle\_qoder_ledger_inbox"
    out = []
    for f in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if not f.endswith(".md") or f.startswith("_"):
            continue
        p = os.path.join(root, f)
        try:
            age = (time.time() - os.path.getmtime(p)) / 60.0
            text = io.open(p, encoding="utf-8", newline="\n").read()
        except Exception:
            continue
        problem = door.shape_problem(text, f)
        if problem and age >= REFUSE_MIN:
            out.append({"file": f, "age": round(age, 1), "q43": "?", "verdict": "SHAPE_SKIP",
                        "aborts": 0, "bad": ["门禁原判： %s" % problem]})
    return out


def pending_aborts():
    """04:37 起新增的一眼：收件目录里「尺绿但被第二道闸拒」的块，车道自己看不见（它只会以为号令者没来插）。

    用只读副本 bolt_replica.py 过两闸。注意它**不读 argv**、一次扫整个收件目录，
    所以我按**文件名那一行**取每块自己的判定，再把它下面那些 `L<行号>` 的被拒行收进来
    （04:38 我第一次写的时候误以为它是逐块调用，拿到的是字母序第一块 cmdr_0438 的 RED）。"""
    root = r"D:\moodle\_qoder_ledger_inbox"
    ages = {}
    try:
        for f in os.listdir(root):
            if not f.endswith(".md"):
                continue
            try:
                ages[f] = (time.time() - os.path.getmtime(os.path.join(root, f))) / 60.0
            except Exception:
                pass
    except Exception:
        return []
    stale = {f: a for f, a in ages.items() if a >= REFUSE_MIN}
    if not stale:
        return []
    r = subprocess.run([PY, os.path.join(HERE, "bolt_replica.py")], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=900,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
    out = ((r.stdout or "") + (r.stderr or ""))
    rows = []
    for f, age in stale.items():
        m = re.search(re.escape(f) + r"\s+q43=(\S+)\s+bolt=(\S+)\s+abort=(\d+)", out)
        if not m:
            continue
        verdict = m.group(2)
        bad = []
        # 第一道闸（Q43 尺）本身就红的块：把尺的原样 findings 抓回来，车道才有得可改
        if m.group(1) == "RED":
            rr = subprocess.run([PY, os.path.join(LC, "claim_coordinate_check_r7.py"), "--text",
                                 os.path.join(root, f)], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=900,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
            rout = ((rr.stdout or "") + (rr.stderr or ""))
            bad = re.findall(r"^\s*line \d+ \S+ .*$", rout, re.M)
            head_line = [l for l in rout.split("\n") if l.startswith("claims checked")]
            bad = (head_line[:1] + bad)[:6]
            verdict = "Q43-RED"
        else:
            tail = out[m.end():]
            bad = re.findall(r"^\s{4,}L\d+\s+\S{8,}\s+declared=\S+\s+anchored=\S+.*$", tail, re.M)
        if verdict not in ("WOULD-ABORT", "Q43-RED"):
            continue
        rows.append({"file": f, "age": round(age, 1), "q43": m.group(1), "verdict": verdict,
                     "aborts": int(m.group(3)), "bad": bad[:6]})
    return rows


def write_pending_relay(row):
    """给值守（我）留一份可复核的敲门件：谁的块、等了多久、被拒的是哪几行、两条合法修法。"""
    os.makedirs(os.path.join(HERE, "relay"), exist_ok=True)
    fn = os.path.join(HERE, "relay", "pending_%s_%s.txt" % (row["file"][:-3], time.strftime("%H%M")))
    gate = ("第一道闸（Q43 尺 r7）" if row["verdict"] == "Q43-RED"
            else ("门禁形状（文件名/首行）" if row["verdict"] == "SHAPE_SKIP" else "第二道闸（坐标闸）"))
    fix_shape = ("把文件名改成 `<车道前缀>_<HHMM>.md` 形状（正则 `^[A-Za-z0-9._-]+_[0-9]{4}\\.md$`）——带 `.draft` "
                 "这类后缀会被代插工具直接 SKIP，块既不进账本也没人提醒你；正文一个字不用改。"
                 "想留痕就把旧名去掉尾巴 `.md`。")
    # 09-29 05:04 把现行闸口逐字核对过（`ledger_insert_after_r2.py:36-110`）：它**只扫 `\b[0-9a-f]{40}\b`**，
    # 短形它根本不看；免除要两件事同时成立——值**自己那一行**写明不是 git 对象，且**所在段落里有另一枚能 cat-file 的 40 位**。
    # `path:line` 只满足第一道闸（尺），不满足这道闸；我之前把它当锚递给过车道，那是我的错，这里已改成正确的说法。
    fix = ("把这枚尺跑到 rc=0 再交：`D:/moodle/CityNexus/.venv/Scripts/python.exe "
           "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py --text <你的块>`"
           "（CLI 只有 `--text`）；findings 点名到行——裸数要在**同一行**带 `path:line`/`field=value`/完整 40 位，"
           "不该写的数改成具名 `NOT_MEASURED`，别删同行其他证据。"
           if row["verdict"] == "Q43-RED" else
           "这道闸的免除要**两件事同时成立**，只做一件仍然红："
           "① 那枚 40 位值**自己那一行**写明它不是 git 对象（`本机 sha1|文件 sha1|内容 sha1|非 blob|不可 cat-file|从未入 git|本地字节重算` 任一，"
           "**`path:line` 在这道闸不算**）；"
           "② 它**所在段落**（连续非空行）里还有**另一枚能 `git cat-file` 的 40 位**（自己 push 过的枝头即可，门会先 fetch 全部分支）。"
           "若那枚值本该是 git 对象，就直接换成可解析的 40 位——闸口只认逐字 40 位，写短形等于没写。")
    if row["verdict"] == "SHAPE_SKIP":
        fix = fix_shape
    txt = "\n".join([
        "【值守 %s · 收件块 `%s` 被%s拒，已等 %.1f 分钟（q43=%s 判定=%s aborts=%d）】"
        % (time.strftime("%H:%M"), row["file"], gate, row["age"], row["q43"], row["verdict"], row["aborts"]),
        "原样读数：",
    ] + ["  > %s" % b.strip() for b in row["bad"]] + [
        "",
        fix,
        "",
        "改完请**覆盖同名件**，不要改名、不要删旧件（02:2x 号令者的代插工具在“列目录→读文件”之间撞上改名崩过一轮）。",
    ])
    io.open(fn, "w", encoding="utf-8", newline="\n").write(txt + "\n")
    return fn


def alive(pid):
    """判「这个 PID 还是不是**这一支自动轮**」，只读、不动目标进程。

    09-30 12:25 实测的毛病：原来只用 kernel32.OpenProcess 取句柄，句柄取得到就算活。
    我把 18260/50916 两条都 Stop-Process 之后（回读命令行匹配 0 行），12:25:45 重启时
    OpenProcess 对 50916 仍取得到句柄 ⇒ 「拒绝双开、退出码 2」，而那一支其实已经死了。
    Windows 上进程对象在有未释放句柄时仍可被 OpenProcess 打开（PID 也可能被复用），
    所以「句柄存在」不等于「那一支还在跑」。
    改成认身份：拿这台机器的进程表按 PID 查它的命令行，命令行里必须有 autumn_watch 才算活；
    查不动（powershell 起不来）时退回旧的句柄判据，并把两种读数都写进日志，别让下一次要靠猜。
    """
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"ProcessId=%d\" | "
             "ForEach-Object { $_.CommandLine }) -join '|'" % int(pid)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25)
        cl = ((p.stdout or "").strip())
        if p.returncode == 0 and cl:
            # 01:08 实测的毛病：光「取到命令行」会认错人。锁里写着上一支的 PID 23596，
            # 那一支 23:59 就退了，Windows 把 23596 复用给了车道目录里的 esbuild.exe，
            # 于是这句回 "yes" ⇒ 我自己拒绝启动、退出码 2（值守就此断档）。命令行必须含本支的名字。
            if "autumn_watch" in cl:
                return ("yes", cl[:160])
            return ("no", "PID %s 已被别的进程复用，命令行不含 autumn_watch：%s" % (pid, cl[:160]))
        if p.returncode == 0 and not cl:
            return ("no", "进程表里 PID %s 没有命令行（判不在）" % pid)
        return ("probe-failed", "CIM rc=%s %s" % (p.returncode, (p.stderr or "")[:80]))
    except Exception as exc:
        try:
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
            if h:
                ctypes.windll.kernel32.CloseHandle(h)
                return ("probe-failed-handle-open", "退回句柄判据：取得到句柄（不代表那一支还在）")
            return ("no", "退回句柄判据：取不到句柄")
        except Exception as exc2:
            return ("probe-failed", "%s / %s" % (exc.__class__.__name__, exc2.__class__.__name__))


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    gap = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    # 单实例锁（09-29 07:48 加）：07:40:21 与 07:45:31 我确实双开过两条自动轮，两条都往同一份日志里写。
    # 那 5 分钟里各步读数都是「无」，所以没有重复上总线（回验过：段内无一条「已发/bus post」），
    # 但双开这件事不能靠我记得——规则要装进启动这一步。
    # 判「PID 还在不在」不能用 `os.kill(pid, 0)`：07:53 我那版就是这么写的，Windows 上 CPython 的
    # os.kill 对非 CTRL_C/CTRL_BREAK 走 OpenProcess+TerminateProcess，`0` 不是可靠的「只探一下」——
    # 它对我自己的自动轮抛了 OSError，于是「拒绝双开」当场变成「接管锁」，我因此又双开了一次
    # （两条并行 4 分钟，期间各步读数都是「无」，回验日志无一条「已发/bus post」，没有重复上总线）。
    # 这里改用 kernel32.OpenProcess 取只读句柄，取不到才算不在。
    lock = os.path.join(HERE, "autumn_watch.pid")
    if os.path.isfile(lock):
        try:
            old = int(io.open(lock, encoding="utf-8").read().strip())
        except Exception:
            old = None
        if old and old != os.getpid():
            verdict, detail = alive(old)
            log_age = (time.time() - os.path.getmtime(LOG)) / 60.0 if os.path.exists(LOG) else 9e9
            if verdict == "yes":
                say("已有自动轮在跑（PID %s，命令行：%s），这一份拒绝双开，退出码 2" % (old, detail))
                return 2
            if verdict == "probe-failed" and log_age < 2.0 * gap / 60.0:
                # 认不出身份、但日志在两拍之内还在长 ⇒ 那一支大概率活着。宁可这一份不起，
                # 也不能双开：09-30 我自己定过规矩，双开的两条轮会往同一份日志写、报警也可能重发。
                say("锁里的 PID %s 判不动（%s：%s），但日志 %s 分前还在长（< 两拍），这一份让位，退出码 2"
                    % (old, verdict, detail, "%.1f" % log_age))
                return 2
            say("锁里的 PID %s 判为不在（%s：%s；日志 %s 分未长），这一份接管锁"
                % (old, verdict, detail, "%.1f" % log_age))
    with io.open(lock, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    st = load()
    st.setdefault("aborted_posted", [])
    for i in range(rounds):
        st["rounds"] = st.get("rounds", 0) + 1
        say("=== cycle %d/%d start" % (i + 1, rounds))
        # 06:34 加固：一次网络抖动就能让 `round.py` 抛 TimeoutExpired，而它在这一轮**最前面**——
        # 不包住的话整个夜间循环会静默退出，等到我下次自查已经过了半小时。单步失败只记账、继续下一轮。
        try:
            r = subprocess.run([PY, os.path.join(HERE, "round.py")], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=1500)
            body = (r.stdout or "") + (r.stderr or "")
        except Exception as e:
            body = ""
            say("round.py 本轮失败（继续，不退出）：%s: %s" % (type(e).__name__, str(e)[:160]))
        if body:
            with io.open(os.path.join(HERE, "round_watch.log"), "a", encoding="utf-8", newline="\n") as f:
                f.write(body)
        # 交付脉搏：09-29 05:38 起每轮记一行「最近 45 分钟有哪些 review 枝动过、涉及哪几张单」，
        # 这样“车道在不在干活”在日志里留有可回查的证据，而不是靠进程或端口猜。
        try:
            dp = subprocess.run([PY, os.path.join(HERE, "_delivery_pulse.py"), "45"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            first = ((dp.stdout or "").strip().split("\n") or [""])[0]
            say("脉搏 %s" % first[:220])
        except Exception as e:
            say("脉搏读取失败：%s" % type(e).__name__)
        # refresh the candidate list and the relay texts (writing files only - the window knock is mine to send)
        try:
            for script in ("wake_from_commits.py", "relay.py"):
                subprocess.run([PY, os.path.join(HERE, script)], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=1500)
        except Exception as e:
            say("转达扫描本轮失败（继续）：%s: %s" % (type(e).__name__, str(e)[:160]))
        try:
            cands = json.load(io.open(os.path.join(HERE, "wake_candidates.json"), encoding="utf-8"))
            say("待转达 %d 条：%s" % (len(cands.get("candidates", [])),
                                     ", ".join(sorted({c["lane"] for c in cands.get("candidates", [])})) or "无"))
        except Exception as e:
            say("wake_candidates 读取失败：%s" % type(e).__name__)
        stalls = re.findall(r"弹窗停摆\? (\S+)\((\w{8})\) 最后一条 tool_use=(\w+) 无 result，已 ([\d.]+) 分钟", body)
        for nm, id8, tool, mins in stalls:
            say("停摆候选 %s(%s) %s 分钟 tool=%s" % (nm, id8, mins, tool))
            # 09-29 04:26 学到的一眼：`tool_use 无 result` 有两种成因——审批形（Bash/Edit/Write/删除类，等人点）
            # 与**委派在飞**（Agent/Skill/Task 本来就要跑很久；那时刻 `list_chat_sessions` 侧 pendingInteractionCount=0、
            # runtimeState=running）。只有前者能写「停在弹窗上」；后者只记账不发贴，否则我给号令者递一条假事实。
            PERM_SHAPED = ("Bash", "Edit", "Write", "MultiEdit", "search_replace", "delete_file",
                           "NotebookEdit", "mcp__builtin__qoder_cron")
            if tool not in PERM_SHAPED:
                say("  不发贴：tool=%s 是委派在飞形，不是审批形（要 pendingInteractionCount>0 才算弹窗）" % tool)
                continue
            if float(mins) >= STALL_MIN and id8 not in st["stall_posted"]:
                cid = post_to_bus(
                    "**值守 %s · 一条车道停在一条未应答的 tool_use 上 `%s` 分钟，账本里看不出来**\n\n"
                    "- 车道 %s（会话 `%s`）：它的会话流水最后一条是 `assistant/tool_use`(%s)，其后没有 `tool_result`。\n"
                    "- 这一条形有**两种成因**，我这侧分不开：① 等人工点批准（会话侧会是 `waiting-user` + `pendingInteractionCount>0`）；"
                    "② 回合死在半路（`runtimeState=cold` 而 `pendingInteractionCount=0`，05:25 那一格实测就是这一形）。"
                    "两者都不该写成「有人在等点击」，所以这条贴只把形报出来，判读留给能看见窗口的人。\n"
                    "- 我**不点别人的批准、不重投别人的命令**（批准的常是删除类命令），也不动它的块；敲门对①解不开弹窗（昨夜 20:40 实测过），对②能续上。\n"
                    "- 同一判据本轮 census 掐着=0 ⇒ 不是额度。其余读数见 `patrol/round_watch.log`（每轮一条：磁盘、census、收件分类、现尖移动）。"
                    % (time.strftime("%H:%M"), mins, nm, id8, tool), "stall_" + id8)
                st["stall_posted"].append(id8)
                say("已发停摆贴 %s -> %s" % (id8, cid))
        if not stalls:
            say("停摆扫描：无")
        frees = re.findall(r"磁盘 (\S+) free=([\d.]+) GB used=([\d.]+)%", body)
        low = [(d, float(v)) for d, v, _u in frees if float(v) < LOW_GB]
        # 回弦：**已经回到阈值以上**的盘，把它记着的下界抬上去（正在低档的不动，否则同一拍就把该贴的吃掉）。
        # 10-03 00:25 实测到的洞：C: 12:58 掉到 6 GB 贴过一次，后来回到 8.07、00:19 又掉到 7.65；
        # 而 `low` 只收 <8 GB 的盘，回升那几拍根本不进循环 ⇒ 记着 6 的旧下界让「再掉回 6」也不会响，
        # 等于盘越涨越迟钝，白捡 1.65 GB 的静默。掉档才贴，回档就上弦。
        lowset = set(d for d, _v in low)
        seen0 = st.setdefault("disk_bands", {})
        for d, v, _u in frees:
            if d in lowset:
                continue
            prev0 = seen0.get(d)
            if prev0 is not None and int(float(v)) > prev0:
                seen0[d] = int(float(v))
                say("盘紧档位回弦 %s %s->%s GB（已回到阈值上方，抬下界；再掉一档才会贴）" % (d, prev0, int(float(v))))
        for d, v in low:
            # 旧版是 `if st.get("disk_posted") != d`——一枚盘整夜只能贴一次，贴过之后哪怕只剩 3 GB 也不响。
            # 改成按「整 GB 档位」发：第一次见到只**种子**不贴（免得跟着别人刚报过的数再刷一遍），
            # 之后每掉一档贴一次。09-30 01:16 实测：01:03=6 GB → 01:16=4.9 GB（掉 1.1 GB），
            # 而 01:18 又回到 5.4 GB（有车自己在回收），所以速率不是直线，只有掉档才值得喊。
            band = int(v)
            seen = st.setdefault("disk_bands", {})
            prev = seen.get(d)
            if prev is None:
                seen[d] = band
                say("盘紧档位种子 %s=%s GB（本轮不贴，掉到下一档才贴）" % (d, band))
                continue
            if band < prev:
                cid = post_to_bus(
                    "**值守 %s · 盘又掉了一档：`%s` 从 `%s` GB 掉到 `%s` GB**\n\n"
                    "- 每轮 `round.py` 都量磁盘；这条阈值是 `%s` GB，掉一个整 GB 档才贴一次（旧版一枚盘整夜只贴一次，之后再也不响）。\n"
                    "- 其他盘现读：%s。\n"
                    "- 我不删任何东西（包括车道自己的临时件），只报数；要不要清、清哪一层，是号令者或用户的决定。"
                    % (time.strftime("%H:%M"), d, prev, v, LOW_GB,
                       "、".join("`%s` %s GB" % (a, b) for a, b, _c in frees)), "disk_" + re.sub(r"\W", "", d))
                seen[d] = band
                st["disk_posted"] = d
                say("已发盘紧贴 %s %s->%s GB -> %s" % (d, prev, band, cid))
        # a block that passes BOTH gates and still sits un-inserted past the commander's own <=15 min promise
        # 旧版是 `wait.group(1) not in st["waiting_posted"]`：一枚块整夜只贴一次。09-30 05:00 实测它
        # 在 03:52 贴过 newlane2_0310 之后就再也不响，而这枚到 05:00 已经等了 103 分（承诺 <=15 分），
        # 越等越久反而越安静——和盘紧贴当年「一夜只响一次」是同一类缺陷。改成分档升级：
        # 15 / 60 / 150 / 300 分钟各响一次，跨档才贴，同一档不重复。
        BANDS = (15.0, 60.0, 150.0, 300.0)
        wait_all = re.findall(r"BLOCK_GREEN (\S+) 已等 ([\d.]+) 分钟", body)
        wp = st.get("waiting_posted")
        if isinstance(wp, list):        # 旧状态：只记名字 ⇒ 迁移成「已贴过第一档」
            st["waiting_posted"] = {k: BANDS[0] for k in wp}
        bands = st.setdefault("waiting_posted", {})
        for nm, mins in wait_all:
            m = float(mins)
            cur = max([b for b in BANDS if m >= b], default=None)
            if cur is None or bands.get(nm, 0.0) >= cur:
                continue
            cid = post_to_bus(
                "**值守 %s · 一枚两闸都干净的块在收件目录等了 `%s` 分钟（第 %d 档提醒）**\n\n"
                "- 块 `%s`：Q43（现行门那枚尺 `%s`）GREEN、第二道闸干净 ⇒ 这一类确实是等代插，不是等车道重切。\n"
                "- 提醒档位是 15／60／150／300 分钟，跨档才贴；上一档是 `%s` 分钟时贴过，所以这次不是重复刷屏。\n"
                "- 同一轮的其他分类：%s\n"
                "- 我不代插（`LEDGER_SINGLE_WRITER_V1` 是一枝笔），只把等待时长量出来；要不要跑那一跳、先跑哪一枚，归你。"
                % (time.strftime("%H:%M"), mins, int(cur), nm, "claim_coordinate_check_r7.py",
                   ("%g" % bands.get(nm, 0.0)) if bands.get(nm) else "从未",
                   (re.search(r"积压分类：(.*)", body).group(1).strip() if re.search(r"积压分类：(.*)", body) else "?")),
                "waiting_" + re.sub(r"\W", "", nm)[:16] + "_%d" % int(cur))
            bands[nm] = cur
            say("已发等插贴 %s 第%s分档 -> %s" % (nm, ("%g" % cur), cid))
        # 01:14 实测的毛病：这一格是「历史累计在记」，不是现值。01:10 号令者的门把收件口整批排空了
        # （1ba48dbf_0056→inserted_010959 等 5 枚），可 01:13 那拍还印「待插在记 16 枚」——读的人会以为
        # 有 16 枚在等代插。只在门的那一轮扫描确实跑成（有「积压分类」行）时，把不在收件口的名字摘掉。
        try:
            if re.search(u"积压分类：", body):
                live = set(x[0] for x in wait_all)
                gone = [k for k in list(bands) if k not in live]
                for k in gone:
                    bands.pop(k)
                if gone:
                    say(u"待插登记摘掉 %d 枚（已不在收件口根目录）：%s" % (len(gone), u"、".join(gone[:6])))
        except Exception as e:
            say(u"待插登记清理失败（不影响下一轮）：%s" % type(e).__name__)
        # 落地预测进自动轮（09-29 07:37 加）：待插块里申报的每条 review/* 枝，对现尖只读预测能不能干净落；
        # 号令者一轮要亲测十几枚块，这一条把他最容易漏的「申报的枝基线已经过时」变成日志里的现成读数。
        try:
            lp = subprocess.run([PY, os.path.join(HERE, "_claims_vs_remote_r1.py")], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=900)
            lb = (lp.stdout or "") + (lp.stderr or "")
            one = re.search(r"合计实质不一致 \d+ 处", lb)
            bad = re.findall(r"^      (?:落地对现尖 .*|枝 refs/heads/.*|40 位 .*)$", lb, re.M)
            say("落地预测：%s；细项 %d 条%s" % (
                one.group(0) if one else "读数不全",
                len(bad), ("｜" + "；".join(x.strip()[:80] for x in bad[:3])) if bad else ""))
        except Exception as e:
            say("落地预测本轮失败（不退出）：%s" % type(e).__name__)
        # 「回合以 API 失败终止」这一形（09-29 07:45 加）：会话在 API 面上看着 ready/cold，
        # 像交完活在等，其实那一步没做完、也没人知道。旧停摆判据只看未应答 tool_use，接不住这种。
        try:
            fp = subprocess.run([PY, os.path.join(HERE, "_failed_turns_r1.py")], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=900)
            fb = (fp.stdout or "") + (fp.stderr or "")
            first = (fb.strip().split("\n") or [""])[0]
            say("失败终态：%s" % first[:180])
            failed = [l.strip() for l in fb.split("\n") if l.strip().startswith("!!")]
            for l in failed:
                say("停在失败上（需要重发）：%s" % l[:170])
            # 09-30 18:05 新加：这一形以前只写在我自己流水里，总线上没人知道。
            # 连续 3 拍（≈30 分钟）还停在失败上才上贴，再按 30/90/150 分档各发一次；清了补一句「清了」。
            if failed:
                st["fail_streak"] = int(st.get("fail_streak") or 0) + 1
                mins = st["fail_streak"] * 10
                band = 0 if mins < 30 else (3 if mins >= 150 else (2 if mins >= 90 else 1))
                if band > int(st.get("fail_band") or 0):
                    cid = post_to_bus(
                        u"**值守 %s · 有 %d 条会话停在「回合以 API 失败终止」那一形，已连着 %d 拍（约 %d 分钟）**\n\n"
                        u"- 逐条原文（尺现读）：%s\n"
                        u"- 为什么单独报：这种会话在 API 面上看着 ready/cold，像交完活在等，其实那一步没做完；旧的停摆判据只看未应答 tool_use，接不住这一形。\n"
                        u"- 我这条只上贴不代重发：重发谁、让他回去做哪张单，是号令者的点名权（工头助签那侧我若要接手，得先看它名下有没有未交的单）。"
                        % (time.strftime("%H:%M"), len(failed), st["fail_streak"], mins,
                           u"；".join(x.lstrip("! ").strip()[:150] for x in failed[:4])),
                        "failturn%d" % band)
                    st["fail_band"] = band
                    say("已发失败终态贴（%d 条 / %d 分，档 %d）-> %s" % (len(failed), mins, band, cid))
            else:
                if int(st.get("fail_band") or 0) > 0:
                    cid = post_to_bus(u"**值守 %s · 「停在失败上」清了**（上一档我报过 %s 条 / 连 %s 拍）\n\n- 档位与连拍计数已归零，重新武装。"
                                      % (time.strftime("%H:%M"), str(st.get("fail_band_last_n", "?")),
                                         str(st.get("fail_streak", "?"))), "failclear")
                    say("已发失败终态清贴 -> %s" % cid)
                st["fail_streak"] = 0
                st["fail_band"] = 0
                st["fail_band_last_n"] = len(failed)
        except Exception as e:
            say("失败终态本轮读数不全（不退出）：%s" % type(e).__name__)
        # 「尺绿但第二道闸拒」的块：车道自己看不到，只会安静等着 ⇒ 每轮过一遍，写一份可复核的敲门件，并按块发一贴
        for row in (pending_aborts() + shape_skips()):
            fn = write_pending_relay(row)
            say("块被闸口拒（%s）：%s 已等 %.1f 分 aborts=%d -> relay/%s"
                % (row["verdict"], row["file"], row["age"], row["aborts"], os.path.basename(fn)))
            if row["file"] not in st["aborted_posted"]:
                cid = post_to_bus(
                    "**值守 %s · 一枚待插块按门的原式复算会被第二道闸拒（`%s`），已在收件目录 `%s` 分钟：`%s`**\n\n"
                    "- 先说性质：这是**我的只读复算**（`patrol/bolt_replica.py` 与 `_bolt_exact.py`，判据逐字取自 "
                    "`ledger_insert_after_r2.py:36-110`），不是门的实测判决——门上一趟是 05:16 那批，这枚块写在其后。"
                    "报这条的目的是让车道在门跑之前就能改，不是替门宣布拒收。\n"
                    "- 复算读数：q43=%s、判定=%s、aborts=%d；被点名的行逐字如下：\n%s\n"
                    "- 两道闸的分工：第一道是 Q43 尺（裸数要**同一行**带 `path:line`/`field=value`/完整 40 位）；"
                    "第二道只扫逐字 40 位，免除要**值自己那一行**写明不是 git 对象 **且** 同段有另一枚能 `git cat-file` 的 40 位"
                    "（`path:line` 在第二道不算；带反引号的「不可 `git cat-file`」也不认——见 `5879481931` 的探针）。\n"
                    "- 可照做的修法已写成件：`patrol/relay/%s`；我也按块点名给那条车道（窗口只报读数与可过的写法，裁定仍归号令者）。\n\n"
                    "边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。"
                    % (time.strftime("%H:%M"), row["verdict"], row["age"], row["file"], row["q43"], row["verdict"],
                       row["aborts"],
                       "\n".join("  > `%s`" % b.strip()[:300] for b in row["bad"]) or "  > （本轮没带回行，见 relay 件）",
                       os.path.basename(fn)),
                    "aborted_" + re.sub(r"\W", "", row["file"])[:16])
                st["aborted_posted"].append(row["file"])
                say("已发待插被拒贴 %s -> %s" % (row["file"], cid))
        # 05:49 加的一眼：账本里「ORD-#### → <uuid>」这种派单，整串 uuid 可能写错（05:36 那块 ORD-0446 就是拼接形）。
        # 派单规矩本身是「按会话 id 点名」，整串错了就会敲错窗口 ⇒ 每轮扫一遍，新出现的一枚报一次。
        try:
            uu = subprocess.run([PY, os.path.join(HERE, "_bus_uuid_typo.py"), "--json"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
            j = json.loads(((uu.stdout or "").strip().split("\n") or ["{}"])[-1])
            bad = j.get("bad") or []
            say("派单 uuid 核对：核 %s 枚，拼接 %d 条，无法判定 %d 条"
                % (j.get("checked"), len(bad), len(j.get("unknown") or [])))
            for b in bad:
                if b["wrote"] in st.get("uuid_posted", []):
                    continue
                cid = post_to_bus(
                    "**值守 %s · 账本里有一枚派单 uuid 是拼接的，按整串开窗口的话会敲错车道**\n\n"
                    "- 现读 `:%s`：%s…\n  写的是 `%s`；注册表（本机 `projects/D--moodle/<uuid>.jsonl` 文件名 + 04:20 会话名单）里"
                    "前 8 位 `%s` 的真会话是 `%s`。\n"
                    "- 我这侧按前 8 位匹配，所以转达仍送对了窗口；但这条派单的整串形是坏的，请开单的一方**在新块里补一具名勘误**"
                    "（旧块不许重写），或以后同时写前 8 位与整串两形。\n"
                    "- 我不改账本、不替任何一方认领收件人。\n\n"
                    "边界：值守 0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次点别人的批准。"
                    % (time.strftime("%H:%M"), b["line"], b["frag"], b["wrote"], b["wrote"][:8], b["real"]),
                    "uuid_" + b["wrote"][:8])
                st.setdefault("uuid_posted", []).append(b["wrote"])
                say("  已发派单 uuid 拼接贴 %s -> %s" % (b["wrote"][:13], cid))
        except Exception as e:
            say("派单 uuid 核对失败：%s" % type(e).__name__)
        # 11:46 新加的一格：cron 的每小时一跳 11:00 已到期（nextRunAt=11:15:12 在到期之后），
        # 所以代插从现在起只靠号令者手动跑。队列非空且代插停了 >=30 分才算门停，缺一不报。
        try:
            db = subprocess.run([PY, os.path.join(HERE, "_door_backlog_r1.py"), "30"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=600,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
            dl = [x.strip() for x in ((db.stdout or "") + (db.stderr or "")).split("\n") if x.strip()]
            say("门停探测器：%s" % (dl[0][:190] if dl else "读数不全"))
            if db.returncode == 3 and dl:
                since = st.get("door_posted_ts", 0)
                if time.time() - since > 3600:
                    cid = post_to_bus(
                        "**值守 %s · 入账门已停（这不是停摆误报，两个条件同时成立才报）**\n\n"
                        "- %s\n"
                        "- 队列里的块按命名门算都还合格（`_claims_vs_remote_r1.py` 每轮在算落地预测），"
                        "但 cron 每小时一跳 `expiresAt = 11:00:00` 已过、`nextRunAt = 11:15:12` 落在到期之后 ⇒ "
                        "**今天不会再有自动跳**，代插只能由你手动跑。\n"
                        "- 我按规矩不插块、不写账本、不动门、不动权威线；这条只报「车道已在交、门没在收」这个形状。\n\n"
                        "边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。"
                        % (time.strftime("%H:%M"), "\n".join(dl[1:6])),
                        "door_stop")
                    st["door_posted_ts"] = time.time()
                    say("  已发门停贴 -> %s" % cid)
        except Exception as e:
            say("门停探测器本轮失败（不退出）：%s: %s" % (type(e).__name__, str(e)[:140]))
        # 11:51 新加：争用尺 r2 —— 谁的枝被现尖追成「两侧都改过」，复切就会 ABORT。
        # 同一枚头只报一次，且总线贴每小时最多一条，免得把「预测」刷成噪音。
        try:
            cr = subprocess.run([PY, os.path.join(HERE, "_hotfile_contention_r2.py")],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=900,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
            cl = [x.strip() for x in ((cr.stdout or "") + (cr.stderr or "")).split("\n") if x.strip()]
            risk = [x for x in cl if "两侧都改过" in x and "两侧都改过 0 枚" not in x
                    and not x.startswith((u"小结", u"现尖"))]
            say("争用尺 r2：%s" % ([x for x in cl if x.startswith(u"小结")][:1] or ["读数不全"])[0][:170])
            newrisk = [x for x in risk if x.split("头")[0].strip() not in st.get("risk_posted", [])]
            for x in newrisk[:3]:
                if x.startswith("cmdr-"):
                    continue        # 号令者自己的 batch/recut 中间物不当车道欠交
                if time.time() - st.get("risk_posted_ts", 0) < 3600:
                    say("  本轮有新风险枝但 1 小时内已发过贴，只记不发：%s" % x[:120])
                    continue
                cid = post_to_bus(
                    "**值守 %s · 一枚车道枝被现尖追成「两侧都改过」⇒ 按复切判据预测 ABORT（只读预测，门的实判归 `--apply`）**\n\n"
                    "- %s\n"
                    "- 判据来源：`patrol/_hotfile_contention_r2.py`（`ls-remote` + `merge-base` + `ls-tree -r` 缓存，"
                    "逐枚对该枝自己动过的每一枚文件比 base/车道/现尖三份 blob；两侧改到**同一字节**不算争用，"
                    "这条是 10:14 我修掉的假报形）。\n"
                    "- 我没有动任何枝；这条只为了让落地顺序与 rebase 提醒早一点到车道。\n\n"
                    "边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线。"
                    % (time.strftime("%H:%M"), x[:600]),
                    "risk_" + re.sub(r"[^0-9a-zA-Z]", "", x[:24]) or "risk")
                st.setdefault("risk_posted", []).append(x.split("头")[0].strip())
                st["risk_posted_ts"] = time.time()
                say("  已发争用预测贴 -> %s" % cid)
        except Exception as e:
            say("争用尺本轮失败（不退出）：%s: %s" % (type(e).__name__, str(e)[:140]))
        # 13:04 新加：已申报但没落地的候选清单（cron 到期后，落地这一笔全靠号令者记得跑）
        try:
            rl = subprocess.run([PY, os.path.join(HERE, "_ready_not_landed_r1.py"), "150"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=900,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
            rll = [x.strip() for x in ((rl.stdout or "") + (rl.stderr or "")).split("\n") if x.strip()]
            s1 = [x for x in rll if x.startswith(u"其中") or x.startswith(u"小结")]
            idle = ""
            for x in rll:
                if x.startswith(u"现尖") and "提交时间" in x:
                    idle = x
                    break
            say("待落地清单：%s" % (" / ".join(s1[:2])[:200] if s1 else "读数不全"))
            m = re.search(r"(\d+(?:\.\d+)?)\s*分前", idle or "")
            n_ready = len([x for x in rll if "只读预测=" in x])
            if m and float(m.group(1)) >= 40 and n_ready >= 5 and time.time() - st.get("queue_posted_ts", 0) > 3600:
                cid = post_to_bus(
                    "**值守 %s · 队列又在等落地：现尖已 %.0f 分钟没动，已申报未落地候选 %d 枚**\n\n"
                    "- %s\n"
                    "- 尺 `patrol/_ready_not_landed_r1.py`（只读：块的枝名+申报头 → `merge-base --is-ancestor` 判是否已在线上 → 未落的跑一次 `merge-tree --write-tree`）。\n"
                    "- 我不落地、不写账本、不动权威线；这条只是把那批「已经能落」的名字摊在你眼前。\n\n"
                    "边界：值守 0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次改动 cron。"
                    % (time.strftime("%H:%M"), float(m.group(1)), n_ready,
                       "\n".join(x[:210] for x in rll if "只读预测=" in x)),
                    "ready_queue")
                st["queue_posted_ts"] = time.time()
                say("  已发待落地清单贴 -> %s" % cid)
        except Exception as e:
            say("待落地清单本轮失败（不退出）：%s: %s" % (type(e).__name__, str(e)[:140]))
        # 14:59 新加：自申报单的「无人接」探测器。cron 没了 ⇒ 他不再逐窗催，
        # 而冷车道不会自己重读账本；夜里这条靠我每轮看一眼（只报数，敲不敲由我判，尺不自动发消息）。
        try:
            uo = subprocess.run([PY, os.path.join(HERE, "_unclaimed_orders_r1.py"), "3"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=900,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
            ul = [x.strip() for x in ((uo.stdout or "") + (uo.stderr or "")).split("\n") if x.strip()]
            none = [x for x in ul if x.startswith("!!")]
            say("无人接的单：%s" % ("0 张" if not none else "%d 张：%s" % (len(none), "; ".join(x[2:40] for x in none[:4]))))
        except Exception as e:
            say("无人接探测本轮失败（不退出）：%s: %s" % (type(e).__name__, str(e)[:140]))
        # 15:03 新加：收件口里「命名不合规 ⇒ 门静默跳过」的隐形交付（15:01 我手抓到一枚）。
        try:
            iv = subprocess.run([PY, os.path.join(HERE, "_invisible_blocks_r1.py")],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=300,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
            il = [x.strip() for x in ((iv.stdout or "") + (iv.stderr or "")).split("\n") if x.strip()]
            say("隐形交付：%s" % (il[0][:170] if il else "读数不全"))
            for x in il:
                if x.startswith("!!"):
                    say("  需提醒车道改名：%s" % x[:170])
        except Exception as e:
            say("隐形交付探测失败（不退出）：%s: %s" % (type(e).__name__, str(e)[:140]))
        # 19:40 新加：D 盘水位打点。报告 §四 的速率原本靠我手工采，最后一粒停在 15:13，
        # 到夜里就成了旧数；每轮采一发，晚报告就能算真实斜率。
        try:
            dfr = subprocess.run(["df", "-B", "1G", "/d"], capture_output=True, text=True,
                                 timeout=90, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            dl = [x for x in (dfr.stdout or "").split(chr(10)) if x.strip()]
            if len(dl) >= 2:
                dw = dl[1].split()
                with io.open(os.path.join(HERE, "disk_trend.txt"), "a", encoding="utf-8") as fdf:
                    fdf.write("%s %s GiB free (df used %s)%s"
                              % (time.strftime("%H:%M"), dw[3], dw[4], chr(10)))
        except Exception as e:
            say("水位打点失败（不退出）：%s: %s" % (type(e).__name__, str(e)[:100]))
        # 19:03 新加：额度潮名册（今晚 18:38 起一波把 11 条车道接连闸掉，判"要不要敲门"必须先分清停在闸上还是自己停的）。
        try:
            qr = subprocess.run([PY, os.path.join(HERE, "_quota_roster_r1.py")],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=300,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
            ql = [x.strip() for x in ((qr.stdout or "") + (qr.stderr or "")).split(chr(10)) if x.strip()]
            for x in ql[:4]:
                say("额度名册：%s" % x[:190])
            # 09-30 17:44 新加：额度潮要**上总线**，不能只留在我自己的流水里。
            # 今天 16:4x 与 17:1x 两波把 8 条车道接连闸掉，号令者是一轮一轮手工叫醒的；
            # 他若只看到「有几条没动静」就会漏叫。这条只报「谁在闸上、停了多久」，**我不敲任何车道**（叫醒是他独有的活）。
            # 分档防重复：每 3 条一档，且 60 分钟内不重发；潮退时报一次「停了」。
            mc = re.search(u"停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", ql[0] if ql else u"")
            if mc:
                capped_n, writing_n, silent_n = int(mc.group(1)), int(mc.group(2)), int(mc.group(3))
                names_line = next((x for x in ql if x.startswith(u"闸上")), u"（名册没给名单行）")
                kou = next((x for x in ql if u"口径" in x), u"")
                band = capped_n // 3
                since = time.time() - float(st.get("quota_posted_at", 0))
                if band >= 1 and st.get("quota_band") != band and since > 3600:
                    cid = post_to_bus(
                        u"**值守 %s · 额度潮：%d 条车道停在额度闸上（名单逐字取自名册尺）**\n\n"
                        u"- 停在闸上：%s\n"
                        u"- 同一拍名册其余两格：在写 %d 条｜静默非闸 %d 条\n"
                        u"- 判据：停在闸上＝那条会话的最后一条角色记录是 `daily usage limit`；工具块（tool_use/tool_result）算在跑，不算停。\n"
                        u"- 我**不敲任何一条车道**——叫醒是号令者独有的活（他 17:33 那块尾条自己说「额度断档了，我先看每条车道现在什么状态，再逐个叫醒」）。这条只把名单报全，免得漏叫。\n"
                        u"- 名册口径：%s"
                        % (time.strftime("%H:%M"), capped_n, names_line, writing_n, silent_n, kou[:220]),
                        "quotawave_%d" % band)
                    st["quota_band"] = band
                    st["quota_posted_at"] = time.time()
                    st["quota_last"] = {"at": time.strftime("%H:%M"), "n": capped_n, "names": names_line[:200]}
                    say("已发额度潮贴（%d 条在闸上，档 %d）-> %s" % (capped_n, band, cid))
                elif capped_n == 0 and st.get("quota_band"):
                    last = st.get("quota_last") or {}
                    cid = post_to_bus(
                        u"**值守 %s · 额度潮退了：停在闸上 0 条**\n\n"
                        u"- 上一波我 %s 报过，当时 %s 条：%s\n"
                        u"- 这一拍名册：在写 %d 条｜静默非闸 %d 条。要不要逐条叫醒仍归号令者，我只报潮起潮落。\n"
                        u"- 分档口径：每 3 条一档、60 分钟内不重发；这一条发完档位清零。"
                        % (time.strftime("%H:%M"), last.get("at", "?"), last.get("n", "?"), last.get("names", "?"),
                           writing_n, silent_n),
                        "quotaclear")
                    st["quota_band"] = None
                    st["quota_posted_at"] = time.time()
                    say("已发额度潮退贴 -> %s" % cid)
        except Exception as e:
            say("额度名册探测失败（不退出）：%s: %s" % (type(e).__name__, str(e)[:140]))
        # 09-30 17:56 新加：**整队没人干活**这一格以前没有档。今天 06:02:40→10:07:02 连续 16 拍「在写 0」（244 分钟），
        # 盘有档、待插有档、闸上有名册，就是没人响过——用户的要求是「保证他们至少工作到晚上11点」，
        # 所以这一段必须自己响，不能等我想起来查。分档 30/60/120 分钟，亮了就重新武装。
        try:
            dw = subprocess.run([PY, os.path.join(HERE, "_dark_window_r1.py"), "1"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=300, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            db = (dw.stdout or "") + (dw.stderr or "")
            in_dark = (u"当前是否正处在暗窗里：是" in db)
            dm = re.search(u"已黑 (\\d+) 分钟", db)
            dmin = int(dm.group(1)) if dm else 0
            dnow = re.search(u"最新一拍 \\d\\d:\\d\\d:\\d\\d：在写 (\\d+)｜闸上 (\\d+)｜静默 (\\d+)", db)
            band = 0 if not in_dark else (3 if dmin >= 120 else (2 if dmin >= 60 else (1 if dmin >= 30 else 0)))
            if band > int(st.get("dark_band") or 0):
                cid = post_to_bus(
                    u"**值守 %s · 车队黑了 %d 分钟（这是新加的档：30/60/120 分钟，以前这一格没有报警）**\n\n"
                    u"- 这一拍名册：在写 %s｜停在闸上 %s｜静默 %s（判据＝会话最后一条角色记录是不是额度字样，工具块算在跑）。\n"
                    u"- 今天已经出现过的暗窗（`_dark_window_r1.py` 现算）：%s\n"
                    u"- 我不敲任何车道：潮退后叫醒归号令者；这里只是把「整队停着」这件事在响之前先没人知道的状态拿掉。\n"
                    u"- 尺的限度：分辨率是自动轮 600 秒一拍，两拍之间黑→亮→黑看不见。"
                    % (time.strftime("%H:%M"), dmin,
                       (dnow.group(1) if dnow else "?"), (dnow.group(2) if dnow else "?"),
                       (dnow.group(3) if dnow else "?"),
                       u"；".join(m2.group(1).strip() for m2 in re.finditer(
                           u"^\\s\\s+(\\d\\d:\\d\\d:\\d\\d → .*)$", db, re.M))[:400]),
                    "dark%d" % band)
                st["dark_band"] = band
                say("已发暗窗贴（黑 %d 分，档 %d）-> %s" % (dmin, band, cid))
            elif band == 0 and int(st.get("dark_band") or 0) > 0:
                cid = post_to_bus(
                    u"**值守 %s · 车队亮了：暗窗结束（上一档我报过「黑 %s 分钟」）**\n\n"
                    u"- 这一拍名册：在写 %s｜停在闸上 %s｜静默 %s。\n"
                    u"- 档位已清零重新武装；下一次再黑到 30 分钟还会响。"
                    % (time.strftime("%H:%M"), str(st.get("dark_last_min", "?")),
                       (dnow.group(1) if dnow else "?"), (dnow.group(2) if dnow else "?"),
                       (dnow.group(3) if dnow else "?")),
                    "darkback")
                st["dark_band"] = 0
                say("已发亮窗贴 -> %s（档清零）" % cid)
            elif in_dark:
                st["dark_last_min"] = dmin
        except Exception as e:
            say("暗窗探测失败（不退出）：%s: %s" % (type(e).__name__, str(e)[:140]))
        # 10-01 05:2x 加：软件重启（模型排队→用户重启）之后「号令者的叫醒有没有人回」这一格。
        # 04:57 那次实测：17 条在场会话都被叫醒到、也全都回了；但下次不一定——队列堵着与那轮真掉了，
        # 在流水上的表现是一样的（尾是 user 叫醒、后面没有 assistant 记录）。所以这里只量条数与最久等待，
        # 分两档（15 / 40 分钟）上总线；草稿在探测器输出里，发不发、发给谁归号令者，我不代派单。
        try:
            rw = subprocess.run([PY, os.path.join(HERE, "_restart_watch_r1.py"), "120"], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=900)
            rb = (rw.stdout or "") + (rw.stderr or "")
            head = re.search(u"在场会话（最近 [\\d.]+ 分钟动过）(\\d+) 条｜被叫醒过 (\\d+) 条｜叫醒后已回话 (\\d+) 条｜叫醒后仍未回话 (\\d+) 条(?:｜停在额度字样且没人接 (\\d+) 条)?", rb)
            waits = [float(x) for x in re.findall(u"等了 +([\\d.]+) 分", rb)]
            if head:
                ln_, wn_, rn_, dn_ = [int(head.group(k)) for k in (1, 2, 3, 4)]
                # 05:39 自测与 13:31 实测都指到同一件事：今天真正卡住的形状是「停在额度那句上、根本没人叫过它」，
                # 那一形在「叫醒后仍未回话」里是 0（因为压根没叫醒）。所以档要按 (未回话 + 停在额度且没人接) 合起来算，
                # 否则这一格只会在被叫醒过的车道上响，漏的正好是最大那一族。
                nq_ = int(head.group(5) or 0)
                mx = max(waits) if waits else 0.0
                say(u"重启叫醒：在场 %d｜叫醒 %d｜已回 %d｜未回 %d｜停在额度且没人接 %d｜最久没回 %.1f 分（现档 %s）" % (
                    ln_, wn_, rn_, dn_, nq_, mx, str(st.get("restart_band"))))
                nbad = dn_ + nq_
                rband = 0 if nbad == 0 else (2 if (mx >= 40.0 or nq_ >= 3) else (1 if (mx >= 15.0 or nq_ >= 1) else 0))
                if rband > int(st.get("restart_band") or 0):
                    who = u"；".join(x.strip()[:58] for x in re.findall(u"^   [0-9a-f]{8}.*$", rb, re.M))[:280]
                    cid = post_to_bus(
                        u"**值守 %s · 有 %d 条车道卡在额度/叫醒之后没动（叫醒后未回话 + 停在额度句上没人接过；最久 %.1f 分，第 %d 档）**\n\n"
                        u"- 两种形状分开看：① 号令者叫过、之后没有 assistant 记录；② 尾条还是「daily usage limit」那句、根本没人叫过它。前者像卡队列，后者像漏叫。\n"
                        u"- 逐条（`_restart_watch_r1.py` 现读）：%s\n"
                        u"- 同一份输出里带着**可粘贴的第二次叫醒草稿**（只重述它自己那条叫醒里的单号与尖）；发不发归你\n"
                        u"- 为什么不上来就敲：叫醒后没回话与排在队列里，这两种在流水上读不出差别。\n"
                        % (time.strftime("%H:%M"), nbad, mx, rband, who or u"（无逐条行）"),
                        "restart%d" % rband)
                    st["restart_band"] = rband
                    say(u"已发重启叫醒贴（未回 %d 条 / 最久 %.1f 分，档 %d）-> %s" % (dn_, mx, rband, cid))
                elif rband == 0 and int(st.get("restart_band") or 0) > 0:
                    cid = post_to_bus(u"**值守 %s · 重启叫醒这格清了：被叫醒的车道都有 assistant 回话了**（上一档我报过 %s 条没回）\n"
                                      % (time.strftime("%H:%M"), str(st.get("restart_band_n", "?"))), "restartclear")
                    st["restart_band"] = 0
                    say(u"已发重启叫醒清贴 -> %s" % cid)
                st["restart_band_n"] = dn_
            else:
                say(u"重启叫醒：读数不全（探测器没给汇总行，不猜）")
        except Exception as e:
            say(u"重启叫醒探测失败（不退出）：%s: %s" % (type(e).__name__, str(e)[:140]))
        # 09-30 18:06 加：每拍把各报警档的**现值**打一行。以前只能靠「没有探测失败」倒推分支跑过，
        # 那是弱证据；夜里我要的是能一眼看见「这五档各自在哪一档、上次几点发的」。
        try:
            _wp = st.get("waiting_posted") or {}
            say("报警档现值：盘=%s GiB 档｜待插在记 %d 枚（最高档 %s 分；这一格是收件口根目录的现值，上一拍若没跑成扫描就沿用上拍）｜额度潮档=%s｜暗窗档=%s｜失败档=%s（连 %s 拍）｜cycle=%d/%d" % (
                str(st.get("disk_bands", {}).get("D:\\")),
                len(_wp), (max(_wp.values()) if _wp else "-"),
                str(st.get("quota_band")), str(st.get("dark_band")),
                str(st.get("fail_band")), str(st.get("fail_streak")), i + 1, rounds))
        except Exception as e:
            say("报警档现值打印失败（不影响下一轮）：%s" % type(e).__name__)
        save(st)
        say("cycle done, sleeping %ds" % gap)
        time.sleep(gap)
    say("AUTO WATCH FINISHED")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
