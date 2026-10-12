# -*- coding: utf-8 -*-
"""ORD-0592 leg: run the revolution-absorption ruler once per landing round and keep the面 on disk.

Why the leg reads the ruler and the manifest from the authoritative tip instead of from this working
tree: measured at 20:33 tonight -- this tooling worktree is a checkout of e9efec6bf (09-21 18:31), so
`docs/REVOLUTION_ABSORPTION_MANIFEST.tsv` does not exist next to it and `live_checks/
revolution_absorption_check_r1.py` is not there either.  Running the local copy would therefore return
the ruler's own exit 3 (数据取不到) every single round and look like a working instrument.  Same
discipline the landing door already uses for the codes-on-screen gate: take the bytes from the tip so a
stale local copy can never pass what the current ruler refuses.

What one round does:
  1. take the live tip; read the ruler's bytes and the manifest's bytes at that tip into a scratch dir;
  2. run the ruler (its own code, unmodified) and parse the lines it prints;
  3. append one row to a dated state file `_absorption_state_YYYYMMDD.tsv` -- this is the deliverable
     the order asks for ("把未吸收面写进带日期的状态文件"), and it is written every round, green or red;
  4. compare with the previous round's stored reading: a grown unabsorbed surface, a lost absorbed-on
     marker, an unresolvable branch object, exit 9 (退化) or exit 3 (取不到数) become an escalation block
     that carries the CAUSE (which branch, which manifest line, what the ruler said) -- not one log line;
  5. the escalation is bolted to its own write door: the block must come back GREEN from the same
     self-check the ledger applier runs, otherwise it is moved aside as `.gate_red` and never reaches
     the inbox.  A cooldown (default 240 min) stops the same reading from being re-posted every round;
     a NEW worse signature bypasses it, because sitting on a regression for four hours is the failure.

Nothing here moves the authoritative line, judges a candidate, or writes the ledger itself.
Exit codes of this leg: 0 = ran (whether or not it posted), 2 = instrument could not read anything.
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))            # .../live_checks/patrol
LC = os.path.dirname(HERE)                                   # .../live_checks
BARE = os.environ.get("CNX_ABSORB_REPO", "D:/moodle/CityNexus")
MIRROR_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
RULER_IN_LINE = "live_checks/revolution_absorption_check_r1.py"
MANIFEST_IN_LINE = "docs/REVOLUTION_ABSORPTION_MANIFEST.tsv"
STATE_DIR = os.environ.get("CNX_ABSORB_STATE_DIR", HERE)
INBOX = os.environ.get("CNX_ABSORB_INBOX", r"D:\moodle\_qoder_ledger_inbox")
SELFCHECK = os.path.join(LC, "block_selfcheck_r1.py")
COOL_MIN = float(os.environ.get("CNX_ABSORB_COOL_MIN", "240"))
TIPRE = re.compile(r"^[0-9a-f]{40}$")


def scratch_dir():
    d = os.path.join(LC, "_absorption_scratch")
    for sub in ("live_checks", "docs"):
        p = os.path.join(d, sub)
        if not os.path.isdir(p):
            os.makedirs(p)
    return d


def git_show_tip(tip, rel):
    p = subprocess.run(["git", "-C", BARE, "show", "%s:%s" % (tip, rel)], capture_output=True, timeout=300)
    if p.returncode:
        return None
    return p.stdout


def live_tip():
    p = subprocess.run(["git", "-C", BARE, "ls-remote", "origin", MIRROR_REF],
                       capture_output=True, timeout=300)
    for ln in (p.stdout or b"").decode("utf-8", "replace").splitlines():
        if ln.rstrip().endswith(MIRROR_REF):
            sha = ln.split()[0].strip()
            if TIPRE.match(sha):
                return sha
    return ""


def resolvable(sha):
    if not sha or not TIPRE.match(sha):
        return False
    return subprocess.run(["git", "-C", BARE, "cat-file", "-e", sha + "^{commit}"],
                          capture_output=True, timeout=180).returncode == 0


def run_ruler(tip):
    """Take the ruler's own bytes and the manifest's own bytes at that tip, then run them.

    Returns (rc, stdout, why).  rc is None only when the instrument could not be laid down at all --
    that is an instrument failure and is reported as such, never as 'the surface is fine'.
    """
    d = scratch_dir()
    ruler = git_show_tip(tip, RULER_IN_LINE)
    if ruler is None:
        return None, "", u"尖上取不到尺字节 %s" % RULER_IN_LINE
    manifest = git_show_tip(tip, MANIFEST_IN_LINE)
    if manifest is None:
        return None, "", u"尖上取不到对账表 %s" % MANIFEST_IN_LINE
    rp = os.path.join(d, "live_checks", "revolution_absorption_check_r1.py")
    mp = os.path.join(d, "docs", "REVOLUTION_ABSORPTION_MANIFEST.tsv")
    io.open(rp, "wb").write(ruler)
    io.open(mp, "wb").write(manifest)
    p = subprocess.run([sys.executable, rp], capture_output=True, timeout=900,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", CNX_WORK_REPO=BARE))
    out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    return p.returncode, out, ""


NUM = r"(\d+)"
RE_HEAD = re.compile(u"权威尖 ([0-9a-f]{12})")
RE_COUNT = re.compile(u"对账表 " + NUM + u" 枚枝 \\| 已挂吸收代 " + NUM + u" \\| 未吸收 " + NUM
                      + u" \\| 枝对象取不到 " + NUM)
RE_SPLIT = re.compile(u"TO_ABSORB " + NUM + u"｜CARRIED_BY_REP " + NUM)
RE_REGRESS = re.compile(u"CHECK 退化：(.+)")
RE_LOST = re.compile(u"需按表内 sha 从远端救回：(.+)")
RE_CLOSED = re.compile(u"对账闭合")


def parse(out):
    v = {"rows": -1, "absorbed": -1, "unabsorbed": -1, "lost": -1,
         "to_absorb": -1, "carried": -1, "regress": "", "rescued": "", "closed": False}
    m = RE_COUNT.search(out)
    if m:
        v["rows"], v["absorbed"], v["unabsorbed"], v["lost"] = (int(x) for x in m.groups())
    m = RE_SPLIT.search(out)
    if m:
        v["to_absorb"], v["carried"] = int(m.group(1)), int(m.group(2))
    m = RE_REGRESS.search(out)
    if m:
        v["regress"] = m.group(1).strip()
    m = RE_LOST.search(out)
    if m:
        v["rescued"] = m.group(1).strip()
    v["closed"] = bool(RE_CLOSED.search(out))
    return v


def fmt(v):
    """-1 means the ruler did not answer that slot on this exit path -- say so, never print a fake zero.

    The ruler returns 9 (退化) before it prints the TO_ABSORB / CARRIED_BY_REP split, so those two slots
    are empty exactly on the regression path.  A leg that dies there swallows the one alarm that matters.
    """
    return str(v) if isinstance(v, int) and v >= 0 else u"尺未报"


def unabsorbed_names():
    """Which branch names sit on the unabsorbed面, and which manifest line each one is on.

    Read off the tip's manifest, so an escalation can name the line a stakeholder has to re-file.
    """
    tip = live_tip()
    raw = git_show_tip(tip, MANIFEST_IN_LINE) if tip else None
    if raw is None:
        return {}, {}, None
    lines = raw.decode("utf-8", "replace").splitlines()
    cols = lines[0].split("\t")
    un, done = {}, {}
    for n, ln in enumerate(lines[1:], 2):
        if not ln.strip():
            continue
        r = dict(zip(cols, ln.split("\t")))
        name = r.get("name", "?")
        (done if (r.get("absorbed_on") or "").strip() else un)[name] = n
    return un, done, tip


def state_path(day=None):
    return os.path.join(STATE_DIR, "_absorption_state_%s.tsv" % (day or datetime.date.today().strftime("%Y%m%d")))


def last_row():
    """The previous round's row: newest dated file, last data line.  None when there is no history."""
    if not os.path.isdir(STATE_DIR):
        return None
    cands = sorted(f for f in os.listdir(STATE_DIR)
                   if f.startswith("_absorption_state_") and f.endswith(".tsv"))
    for f in reversed(cands):
        try:
            body = io.open(os.path.join(STATE_DIR, f), encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        data = [l for l in body if l.startswith("2")]
        if data:
            return f, data[-1]
    return None


def append_row(rec):
    p = state_path()
    new = not os.path.exists(p)
    with io.open(p, "a", encoding="utf-8", newline="") as fh:
        if new:
            fh.write(u"时间戳\t拍号\t权威尖\t尺退出码\t表内枝数\t已挂吸收代\t未吸收\tTO_ABSORB\tCARRIED_BY_REP\t枝对象取不到\t判语\n")
        fh.write(u"\t".join([rec["at"], rec["round"], rec["tip"][:12], str(rec["rc"]), str(rec["rows"]),
                             str(rec["absorbed"]), str(rec["unabsorbed"]), str(rec["to_absorb"]),
                             str(rec["carried"]), str(rec["lost"]), rec["verdict"]]) + u"\n")
    n = len([l for l in io.open(p, encoding="utf-8").read().splitlines() if l.startswith("2")])
    return p, n


def decide(cur, prev, rc):
    """Return (verdict, cause).  Anything the ruler could not answer is escalated, not swallowed."""
    if rc is None or rc == 3:
        return (u"取不到数", u"尺这一拍没拿到数（rc=%s，成因：%s）——不判等于没跑，必须报" % (rc, cur.get("why") or "见尺原话"))
    if rc == 9 or cur["regress"]:
        return (u"退化", u"尺报退化：%s" % (cur["regress"] or "见尺原话"))
    if prev is None:
        return (u"首拍无对照", u"状态件里还没有上一拍的行，这一拍只落账不报警")
    if cur["unabsorbed"] > prev["unabsorbed"]:
        return (u"面涨了", u"未吸收面从 %d 涨到 %d（+ %d 枚）" % (
            prev["unabsorbed"], cur["unabsorbed"], cur["unabsorbed"] - prev["unabsorbed"]))
    if cur["absorbed"] < prev["absorbed"]:
        return (u"面涨了", u"已挂吸收代从 %d 掉到 %d（吸收代被撤回或在权威线上丢了）" % (
            prev["absorbed"], cur["absorbed"]))
    if cur["lost"] > prev["lost"]:
        return (u"对象取不到", u"表里 sha 取不到的枝从 %d 涨到 %d，需按表内 40 位从远端救回" % (
            prev["lost"], cur["lost"]))
    if rc == 0 or cur["closed"]:
        return (u"闭合", u"表内每枚枝都有在权威线上的吸收代，无退化")
    return (u"推进中", u"未吸收面持平在 %s 条（TO_ABSORB %s／CARRIED_BY_REP %s）" % (
        fmt(cur["unabsorbed"]), fmt(cur["to_absorb"]), fmt(cur["carried"])))


def cstate_path():
    return os.path.join(STATE_DIR, "_absorption_cstate.json")


def signature(cur, verdict):
    return "%s|%s|%s|%s|%s" % (verdict, cur["unabsorbed"], cur["absorbed"], cur["lost"], cur["regress"][:60])


def compose_block(rec, cur, prev, un, lines_by_name, selftest=False):
    """The escalation block.  Every number on a line carries that line's own coordinate."""
    tip = rec["tip"]
    day = rec["at"][:8]
    st = "live_checks/patrol/_absorption_state_%s.tsv" % day
    nrow = rec["state_row"]
    moved = []
    if prev is not None and prev.get("names"):
        now = set(un)
        before = set(prev["names"])
        moved = sorted(now - before)[:6]
        gone = sorted(before - now)[:6]
    else:
        before, now, gone = set(), set(un), []
    ver = rec["verdict"]
    head = u"### 加闸工 ORD-0592 腿的报警（%s）：吸收面 %s，成因在下面" % (
        datetime.datetime.now().strftime("%m-%d %H:%M"), ver)
    body = [head, u""]
    if selftest:
        body.append(u"（这一件是 --selftest 造的形状对照件，只在临时目录里，不进收件口。）")
        body.append(u"")
    body += [
        u"跑批第 %s 拍现读，命令原样 `git -C D:\\moodle\\CityNexus ls-remote origin %s`。" % (rec["round"], MIRROR_REF),
        u"",
        u"| 读数 | 值 | 锚 |",
        u"|---|---|---|",
        u"| 权威尖 | %s | %s:%s |" % (tip, st, nrow),
        u"| 表内枝数 | %s 枚 | %s:2 |" % (fmt(cur["rows"]), "docs/REVOLUTION_ABSORPTION_MANIFEST.tsv"),
        u"| 已挂吸收代 | %s 枚 | %s:%s |" % (fmt(cur["absorbed"]), st, nrow),
        u"| 未吸收 | %s 条 | %s:%s |" % (fmt(cur["unabsorbed"]), st, nrow),
        u"| 按 verdict 分 | TO_ABSORB %s 条／CARRIED_BY_REP %s 条 | %s:%s |" % (
            fmt(cur["to_absorb"]), fmt(cur["carried"]), st, nrow),
        u"| 枝对象取不到 | %s 枚 | %s:%s |" % (fmt(cur["lost"]), st, nrow),
        u"| 尺退出码 | %s（语义见 live_checks/revolution_absorption_check_r1.py:9） | %s:%s |" % (
            ("无（尺没跑成）" if rec["rc"] is None else rec["rc"]), st, nrow),
        u"| 这一拍的判语 | %s | %s:%s |" % (ver, st, nrow),
        u"",
    ]
    if cur["regress"]:
        body += [u"退化名单（尺原话，逐枚给它在对账表的行）：", u""]
        for piece in [x.strip() for x in cur["regress"].split(",") if x.strip()][:6]:
            name = piece.split(":", 1)[0].strip()
            ln = lines_by_name.get(name, "?")
            body.append(u"- %s —— 它在对账表里那一行：`docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:%s`" % (piece, ln))
        body.append(u"")
    if moved:
        body += [u"这一拍新落进未吸收面的枝（对照上一拍存的名单）：", u""]
        for name in moved:
            body.append(u"- `%s` 在对账表第 %s 行：`docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:%s`" % (
                name, un.get(name, "?"), un.get(name, "?")))
        body.append(u"上一拍存过而这一拍不在未吸收面里的枝 %d 枚（那是吸收推进，不是报警）" % len(gone))
        body.append(u"")
    body += [
        u"成因怎么读：尺只判两件事——表里每枚枝的 sha 取得到取不到、已声明的吸收代是不是权威尖的祖先。",
        u"所以「面涨了」只有三种来路：有人把某行的 absorbed_on 清空了、那枚吸收代不在权威线上了、",
        u"或表里多了一行还没落。哪一种都由上面那几行坐标指回对账表自己那一行，不必猜。",
        u"",
        u"这条腿每拍都跑一次尺，并把数落进带日期的状态件 {st}（第 {nrow} 行是本拍）；同一形状的块不重交，"
        u"冷却 {cool} 分钟装在腿自己身上（{cj}），判定变了或更坏就立刻再交。".format(
            st=st, nrow=nrow, cool=int(COOL_MIN),
            cj=u"live_checks/patrol/_absorption_cstate.json:1"),
    ]
    return u"\n".join(body) + u"\n"


def post(block, stamp, apply_mode, fname=None):
    """Write the block into the inbox, but only past the same self-check the applier runs."""
    if not apply_mode:
        print(u"DRY｜这一拍本会交一块（未落盘）：")
        print(block)
        return 0, u"dry"
    os.makedirs(INBOX, exist_ok=True)
    out = os.path.join(INBOX, fname or (u"cmdr_absorption_%s.md" % stamp))
    io.open(out, "w", encoding="utf-8", newline="\n").write(block)
    if not os.path.isfile(SELFCHECK):
        os.rename(out, out + u".gate_unreadable")
        print(u"REFUSE｜自查尺取不到（%s）⇒ 块挪成 %s.gate_unreadable，不压进收件口" % (
            SELFCHECK, os.path.basename(out)))
        return 1, u"gate_unreadable"
    p = subprocess.run([sys.executable, SELFCHECK, "--text", out], capture_output=True, timeout=900,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    so = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    first = so.strip().splitlines()[0][:150] if so.strip() else "(空)"
    if p.returncode or u"GREEN" not in so:
        bad = out + u".gate_red"
        os.rename(out, bad)
        print(u"REFUSE｜自查不绿 ⇒ 原稿挪去 %s｜%s" % (os.path.basename(bad), first))
        return 1, u"gate_red"
    print(u"已交：%s｜%d B｜自查绿 %s" % (out, os.path.getsize(out), first))
    return 0, u"posted"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the dated state file and post escalations")
    ap.add_argument("--round", default="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    tip = live_tip()
    if not tip:
        print(u"ABSORB-LEG rc=2 现读权威尖失败 ⇒ 这一拍不判也不落行（不猜）")
        return 2
    rc, rout, why = run_ruler(tip)
    cur = parse(rout)
    cur["why"] = why
    if rc is None:
        cur.update({"rows": -1, "absorbed": -1, "unabsorbed": -1, "lost": -1,
                    "to_absorb": -1, "carried": -1})
    un, lines_by_name, _ = unabsorbed_names()
    hist = last_row()
    prev = None
    if hist and rc is not None:
        f, line = hist
        c = line.split("\t")
        try:
            prev = {"unabsorbed": int(c[6]), "absorbed": int(c[5]), "lost": int(c[9]),
                    "regress": "", "names": []}
            js = cstate_path()
            if os.path.isfile(js):
                prev["names"] = json.loads(io.open(js, encoding="utf-8", errors="replace").read()).get("names", [])
        except (ValueError, IndexError):
            prev = None
    verdict, cause = decide(cur, prev, rc)
    at = datetime.datetime.now().strftime("%Y%m%d %H:%M:%S")
    rec = {"at": at, "round": str(a.round), "tip": tip, "rc": rc, "verdict": verdict,
           "rows": cur["rows"], "absorbed": cur["absorbed"], "unabsorbed": cur["unabsorbed"],
           "to_absorb": cur["to_absorb"], "carried": cur["carried"], "lost": cur["lost"], "cause": cause}
    if a.apply:
        p, nrow = append_row(rec)
        rec["state_row"] = nrow
        print(u"ABS-ROW %s｜%s 行｜未吸收 %s 条（TO_ABSORB %s／CARRIED_BY_REP %s）｜判语=%s" % (
            os.path.basename(p), nrow, fmt(cur["unabsorbed"]), fmt(cur["to_absorb"]),
            fmt(cur["carried"]), verdict))
    else:
        rec["state_row"] = 0
        print(u"DRY ROW（未落盘）｜未吸收 %s 条（TO_ABSORB %s／CARRIED_BY_REP %s）｜判语=%s｜rc=%s" % (
            fmt(cur["unabsorbed"]), fmt(cur["to_absorb"]), fmt(cur["carried"]), verdict, rc))
    print(u"ABS-LEG 权威尖 %s｜尺 rc=%s｜判语=%s｜成因=%s" % (tip[:12], rc, verdict, cause))

    escalate = verdict in (u"取不到数", u"退化", u"面涨了", u"对象取不到")
    js = cstate_path()
    st0 = {}
    if os.path.isfile(js):
        try:
            st0 = json.loads(io.open(js, encoding="utf-8", errors="replace").read())
        except ValueError:
            st0 = {}
    sig = signature(cur, verdict)
    if not escalate:
        st0.update({"names": sorted(un), "last_sig": sig, "last_tip": tip, "last_at": at})
        if a.apply:
            io.open(js, "w", encoding="utf-8", newline="").write(json.dumps(st0, ensure_ascii=False))
        print(u"ABS-QUIET｜这一拍不报警（%s），名单刷进 %s" % (verdict, os.path.basename(js)))
        return 0
    last = float(st0.get("sig_at") or 0)
    same = st0.get("sig") == sig
    if same and last and (time.time() - last) < COOL_MIN * 60.0:
        print(u"ABSORB-COOLED｜同一形状的块 %d 分前交过（冷却 %d 分）⇒ 这一拍不重交；要强制就删 %s" % (
            int((time.time() - last) / 60.0), int(COOL_MIN), os.path.basename(js)))
        return 0
    block = compose_block(rec, cur, prev, un, lines_by_name)
    stamp = datetime.datetime.now().strftime("%H%M")
    rc2, kind = post(block, stamp, a.apply)
    if kind == "posted":
        st0.update({"sig": sig, "sig_at": time.time(), "names": sorted(un),
                    "last_tip": tip, "last_at": at})
        io.open(js, "w", encoding="utf-8", newline="").write(json.dumps(st0, ensure_ascii=False))
    elif kind == "gate_red":
        st0.update({"names": sorted(un)})
        io.open(js, "w", encoding="utf-8", newline="").write(json.dumps(st0, ensure_ascii=False))
        print(u"ABS-LEG 自查红 ⇒ 块没进收件口，成因只在本机 stdout 与状态件里（这是故意的）")
    return rc2


def selftest():
    import tempfile
    import time as _t
    global STATE_DIR, INBOX
    tmp = tempfile.mkdtemp(prefix="absorb_selftest_")
    STATE_DIR = os.path.join(tmp, "patrol")
    INBOX = os.path.join(tmp, "inbox")
    os.makedirs(STATE_DIR)
    A = []

    def ck(name, cond):
        A.append((name, bool(cond)))

    sample = (u"revolution 吸收进度尺 | 权威尖 3446d6f017dc\n"
              u"CHECK 对账表 41 枚枝 | 已挂吸收代 0 | 未吸收 41 | 枝对象取不到 0\n"
              u"CHECK 未吸收面按 verdict 分：TO_ABSORB 35｜CARRIED_BY_REP 6\n")
    v = parse(sample)
    ck("parse counts (41/0/41/0)", (v["rows"], v["absorbed"], v["unabsorbed"], v["lost"]) == (41, 0, 41, 0))
    ck("parse split (35/6)", (v["to_absorb"], v["carried"]) == (35, 6))
    ck("parse exits no regress", v["regress"] == "")

    # 尺在退出码 9 那条出口是先 return 再打 verdict 分档的，所以那两档一定是空的——
    # 这条腿必须在这种情况下照样把块交出去，而不是崩在报警的那一拍。
    v9a = parse(u"CHECK 对账表 41 枚枝 | 已挂吸收代 3 | 未吸收 38 | 枝对象取不到 0\n"
                u"CHECK 退化：gpt/revolution-r33-x:吸收代不在权威线上\n")
    ck("退出码九那拍没有分档行（读成 -1 而不是猜零）", v9a["to_absorb"] == -1 and v9a["carried"] == -1)
    ck("尺未报的写法", fmt(-1) == u"尺未报" and fmt(35) == "35")

    r9 = (u"CHECK 对账表 41 枚枝 | 已挂吸收代 3 | 未吸收 38 | 枝对象取不到 0\n"
          u"CHECK 退化：r33:吸收代不在权威线上, r61:吸收代取不到对象\n")
    v9 = parse(r9)
    ck("parse regress list", u"r33" in v9["regress"])
    ck("rc9 verdict 退化", decide(v9, None, 9)[0] == u"退化")
    ck("rc3 verdict 取不到数", decide(v, None, 3)[0] == u"取不到数")
    ck("rc None verdict 取不到数", decide({"why": u"尖上取不到尺字节"}, None, None)[0] == u"取不到数")
    prev41 = {"unabsorbed": 41, "absorbed": 0, "lost": 0, "regress": "", "names": []}
    ck("same面 不报（推进中）", decide(v, prev41, 4)[0] == u"推进中")
    prev40 = dict(prev41, unabsorbed=40)
    ck("面涨了（40 到 41）", decide(v, prev40, 4)[0] == u"面涨了")
    ck("吸收代掉了也报面涨", decide(v, dict(prev41, absorbed=5), 4)[0] == u"面涨了")
    ck("对象取不到涨了单独报", decide(dict(v, lost=3), dict(prev41, lost=1), 4)[0] == u"对象取不到")
    closed = parse(u"CHECK 对账表 41 枚枝 | 已挂吸收代 41 | 未吸收 0 | 枝对象取不到 0\nCHECK 对账闭合：表内每枚枝都有在权威线上的吸收代，且无退化\n")
    ck("闭合判语", decide(closed, prev41, 0)[0] == u"闭合")
    ck("首拍无对照", decide(v, None, 4)[0] == u"首拍无对照")

    rec = {"at": datetime.datetime.now().strftime("%Y%m%d %H:%M:%S"), "round": "1", "tip": "a" * 40,
           "rc": 4, "verdict": u"面涨了", "cause": u"从 40 涨到 41", "state_row": 1}
    p, n = append_row(dict(rec, rows=41, absorbed=0, unabsorbed=41, to_absorb=35, carried=6, lost=0))
    ck("状态件带日期在文件名里", re.search(r"_absorption_state_\d{8}\.tsv$", p) and n == 1)
    ck("状态件第一行是表头", io.open(p, encoding="utf-8").read().splitlines()[0].startswith(u"时间戳"))
    ck("last_row 取得到刚才那行", (last_row() or (None, ""))[1].split("\t")[6] == "41")

    un = {u"gpt/revolution-r33-x": 29, u"gpt/revolution-r61-y": 33}
    curx = dict(v, regress=u"gpt/revolution-r33-x:吸收代不在权威线上")
    blk = compose_block(rec, curx, {"unabsorbed": 40, "absorbed": 1, "lost": 0, "regress": "",
                                   "names": [u"gpt/revolution-r60-z"]}, un, un)
    ln = [l for l in blk.split(u"\n") if u"未吸收 | 41" in l]
    ck("块里「未吸收」那行自带同行锚", bool(ln) and re.search(r"_absorption_state_\d{8}\.tsv:1", ln[0]))
    ck("退化那枚枝指回它对账表的行", u"REVOLUTION_ABSORPTION_MANIFEST.tsv:29" in blk)
    ck("新落进未吸收面的枝被点名", u"gpt/revolution-r60-z" not in blk.split(u"这一拍新落进")[1].split(u"\n")[2] if u"这一拍新落进" in blk else False)
    ck("尺退出码那行给了语义锚", u"revolution_absorption_check_r1.py:9" in blk)

    # 退出码九那一拍（分档空着）也要能成块，不许崩——这条就是刚才那条 bug 的守门 assertions
    rec9 = dict(rec, rc=9, verdict=u"退化")
    blk9 = compose_block(rec9, v9a, {"unabsorbed": 41, "absorbed": 0, "lost": 0, "regress": "",
                                    "names": []}, un, un)
    ck("退化那拍照样成块", u"未吸收 | 38" in blk9 and u"尺未报" in blk9)
    ck("退化那拍的块自带尺退出码九的语义锚", u"| 尺退出码 | 9（语义见 live_checks/revolution_absorption_check_r1.py:9）" in blk9)
    ck("取不到数那拍也成块（rc=None）", u"尺没跑成" in compose_block(
        dict(rec, rc=None, verdict=u"取不到数"), dict(v9a, rows=-1, absorbed=-1, unabsorbed=-1, lost=-1),
        None, un, un))

    sig = signature(curx, u"退化")
    ck("签名含判语与四数", sig.startswith(u"退化|"))
    ck("同签名带冷却判重", sig == signature(curx, u"退化"))
    t0 = _t.time()
    ck("冷却窗口算得动", (t0 - (t0 - 60)) < COOL_MIN * 60.0)

    os.makedirs(INBOX)
    fake = os.path.join(INBOX, "cmdr_absorption_0000.md")
    io.open(fake, "w", encoding="utf-8", newline="\n").write(u"### 标题\n\n这块没有任何坐标，光说「零条」。\n")
    ck("写门形状：文件名带花名与四点钟点", re.search(r"cmdr_absorption_\d{4}\.md$", fake))
    rc_, kind = post(u"### 一件不该落盘的块\n\n裸数 5 条。\n", u"9999", False)
    ck("DRY 不写盘", kind == u"dry" and not os.path.exists(os.path.join(INBOX, "cmdr_absorption_9999.md")))
    print(u"ABSORB-LEG-SELFTEST assertions=%d failures=%d" % (len(A), len([x for x in A if not x[1]])))
    for name, ok in A:
        if not ok:
            print(u"  FAIL %s" % name)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if not [x for x in A if not x[1]] else 9


if __name__ == "__main__":
    sys.exit(main())
