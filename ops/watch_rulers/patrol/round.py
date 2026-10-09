"""One patrol round, appended to round_watch.log by a background loop until the 11:00 deadline (09-29).

Round contents (all read-only except the round log itself):
  1. session census with quota_now's own predicate (掐着 / 在产出 / 静待);
  2. inbox classification by the ruler the live door calls + the writer's second bolt;
  3. whether the authoritative tip moved since the previous round (so "the line is sleeping" is a measured claim);
  4. lanes the newest ledger blocks point at, minus whoever is already producing;
  5. free space per drive (lanes write hardlinked export trees; D: filled up at 23:5x and the
     commander had to clean it), and lanes whose transcript ENDS on an unanswered tool_use
     (the permission-prompt signature that cost 129 lane-minutes last night).
State persists in round_state.json so a restart does not re-report the same tip as "new".
"""
import glob
import io
import json
import os
import re
import subprocess
import quota_now as Q
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
STATE = os.path.join(HERE, "round_state.json")
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"


def load():
    try:
        return json.load(io.open(STATE, encoding="utf-8"))
    except Exception:
        return {"last_tip": None, "notified": {}}


def save(s):
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(s, ensure_ascii=False, indent=1))


def run(script, *args):
    r = subprocess.run([PY, os.path.join(HERE, script)] + list(args), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=1800)
    return (r.stdout or "") + (r.stderr or "")


def disk_free():
    """Free space per drive, in GB, from shutil (cheap). Lanes write hardlinked export trees, so this
    is the resource that actually kills a night: report it every round with an alarm threshold."""
    import shutil
    out = []
    for d in ("C:\\", "D:\\", "E:\\"):
        try:
            u = shutil.disk_usage(d)
            out.append((d, round(u.free / 2 ** 30, 1), round(100.0 * u.used / u.total, 1)))
            if d == "D:\\":
                # 09-30 12:45 加：D 盘每拍落一点进 disk_points.txt。总线上的斜率只能由**两个落档的点**算——
                # 12:42 我自己撞出来的：12:30 那次 df 只留在终端里，于是「约 0.8 GB/小时」那句拿不出原件。
                # 只写不读，失败就跳过，不影响本轮其它读数。
                try:
                    with io.open(os.path.join(HERE, "disk_points.txt"), "a", encoding="utf-8") as fh:
                        fh.write("%s %d\n" % (time.strftime("%m-%d %H:%M:%S"), int(u.free / 1024)))
                except Exception:
                    pass
        except Exception as e:
            out.append((d, None, type(e).__name__))
    return out


def lane_universe(hours=12.0):
    """要盯的车道集合 = 名册表里的 ∪ 最近 `hours` 小时内真的动过的流水文件。

    09-30 18:33 实测过这个洞：`Q.NAMES` 只有 13 条，而今天 10 小时内动过的会话有 18 枚，
    **其中 11 枚不在表里**（含今晚主力 1ba48dbf / e766b154 / da46954a / cff87c64 / 5a53846b / 6a150e1e / 8ac89982…）。
    停摆扫描以前只遍历这张静态表 ⇒ 23:00 的保证是拿一只看不见大半车队的眼在守。
    现在名字仍从表里取（花名只一张表这条不改），取不到就标 `未登记·<id8>`，**认不到也照样盯**。
    """
    import glob as _g
    ids = dict(Q.NAMES)
    cutoff = time.time() - hours * 3600.0
    for f in _g.glob(os.path.join(Q.BASE, "*.jsonl")):
        if os.path.getmtime(f) >= cutoff:
            sid = os.path.basename(f)[:8]
            ids.setdefault(sid, u"未登记·" + sid)
    for sid in ("494abfd7", Q.ME, "6efab655"):     # 号令者本人 + 值守自己 + 不可寻址的旧实例，都不当车道敲
        ids.pop(sid, None)
    return ids


