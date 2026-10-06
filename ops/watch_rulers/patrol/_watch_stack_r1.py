# -*- coding: utf-8 -*-
"""值守栈的一键起复：`python _watch_stack_r1.py`（缺哪支补哪支，已有的绝不起第二支）。

为什么要有它：这台机器 8 天里蓝屏 8 次（ntoskrnl + WHEA 处理器内部奇偶错），
一旦重启，`autumn_supervise` / `哨兵续跑器` / `autumn_watch` / `哨兵` 会**一起没了**，
而续跑器只能救哨兵、救不了自己——那一夜就真没人盯了，车队安静到天亮也没人报警。
这一枚是给「回来发现全空」那个场景的入口，也是我自己半夜回来补coverage的入口。

口径：判活一律按 CommandLine（且只认 python 起的），不看平台的 runtimeState/updatedAt（它们滞后）。
边界：只起 COMPONENTS 里点名的那几支（supervise/keepalive/verdict/bus_hub/board/keeper/inbox_applier，
     watch 与哨兵由前两支各自带起）；0 次碰他人进程（含号令者的 cmdr_night_watch）、0 次改 cron、0 次写注册表。
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PYEXE = sys.executable
LOGDIR = HERE
DETACH = 0
if os.name == "nt":
    DETACH = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008   # DETACHED_PROCESS（与续跑器同一形制）

COMPONENTS = [
    # (名字, 脚本, 日志文件, 环境默认收工)
    ("supervise", "autumn_supervise_r1.py", "autumn_supervise.log",
     u"到 %s 自停；它自己带起 autumn_watch" % os.environ.get("SUP_STOP", "2340")),
    ("keepalive", "_sentinel_keepalive_r1.py", "_sentinel_keepalive.log",
     u"到 %s 自停；它自己带起哨兵" % os.environ.get("SENTINEL_STOP", "2335")),
    # 23:00 出件那枚也要能被重启拉回来。它自己有闸：锁里的 pid 还活着就退、done 写着今天就不再出第二份，
    # 所以「重起」是安全的——不会因为多拉一次而落两份互相矛盾的读数。
    ("verdict", "_night_verdict_runner_r1.py", "_night_verdict_runner.log", "到 23:00:20 出终值单+第2格补件，出完自退", u"23:00:20"),
    # 11:00 前收尾那一档也进覆盖，否则它一死就得靠我正好醒着补（上一条注释里那次就是这么丢的）。
    # 两档同名脚本 ⇒ 判活必须带档点标记，不然场上只要有任一枚 verdict，另一档就被读成"已在"。
    ("verdict_1055", "_night_verdict_runner_r1.py", "_night_verdict_runner_early.log",
     u"到 %s 出收尾读数（今天 11:00 前那一档），出完自退" % os.environ.get("NVR_EARLY_AT", "10:55:00"),
     os.environ.get("NVR_EARLY_AT", "10:55:00")),
    # BB 机中枢也得进这一串：它原先不在覆盖里 —— 今天这台机器重启过四轮，第五轮一起来
    # 账本哨兵都会被拉回来，唯独 4799 那扇门是死的，车道与号令者的问答会静静堆在 drop/ 里没人吸收。
    # 它自己带单实例锁（hub.lock），重复起的那一枚会自退，所以这里多拉一次不落第二个服务。
    ("bus_hub", u"D:/moodle/agent_bus/bus_hub.py", "_bus_hub_stack.log",
     u"BB 机中枢（127.0.0.1:4799）：带单实例锁，重复起的那枚自退"),
    # 人看的那块板（127.0.0.1:4820）也进覆盖：主人白天回来若板子开了、中枢没开，他会看见一块"取数失败"的死板；
    # 反过来中枢活着而板子掉了，他唯一能自己按的「发话」门就没了。它自己先探端口：撞了 REFUSE 退出，不抢别人的口。
    ("board", u"D:/moodle/agent_bus/board.py", "_board_stack.log",
     u"工地板（127.0.0.1:4820，只绑本机）：端口被占就 REFUSE 自退，不会挤掉别的服务"),
    # 看门人自己也进表：它掉了我这一夜的「一键起复」就只剩靠人敲；它在表里 ⇒ 任何一次起复都会把它补回来。
    # 反过来它每轮又跑这条命令，而这条命令按 CommandLine 认到现支就不再起第二枚 ⇒ 不会自我增殖。
    ("keeper", "_stack_keeper_r1.py", "_stack_keeper.log",
     u"每 900 秒转交一次本脚本（缺才起、有就不起），到 SENTINEL_STOP 收工"),
    # 代插这一格不能靠「值守记得跑」：10-04 午后我被上下文压缩腰斩几小时，
    # 三枚待插块就在收件口躺了两小时多才落地。这条腿自己每 900 秒跑一次 applier，
    # 空目录不动写、被门拒的原样留着等号令者拆，且带单实例锁绝不双插。
    ("inbox_applier", "_inbox_applier_r2.py", "_inbox_applier.log",
     u"每 900 秒代插一次（只跑现成 applier，不自己写账本）；到 APPLIER_STOP 收工"),

    # 巡检跑批也进覆盖：19:14-19:16 实测它由工具手起时只活一拍（stdout 空、无异常、tasklist 三查皆无），
    # 与栈腿同形制却被回收 ⇒ 它落在工具进程树的清理范围里。挂进栈就由栈来起、也随栈重启拉回。
    # 它自带单实例锁（`_patrol_loop_r1.py` 的 claim()），叠上栈的去重 ⇒ 不会起出第二枚。
    # **四元**：不能带第五项——栈把 entry[4] 当档点塞 `NVR_AT=` argv，跑批不认那个变量。
    # 间隔走 env（`PATROL_LOOP_MIN`，栈的 start() 也会把 os.environ 传下去）。
    ("patrol_loop", "_patrol_loop_r1.py", "_patrol_loop.log",
     u"每 %s 分钟自己跑一次巡逻并存档；到 %s 自停（比守到 11:00 晚五分钟留写快照）"
     % (os.environ.get("PATROL_LOOP_MIN", "12"), os.environ.get("PATROL_LOOP_STOP", "1105"))),]

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ps_rows():
    q = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*python*' } | "
         "Select-Object ProcessId,CommandLine | ConvertTo-Csv -NoTypeInformation")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", q],
                         capture_output=True).stdout.decode("utf-8", "replace")
    rows = []
    for l in out.split(chr(10)):
        if not l.strip():
            continue
        p = l.split('","')
        if len(p) < 2:
            continue
        pid, cl = p[0].strip('"'), p[1]
        if pid == "ProcessId":
            continue
        rows.append((pid, cl))
    return rows


def alive(name, script, rows=None, slot=None):
    rows = rows if rows is not None else ps_rows()
    hit = [(pid, cl) for pid, cl in rows if script in cl and "python" in cl.lower()]
    if slot:
        # 同一份脚本守几档：只认 CommandLine 里带着本档标记的那几枚。
        # 不带标记的老腿（重启前手起的那些）在这儿会读成"缺"，下一拍被带标记的新腿替上；
        # 真 double 起不了：取数器自己有按档点的锁，锁里 pid 还活着就自退，不重写出第二枚。
        hit = [x for x in hit if (u"NVR_AT=%s" % slot) in x[1]]
    return hit


def resolve(script):
    """组件可以写相对名（本目录），也可以写绝对路径（BB 机中枢在 D:/moodle/agent_bus）。
    取数时刻一律按脚本自己所在目录起：bus_hub 用 __file__ 定位账本，cwd 给错就会指到别处的账。"""
    p = script if os.path.isabs(script) or ":" in script[:3] else os.path.join(HERE, script)
    return p.replace("\\", "/")


def start(name, script, logfile, slot=None):
    p = resolve(script)
    if not os.path.exists(p):
        raise RuntimeError("脚本不在：" + p)
    cwd = os.path.dirname(p)
    # slot 非空 ⇒ 把档点当显式 argv 传（env 那份也一起给，兼容手敲的跑法）：
    # 这样进程表里就看得见"这一枚守的是哪一档"，判活才分得开同名脚本的两档。
    argv = [PYEXE, p] + ([u"NVR_AT=%s" % slot] if slot else [])
    with io.open(os.devnull, "rb") as dn, io.open(os.path.join(LOGDIR, logfile), "a") as out:
        pr = subprocess.Popen(argv, stdin=dn, stdout=out, stderr=out, cwd=cwd,
                              creationflags=DETACH,
                              env=dict(os.environ, PYTHONIOENCODING="utf-8",
                                       **({"NVR_AT": slot} if slot else {})))
    return pr.pid


def kid_gap_note(kid):
    """数不到子支时，先分清「判红早退的空档」与「真缺」，再说要不要动手。

    10-05 06:0x 连着两次踩到：哨兵 06:00:24 判红落 HIT 后按设计早退交人，
    keepalive 下一拍才把它带回来；我 06:00:32 巡检就数不到它，那行写的是「还缺」，
    读起来像要动手。把两种形状混在一行的后果是我可能手起第二枚哨兵 ⇒ 双哨兵双报警，
    那才是真事故。所以这一格现在先读 HIT 文件的落档时刻：20 分钟内落过就写「早退交人」。
    """
    hit = os.path.join(HERE, u"_sentinel_relay_HIT.txt")
    if kid == u"sentinel" and os.path.exists(hit):
        age = (time.time() - os.path.getmtime(hit)) / 60.0
        if age < 20:
            return (u"（刚判红早退交人：HIT 落档 %d 分前 ⇒ 等 keepalive 下一拍，"
                    u"别手起第二枚）" % int(age))
    return u"（还没有，父支下一拍会带起）"


def main():
    check_only = "--check" in sys.argv
    rows = ps_rows()
    started, kept, missing_files = [], [], []
    for entry in COMPONENTS:
        name, script, logfile, note = entry[0], entry[1], entry[2], entry[3]
        slot = entry[4] if len(entry) > 4 else None   # 老的四元条目＝不带档点的普通腿
        if not os.path.exists(resolve(script)):
            missing_files.append(name)
            continue
        # 判活按脚本名本身，不按我登记时写的那串路径：中枢是 `python bus_hub.py`（相对名＋cwd）起来的，
        # 拿绝对路径去比就永远比不中 ⇒ 每轮都误判成「死了」，然后反复去拉第二枚。
        hit = alive(name, os.path.basename(script), rows, slot=slot)
        if hit:
            kept.append(u"%s 已在（pid=%s）" % (name, ",".join(x[0] for x in hit)))
            continue
        if check_only:
            started.append(u"%s **缺**（--check 不动手）" % name)
            continue
        pid = start(name, script, logfile, slot)
        started.append(u"%s 起了一枚 pid=%s｜%s" % (name, pid, note))
    time.sleep(3)
    rows2 = ps_rows()
    kids = []
    for kid, script in (("watch", "autumn_watch.py"), ("sentinel", "_sentinel_relay_r1.py")):
        h = alive(kid, script, rows2)
        kids.append(u"%s=%s" % (kid, ",".join(x[0] for x in h) if h else kid_gap_note(kid)))
    print(u"_watch_stack_r1.py 于 %s｜现数 %d 行 python 进程" % (time.strftime("%m-%d %H:%M:%S"), len(rows2)))
    for x in kept:
        print(u"   保留：" + x)
    for x in started:
        print(u"   动作：" + x)
    for x in missing_files:
        print(u"   缺文件：%s（不起，只报）" % x)
    print(u"   子支：" + u"、".join(kids))
    kid_missing = any(u"（还没有" in k for k in kids)
    kid_early = any(u"早退交人" in k for k in kids)
    if not started and not missing_files and not kid_missing and not kid_early:
        print(u"⇒ 栈完整，0 次启动（这条命令可反复跑，重复跑不会起第二支）")
    elif kid_early and not kid_missing:
        # 判红早退**不是停摆**：这一行既不许写成「栈完整」（场上此刻真没有哨兵进程），
        # 也不许写成「还缺、再跑一次」——后者会诱导我去手起第二枚哨兵，双哨兵＝双报警，
        # 那才是真事故。所以这里只指路：等 keepalive 下一拍带回，红因去看 HIT 那枚文件。
        print(u"⇒ 父支齐、哨兵刚判红早退交人：等 keepalive 下一拍把它带回，**别手起第二枚**；"
              u"红因见 _sentinel_relay_HIT.txt。")
    elif kid_missing:
        # 「父支都在」不等于「值守在跑」：子支（哨兵/watch）没起来时这句必须另说，
        # 否则一次 --check 就把 K/M 档整档停摆读成绿灯（10-04 14:0x 自己踩到）。
        print(u"⇒ 父支齐、子支还缺：这一行**不等于值守在跑**，看下一拍父支带不带得起；带不起就再跑一次不带 --check。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
