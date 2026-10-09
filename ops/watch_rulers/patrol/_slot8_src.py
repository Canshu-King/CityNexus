# 8) 值守覆盖——「这一档有没有人盯着」本身也要有数，不是我说盯过就算盯过。
#    为什么要这一格：今天已经三次整机重启（14:06 / 22:11 / 23:49），每一次都会把我的值守栈一起带走；
#    而终值单原本只有车队与门的读数，看不出夜里其实有一段没人盯。覆盖洞要能被算出来，不能靠我记得。
print("\n8) 值守覆盖（哨兵/续跑/监督/取数器）：")
try:
    import ctypes as _ct
    _up_ms = _ct.windll.kernel32.GetTickCount64()
    _boot = time.time() - _up_ms / 1000.0
    print("   本次开机 %s｜已 %.0f 分（若开机时刻晚于今天 18:00，则 18:00→开机之间无人盯）" % (
        time.strftime("%m-%d %H:%M:%S", time.localtime(_boot)), (time.time() - _boot) / 60.0))
except Exception as _e:
    print("   开机时刻：读数不全（%s）" % type(_e).__name__)

_slog = os.path.join(HERE, "_sentinel_relay_latest.log")
try:
    _rows = [l for l in io.open(_slog, encoding="utf-8", errors="replace").read().split(chr(10))
             if l.startswith("[") and "] 轮 " in l]
    _stamps = []
    for _l in _rows:
        _hms = _l[1:9]
        _e2 = hhmm_to_epoch(_hms[:5])
        _stamps.append(_e2)
    _stamps.sort()
    _gaps = [(_b - _a) / 60.0 for _a, _b in zip(_stamps, _stamps[1:])]
    _big = [g for g in _gaps if g > 25.0]
    _last_age = (time.time() - _stamps[-1]) / 60.0 if _stamps else -1
    print("   哨兵轮行 {n} 枚｜相邻拍最大间隔 {mx:.0f} 分｜>25 分的断拍 {nb} 处｜最后一拍距今 {age:.0f} 分".format(
        n=len(_stamps), mx=max(_gaps) if _gaps else 0.0, nb=len(_big), age=_last_age))
    if _big:
        print("   ⚠ 断拍就是覆盖洞（重启/崩了没被拉回）：这些间隔里没人盯，别看成「那段很安静所以没红」")
except Exception as _e:
    print("   哨兵轮次：读数不全（%s）" % type(_e).__name__)

for _nm, _f in (("续跑器", "_sentinel_keepalive.log"), ("监督", "autumn_supervise.log"),
                ("取数器", "_night_verdict_runner.log"), ("脉搏", "autumn_watch.log")):
    _p = os.path.join(HERE, _f)
    if os.path.isfile(_p):
        print("   {nm} 日志最后写入距今 {age:.0f} 分".format(
            nm=_nm, age=(time.time() - os.path.getmtime(_p)) / 60.0))
    else:
        print("   {nm} 日志：读数不全（文件不在）".format(nm=_nm))

_q = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*python*' } | "
      "Select-Object ProcessId,CommandLine | ConvertTo-Csv -NoTypeInformation")
try:
    _o = subprocess.run(["powershell", "-NoProfile", "-Command", _q], capture_output=True, env=ENV).stdout
    _txt = _o.decode("utf-8", "replace")
    _live = {}
    for _key in ("autumn_supervise_r1", "_sentinel_keepalive_r1", "_sentinel_relay_r1",
                 "autumn_watch.py", "_night_verdict_runner_r1"):
        _live[_key] = _txt.count(_key)   # 每行命令行只出现一次，所以出现次数＝在世实例数
    print("   现数在世实例（按命令行）：监督 {a}｜续跑 {b}｜哨兵 {c}｜脉搏 {d}｜取数器 {e}".format(
        a=_live["autumn_supervise_r1"], b=_live["_sentinel_keepalive_r1"], c=_live["_sentinel_relay_r1"],
        d=_live["autumn_watch.py"], e=_live["_night_verdict_runner_r1"]))
except Exception as _e:
    print("   在世实例：读数不全（%s）" % type(_e).__name__)

try:
    _proc = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "_processed")
    _d0 = hhmm_to_epoch("00:00")
    _ins = [p for p in os.listdir(_proc) if ".inserted_" in p and os.path.getmtime(os.path.join(_proc, p)) >= _d0]
    print("   今天（{d} 00:00 起）收件口进账 {n} 枚｜此刻根目录待插 {m} 枚".format(
        d=today, n=len(_ins),
        m=len([x for x in os.listdir(r"D:\moodle\_qoder_ledger_inbox")
               if x.endswith(".md") and os.path.isfile(os.path.join(r"D:\moodle\_qoder_ledger_inbox", x))])))
except Exception as _e:
    print("   进账枚数：读数不全（%s）" % type(_e).__name__)