def stalled_lanes(tail_bytes=512 * 1024, min_idle_min=15.0):
    """Lanes whose transcript ENDS on an assistant tool_use with no tool_result, read from the tail only.

    Reading just the tail is deliberate: the 号令者 log is ~200 MB, and a prompt-stall is by definition at the
    end of the file. Returns [(lane, id8, idle_min, tool_name)].
    """
    import glob as _g
    rows = []
    for id8, nm in lane_universe().items():
        f = _g.glob(os.path.join(Q.BASE, id8 + "*.jsonl"))
        if not f:
            continue
        p = max(f, key=os.path.getmtime)
        idle = (time.time() - os.path.getmtime(p)) / 60.0
        if idle < min_idle_min:
            continue
        size = os.path.getsize(p)
        with io.open(p, "rb") as fh:
            if size > tail_bytes:
                fh.seek(size - tail_bytes)
            raw = fh.read().decode("utf-8", "replace")
        last_use = None
        for line in raw.split(chr(10))[1:]:        # drop the first (possibly truncated) line
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            m = d.get("message") or {}
            c = m.get("content")
            if not isinstance(c, list):
                continue
            for x in c:
                if not isinstance(x, dict):
                    continue
                if m.get("role") == "assistant" and x.get("type") == "tool_use":
                    last_use = x.get("name")
                if m.get("role") == "user" and x.get("type") == "tool_result":
                    last_use = None
        if last_use:
            rows.append((nm, id8, round(idle, 1), last_use))
    return rows


def main():
    out = []
    s = load()
    out.append("===== [%s] round" % time.strftime("%H:%M:%S"))
    for d, free_gb, pct in disk_free():
        alarm = " <== 报警：车道导出口会先吃掉这里" if (isinstance(free_gb, float) and free_gb < 8.0) else ""
        out.append("  磁盘 %s free=%s GB used=%s%%%s" % (d, free_gb, pct, alarm))
    st = stalled_lanes()
    if st:
        for nm, id8, idle, tool in st:
            out.append("  弹窗停摆? %s(%s) 最后一条 tool_use=%s 无 result，已 %s 分钟 ⇒ 敲门解不开，需人工"
                       % (nm, id8, tool, idle))
    else:
        out.append("  弹窗停摆扫描：无（>=15 分钟无新记录且末条是未应答 tool_use 的车道 = 0 条）")
    out.append(run("quota_now.py").rstrip())
    inbox = run("inbox_check.py", "--sla", "20")
    for ln in inbox.splitlines():
        if "积压分类" in ln or "反控" in ln or "DOOR-BYPASSED" in ln or "尺=" in ln:
            out.append("  " + ln.strip())
    for ln in inbox.splitlines():
        if "BLOCK_GREEN_BUT_BOLTED" in ln or "BLOCK_GREEN " in ln:
            out.append("  " + ln.strip()[:190])
    tip = None
    r = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                        "ls-remote", "origin", AUTH_REF], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    parts = (r.stdout or "").split()
    if parts and re.match(r"^[0-9a-f]{40}$", parts[0]):
        tip = parts[0]
    if tip is None:
        out.append("  TIP-READ rc=%d 无 40 位（不把「线停了」当成结论）%s" % (r.returncode, (r.stderr or "")[:80]))
    else:
        moved = "moved" if (s.get("last_tip") and s["last_tip"] != tip) else "same as 上一轮"
        out.append("  tip=%s (%s) 上一轮=%s" % (tip[:12], moved, (s.get("last_tip") or "-")[:12]))
        s["last_tip"] = tip
    wake = run("wake_from_commits.py")
    out.append("  " + (wake.strip().splitlines() or ["(wake 无输出)"])[-1][:200])
    rel = run("relay.py", "--list")
    keep = [l for l in rel.splitlines() if "要转达" in l or "candidates=" in l or "本轮没有" in l]
    for l in keep[-6:]:
        out.append("  " + l.strip()[:200])
    proc = len(glob.glob(os.path.join(r"D:\moodle\_qoder_ledger_inbox", "_processed", "*")))
    out.append("  _processed=%d  inbox_root=%d" % (proc, len(glob.glob(os.path.join(
        r"D:\moodle\_qoder_ledger_inbox", "*.md")))))
    save(s)
    txt = "\n".join(out) + "\n"
    print(txt)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
