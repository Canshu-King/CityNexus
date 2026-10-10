# -*- coding: utf-8 -*-
"""终值单第 2 格的本地 git 补件：权威尖、窗口内逐笔提交、复算命令，一次跑齐。

为什么要脚本化：10-01 23:00 那一档 API 侧 `IncompleteRead`，第 2 格是我**手敲 git 现补**的——
夜里十点靠即兴，格式会漂、证据会少一行。今晚（10-02）这一格必须是**一条命令**。
每一格都要有出处；任何一步取不到就整件拒发，不许用记忆里的尖填坑。
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

REPO = r"D:\moodle\CityNexus"
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="", GIT_TERMINAL_PROMPT="0")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
DATE = os.environ.get("NIGHT_DATE", time.strftime("%Y-%m-%d"))
FRM = os.environ.get("NIGHT_FROM", "18:00")
TO = os.environ.get("NIGHT_TO", "23:00")
SINCE = "%s %s" % (DATE, FRM)
UNTIL = "%s %s" % (DATE, TO)


def sh(args, t=300):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    fails = []
    rc_l, out_l = sh(["git", "ls-remote", "origin", TIPREF])
    m = re.match(r"^([0-9a-f]{40})\s", out_l.strip() or " ")
    tip = m.group(1) if m else ""
    if rc_l != 0 or not tip:
        fails.append(u"ls-remote 取不到现尖（rc=%d，输出前 120：%s）" % (rc_l, out_l[:120]))
        tip = ""
    rc_f, out_f = sh(["git", "fetch", "origin", TIPREF], t=600)
    # 基准就用远端现读那枚 40 位本身：FETCH_HEAD 在只取单一 refspec 时不一定存在（128 实测），
    # 而 refs/remotes/origin/<枝> 又可能是别人上一轮的旧尖——两者都不如「先把这枚对象取到本地」可靠。
    base = tip if tip else ""
    if base:
        rc_e, _oe = sh(["git", "cat-file", "-e", base + "^{commit}"])
        if rc_e != 0:
            rc_f2, out_f2 = sh(["git", "fetch", "origin", base], t=600)
            rc_e, out_e = sh(["git", "cat-file", "-e", base + "^{commit}"])
            if rc_e != 0:
                fails.append(u"取不到本地对象 %s（fetch rc=%d%r、%d%%）" % (base[:12], rc_f2, (out_f2 or "")[:150], rc_e))
    rc_c, out_c = sh(["git", "rev-parse", base]) if base else (1, "")
    got = (out_c or "").strip()
    if base and rc_c != 0:
        fails.append(u"本地解不开这枚尖（rc=%d）" % rc_c)
    rc_n, out_n = sh(["git", "rev-list", "--count", "--since=%s" % SINCE, "--until=%s" % UNTIL, base]) if base else (1, "")
    n = (out_n or "").strip()
    rc_g, out_g = sh(["git", "log", "--since=%s" % SINCE, "--until=%s" % UNTIL,
                      "--format=%h %ad %s", "--date=format:%H:%M:%S", base])
    rows = [l.strip() for l in (out_g or "").splitlines() if l.strip()]
    if rc_n != 0 or not n.isdigit():
        fails.append(u"窗口内提交计数取不到（rc=%d）" % rc_n)
    if rc_g != 0:
        fails.append(u"逐笔清单取不到（rc=%d）" % rc_g)
    elif n.isdigit() and len(rows) != int(n):
        fails.append(u"计数 %s 与逐笔行数 %d 不一致 ⇒ 清单没收齐" % (n, len(rows)))
    if fails:
        print(u"REFUSE %d 条：" % len(fails))
        for x in fails:
            print(u"   - " + x)
        return 1

    now = time.strftime("%H:%M:%S")
    per = u" ／ ".join(r.split(" ")[0] + " " + r.split(" ")[1] for r in rows[:12]) or u"（窗口内 0 笔）"
    lines = []
    lines.append(u"_night_tipfix_%s_%s.txt · 补第 2 格（终值单那格若 API 侧 IncompleteRead，就用这件）于 %s" % (
        time.strftime("%m%d", time.strptime(DATE, "%Y-%m-%d")), TO.replace(":", ""), now))
    lines.append(u"[1] 远端现尖 %s（ls-remote 现读；fetch rc=%d，本地 %s=%s）" % (
        tip, rc_f, base, got[:12]))
    lines.append(u"[2] %s→%s 这一窗内该枝上的提交 %s 笔" % (FRM, TO, n))
    lines.append(u"[3] 逐笔：%s" % per)
    lines.append(u"[4] 尖那笔的说明：%s" % (rows[0] if rows else u"（窗口内无提交）"))
    lines.append(u"[5] 复算：git -C D:/moodle/CityNexus ls-remote origin %s；"
                 u"git -C D:/moodle/CityNexus log --since='%s' --until='%s' --format='%%h %%ad %%s' --date=format:'%%H:%%M:%%S' %s" % (
                     TIPREF, SINCE, UNTIL, base))
    out = u"\n".join(lines) + u"\n"
    p = os.path.join(HERE, u"_night_tipfix_%s_%s.txt" % (
        time.strftime("%m%d", time.strptime(DATE, "%Y-%m-%d")), TO.replace(":", "")))
    io.open(p, "w", encoding="utf-8", newline="\n").write(out)
    print(out, end="")
    b = out.encode("utf-8")
    print(u"[落盘 %s｜%d B｜sha1 %s]" % (os.path.basename(p), len(b), hashlib.sha1(b).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
