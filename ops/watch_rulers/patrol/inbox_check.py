"""账本收件箱积压哨兵。

23:07 起 LEDGER_SINGLE_WRITER_V1：车道不再直接写账本，改成把块丢进
`D:\\moodle\\_qoder_ledger_inbox\\<lane>_<HHMM>.md`，由号令者跑
`ledger_inbox_apply_r1.py --apply` 代插（他自己承诺 <=15 分钟一轮）。
⇒ **协调链出现了一个唯一瓶颈**：他一旦睡着或卡住，车道的交付就永远进不了账本，
  后面的验收、派单、裁决全部停摆，而且从车道落盘看是"正常"的。

判据：根目录里存在 mtime 早于 (now - SLA_MIN) 的 `.md` ⇒ INBOX_BACKLOG。
已处理件会被改名成 `*.inserted_*` 移进 `_processed`，所以只数根目录。

09-28 05:06 改版（我自己那条误读）：光看 mtime 会把「块被写盘门拒了」误报成「号令者没及时代插」。
现在每枚积压块都过一遍**写盘门自己那一枚尺**（`claim_coordinate_check_r4e.py`，即
`ledger_insert_after.py:28` 调的那枚），按门的原判分类：
  RED   ⇒ 归车道（要重切补坐标），不该催号令者插
  GREEN + 第二道闸干净 ⇒ 归号令者（真的在等代插）
  GREEN + 第二道闸 abort ⇒ 归车道（09-28 19:31 改版：门绿只代表 Q43 那枚尺放行，写盘工还有坐标可取回闸，
    19:24 实测收件目录 5 枚门绿块全卡在那一道，把它们算成「号令者压着」是错的）
尺坏了怎么排除：每轮拿一枚**已入账**的块当反控回跑同一枚尺，必须 GREEN。
`--no-door` 可以只要积压计数（快，但不分类）；`--no-bolt` 只跑第一道闸。

用法：python inbox_check.py [--sla 20] [--no-door] ;  python inbox_check.py --selftest
"""
import glob
import hashlib
import io
import os
import re
import subprocess
import sys
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
SLA_MIN = 20.0
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
# 尺名不再写死：从「真正在跑的写盘门」那件里读出来（19:40 实测：账本 L17517 已把门换到
# `ledger_inbox_apply_r2.py` + `ledger_insert_after_r2.py`，它调的是 r7；而车道被告知跑的仍是 r4e。
# 我照 r4e 判就会把 r7-GREEN 的块读成「门拒了却入账」——19:38 我就这样误报过一次，所以这里改成派生。）
DOOR_FILES = ["ledger_insert_after_r2.py", "ledger_insert_after.py"]
DOOR_FALLBACK = "claim_coordinate_check_r4e.py"


def live_ruler():
    """Return (ruler_file_name, source_path, source_line) read from the door that is actually in use."""
    for df in DOOR_FILES:
        p = os.path.join(LC, df)
        if not os.path.exists(p):
            continue
        for i, ln in enumerate(io.open(p, encoding="utf-8", errors="replace").read().splitlines(), 1):
            m = re.search(r'"(claim_coordinate_check_r[0-9a-z]*\.py)"', ln)
            if m:
                return m.group(1), p, i
    return DOOR_FALLBACK, None, None


DOOR, DOOR_SRC, DOOR_SRC_LINE = live_ruler()


def door_verdict(path, timeout=300):
    """跑写盘门本身，返回 (rc, findings 数, 门打印的 GREEN/RED 串)。只读，不碰账本。"""
    try:
        r = subprocess.run([sys.executable, os.path.join(LC, DOOR), "--text", path, "--expect-clean"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
    except Exception as e:
        return None, None, "DOOR_ERROR " + type(e).__name__
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"Q43_GATE_(GREEN|RED)", out)
    n = len(re.findall(r"^\s*line \d+ \w+ \w+ \|", out, re.M))
    return r.returncode, n, ("Q43_GATE_" + m.group(1)) if m else ("rc=%d 无 overall 行" % r.returncode)


def control_verdict(newest=8):
    """反控：拿已经入账的块跑同一枚尺。

    09-28 19:35 改版：只拿「最新那一枚」当反控是错的——19:24 有块在门拒（rc=3）的情况下仍然进了账本，
    于是反控读到 RED，整轮分类被作废，监视器反而瞎了。现在往前扫 newest 枚，取第一枚 GREEN 的当反控，
    同时把「已入账却被门拒」的块单独列出来（那是写盘门被绕过或门与尺不同代的信号，本身就是要报的事）。
    """
    cand = sorted(glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")),
                  key=lambda p: -os.path.getmtime(p))[:newest]
    red = []
    good = None
    for p in cand:
        rc, n, tag = door_verdict(p)
        if rc is None:
            continue
        if rc == 0:
            if good is None:
                good = (os.path.basename(p), rc, n, tag)
        else:
            red.append("%s(rc=%d findings=%s)" % (os.path.basename(p), rc, n))
    # 扫完 newest 枚而不是找到第一枚 GREEN 就停：绕过门的块通常就混在最新几枚里，早停会让它隐形。
    if good:
        return good[0], good[1], good[2], good[3], red
    if red:
        return None, 3, None, "NO_GREEN_CONTROL_AMONG_%d" % len(cand), red
    return None, None, None, "NO_PROCESSED_BLOCK", red



def scan(now=None, sla=SLA_MIN):
    now = now if now is not None else time.time()
    if not os.path.isdir(INBOX):
        return [], "INBOX_MISSING", 0
    files = [f for f in glob.glob(os.path.join(INBOX, "*.md"))]
    stale = [(f, (now - os.path.getmtime(f)) / 60.0) for f in files]
    over = [(f, a) for f, a in stale if a >= sla]
    over.sort(key=lambda x: -x[1])
    status = "BACKLOG" if over else ("IDLE" if not files else "FRESH")
    return over, status, len(files)


def selftest():
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_inbox_selftest")
    os.makedirs(tmp, exist_ok=True)
    old = os.path.join(tmp, "old.md")
    fresh = os.path.join(tmp, "fresh.md")
    open(old, "w").write("x")
    open(fresh, "w").write("y")
    past = time.time() - 3600
    os.utime(old, (past, past))
    global INBOX
    keep = INBOX
    cases = []
    try:
        INBOX = tmp
        o, s, n = scan(sla=20.0)
        cases.append(("正控 有一枚 60 分钟前的块 -> BACKLOG", s == "BACKLOG" and len(o) == 1, True))
        os.remove(old)
        o, s, n = scan(sla=20.0)
        cases.append(("反控 只有新鲜块 -> 不报", s == "FRESH" and len(o) == 0, True))
        os.remove(fresh)
        o, s, n = scan(sla=20.0)
        cases.append(("反控 空收件箱 -> IDLE 不报", s == "IDLE" and len(o) == 0, True))
    finally:
        INBOX = keep
        for f in (old, fresh):
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
    bad = 0
    for name, got, want in cases:
        ok = (got == want)
        print("  %-40s got=%s %s" % (name, got, "OK" if ok else "FAIL"))
        bad += 0 if ok else 1
    print("selftest %s (%d/%d)" % ("PASS" if bad == 0 else "FAIL", len(cases) - bad, len(cases)))
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    sla = SLA_MIN
    if "--sla" in sys.argv:
        sla = float(sys.argv[sys.argv.index("--sla") + 1])
    over, status, n = scan(sla=sla)
    proc = len(glob.glob(os.path.join(INBOX, "_processed", "*")))
    use_door = "--no-door" not in sys.argv
    print("[%s] inbox root=%d 待处理, _processed=%d, 状态=%s (SLA=%.0f 分钟)" % (
        time.strftime("%H:%M:%S"), n, proc, status, sla))
    print("   尺=%s  sha1=%s  派生自 %s" % (
        DOOR, hashlib.sha1(io.open(os.path.join(LC, DOOR), "rb").read()).hexdigest()[:12],
        ("%s:%d" % (DOOR_SRC, DOOR_SRC_LINE)) if DOOR_SRC else "FALLBACK（没从门件里读到尺名）"))
    if not use_door:
        for f, a in over:
            print("   INBOX_BACKLOG %s 已等 %.1f 分钟（本轮没跑门，不判归谁）" % (os.path.basename(f), a))
        return 1 if over else 0
    cname, crc, cn, ctag, cred = control_verdict()
    print("   反控（已入账块跑同一枚尺）：%s rc=%s %s findings=%s ⇒ %s"
          % (cname, crc, ctag, cn, "尺可信" if crc == 0 else "尺或环境异常，本轮分类作废"))
    if cred:
        print("   DOOR-BYPASSED %d 枚块「门拒了但仍已入账」（近 %d 枚里）：%s"
              % (len(cred), 8, "; ".join(cred)))
        print("      ⇒ 要么写盘时带了 --allow-ungated，要么车道直接写了账本；两种都要号令者判，本轮分类照跑"
              "（反控另有 GREEN 块，尺本身仍可信）。")
    if crc != 0:
        # 反控不绿就说明这枚尺此刻不可信；拿它判「归车道还是归号令者」会冤枉人，所以退回不判归谁。
        for f, a in over:
            print("   INBOX_BACKLOG %s 已等 %.0f 分钟（反控非 GREEN，本轮不判归谁）" % (os.path.basename(f), a))
        return 1 if over else 0
    red = green = bolted = 0
    try:
        import bolt_replica as BR
    except Exception as e:
        BR = None
        print("   BOLT-SKIP 第二道闸本轮没跑（导入 bolt_replica 失败：%s）⇒ 门绿一律不判归号令者" % e)
    for f, a in over:
        rc, cnt, tag = door_verdict(f)
        if tag == "Q43_GATE_RED":
            red += 1
            print("   BLOCK_RED   %s 已等 %.0f 分钟，门 RED / findings=%s ⇒ 归车道：补同行坐标后另投新块"
                  % (os.path.basename(f), a, cnt))
        elif tag == "Q43_GATE_GREEN":
            # 门绿不等于能插。写盘工还带第二道闸（ledger_insert_after.py:94-109）：块里每一枚 40 位坐标必须
            # 能 cat-file；否则那一行要同时（a）声明它不是 git 对象，（b）同段里有一枚真能取回的坐标。
            # 19:24 实测：收件目录 5 枚门绿块 5 枚都卡在这一闸，0 枚是号令者能代插的——把「门绿」直接读成
            # 「号令者压着没插」会冤枉人，所以这里先复算那道闸再判归谁。
            ab = []
            if BR is not None and "--no-bolt" not in sys.argv:
                try:
                    _q, ab, _c, _n = BR.evaluate(f)
                except Exception as e:
                    print("   BOLT-ERR  %s 第二道闸复算失败：%s ⇒ 本轮不判归谁" % (os.path.basename(f), e))
                    ab = None
            if ab is None:
                print("   BLOCK_UNKNOWN %s 已等 %.0f 分钟（第二道闸没读数）" % (os.path.basename(f), a))
            elif ab:
                bolted += 1
                print("   BLOCK_GREEN_BUT_BOLTED %s 已等 %.0f 分钟，门绿 / 第二道闸 abort=%d ⇒ 归车道：%s"
                      % (os.path.basename(f), a, len(ab),
                         "; ".join("L%d %s declared=%s anchored=%s" % (ln, t[:12], d, anc) for ln, t, d, anc in ab[:3])))
            else:
                green += 1
                print("   BLOCK_GREEN %s 已等 %.0f 分钟，门绿 + 第二道闸干净 ⇒ 归号令者：真的在等代插（承诺 <=15 分钟）"
                      % (os.path.basename(f), a))
        else:
            print("   BLOCK_%s %s 已等 %.0f 分钟（门没给可读判语：%s）" % ("UNKNOWN", os.path.basename(f), a, tag))
    print("   积压分类：门拒 %d 枚 / 门绿但第二道闸拒 %d 枚 / 门绿真能插 %d 枚（尺 %s）" % (red, bolted, green, DOOR))
    return 1 if (over or green) else 0



if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
