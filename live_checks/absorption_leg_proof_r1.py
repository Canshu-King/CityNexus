# -*- coding: utf-8 -*-
"""ORD-0592 proof driver: run the absorption leg and its mount end to end, in a temp dir only.

Why this file exists: an instrument that was only ever described is not delivered.  This driver replays
every claim the delivery block makes -- the leg's own assertions, a live read of the ruler at the tip,
the grow/regress/cooldown decisions, the negative control that a block without coordinates cannot reach
the inbox, the mount's byte-identity and compile check, and the shipped leg block executed through the
landing loop's own run() so the call shape is proved, not asserted.

Nothing here writes into the shared ledger, the real inbox, the live loop file or the authoritative
line: state dir, inbox and the loop file are all temp copies.
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
LEG = os.path.join(HERE, "patrol", "_absorption_leg_r1.py")
MOUNTER = os.path.join(HERE, "mount_absorption_leg_r1.py")
LIVE_LOOP = os.environ.get("CNX_PROOF_LOOP", r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_auto_land_loop_r1.py")
BARE = os.environ.get("CNX_PROOF_REPO", "D:/moodle/CityNexus")
MIRROR = "refs/heads/mirror/integration-frontend-apple-pass1"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def head(*t):
    print("\n" + "=" * 78)
    print((" ".join(x for x in t)))
    print("=" * 78)


def main():
    tmp = tempfile.mkdtemp(prefix="absorb_proof_")
    deploy = os.path.join(tmp, "live_checks")
    os.makedirs(os.path.join(deploy, "patrol"))
    shutil.copyfile(LEG, os.path.join(deploy, "patrol", "_absorption_leg_r1.py"))
    # the write-door bolt the leg calls, and the ruler it runs, come from the real places: copy the
    # self-check next to the leg so the leg's own path logic is what gets exercised.
    for f in ("block_selfcheck_r1.py", "claim_coordinate_check_r7.py"):
        src = os.path.join(HERE, f)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(deploy, f))
    state = os.path.join(tmp, "state")
    inbox = os.path.join(tmp, "inbox")
    os.makedirs(state)
    os.makedirs(inbox)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", CNX_ABSORB_STATE_DIR=state, CNX_ABSORB_INBOX=inbox)

    leg = load(LEG, "legmod")
    leg.STATE_DIR = state
    leg.INBOX = inbox

    head("1 尺自己的自检（leg --selftest）")
    r = subprocess.run([sys.executable, LEG, "--selftest"], capture_output=True, env=env, timeout=600)
    for ln in (r.stdout or b"").decode("utf-8", "replace").strip().splitlines()[-3:]:
        print(" ", ln)
    print("  exit=%d" % r.returncode)

    head("2 真跑一拍 --dry（不写盘）")
    r = subprocess.run([sys.executable, LEG, "--round", "p1"], capture_output=True, env=env, timeout=900)
    print((r.stdout or b"").decode("utf-8", "replace").strip())
    print("  exit=%d｜状态目录里有几枚文件：%d" % (r.returncode, len(os.listdir(state))))

    head("3 真跑一拍 --apply（状态件应落下带日期的一行）")
    r = subprocess.run([sys.executable, LEG, "--round", "p2", "--apply"], capture_output=True,
                       env=env, timeout=900)
    print((r.stdout or b"").decode("utf-8", "replace").strip())
    dated = [f for f in sorted(os.listdir(state)) if f.startswith("_absorption_state_")]
    print("  状态件：%s" % (dated or "（没写出来 = 这条腿没干活）"))
    if dated:
        for ln in io.open(os.path.join(state, dated[0]), encoding="utf-8").read().splitlines():
            print("   |", ln.replace("\t", " | "))

    head("4 面涨了：种一行「上一拍 40 条」再跑，应报警并把带坐标的块交进临时收件口")
    p = os.path.join(state, dated[0])
    rows = io.open(p, encoding="utf-8").read().splitlines()
    seed = rows[0].replace("时间戳", "20260101 00:00:00") if False else \
        "20260101 00:00:00\tseed\t" + "0" * 12 + "\t4\t41\t1\t40\t34\t6\t0\t推进中"
    io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(rows + [seed]) + "\n")
    r = subprocess.run([sys.executable, LEG, "--round", "p3", "--apply"], capture_output=True,
                       env=env, timeout=900)
    print((r.stdout or b"").decode("utf-8", "replace").strip())
    posted = [f for f in sorted(os.listdir(inbox)) if f.endswith(".md")]
    print("  临时收件口：%s" % (posted or "（空）"))
    if posted:
        body = io.open(os.path.join(inbox, posted[0]), encoding="utf-8").read().splitlines()
        print("  交出去的块头 8 行：")
        for ln in body[:8]:
            print("    " + ln[:150])

    head("5 冷却：同一形状的块不重交（先把「上一拍 40 条」那行种回末位，让判语仍是面涨了）")
    rows = io.open(p, encoding="utf-8").read().splitlines()
    seed2 = "20260101 00:00:01\tseed2\t" + "0" * 12 + "\t4\t41\t1\t40\t34\t6\t0\t推进中"
    io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(rows + [seed2]) + "\n")
    r = subprocess.run([sys.executable, LEG, "--round", "p4", "--apply"], capture_output=True,
                       env=env, timeout=900)
    for ln in (r.stdout or b"").decode("utf-8", "replace").strip().splitlines():
        print("  " + ln[:200])
    print("  临时收件口仍是 %d 块（同形状不重交）" % len([f for f in os.listdir(inbox) if f.endswith(".md")]))

    head("6 负对照：一块没有坐标的件过不了写门")
    rc_, kind = leg.post(u"### 故意没坐标的一块\n\n未吸收面涨了 5 条。\n", "9998", True)
    print("  post 返回 rc=%s kind=%s" % (rc_, kind))
    print("  收件口现在：%s" % sorted(os.listdir(inbox)))

    head("7 退化那一拍：绕过冷却，且尺没给的分档写「尺未报」而不是猜零")
    m2 = load(LEG, "legmod2")
    m2.STATE_DIR = os.path.join(tmp, "state2")
    m2.INBOX = os.path.join(tmp, "inbox2")
    os.makedirs(m2.STATE_DIR)
    os.makedirs(m2.INBOX)
    io.open(m2.state_path(), "w", encoding="utf-8", newline="\n").write(
        "时间戳\t拍号\t权威尖\t尺退出码\t表内枝数\t已挂吸收代\t未吸收\tTO_ABSORB\tCARRIED_BY_REP\t枝对象取不到\t判语\n"
        "20260101 00:00:00\tp0\t" + "0" * 12 + "\t4\t41\t0\t41\t35\t6\t0\t推进中\n")
    io.open(m2.cstate_path(), "w", encoding="utf-8", newline="").write(json.dumps(
        {"sig": u"面涨了|x", "sig_at": __import__("time").time(), "names": []}, ensure_ascii=False))
    reg = (u"CHECK 对账表 41 枚枝 | 已挂吸收代 3 | 未吸收 38 | 枝对象取不到 0\n"
           u"CHECK 退化：gpt/revolution-r33-open-world-journey-adaptation:吸收代不在权威线上\n")
    m2.run_ruler = lambda tip: (9, reg, u"")
    sys.argv = ["leg", "--round", "p5", "--apply"]
    m2.main()
    got = [f for f in sorted(os.listdir(m2.INBOX)) if f.endswith(".md")]
    print("  退化那拍的块：%s" % (got or "（没交 = 报警被吞）"))
    if got:
        for ln in io.open(os.path.join(m2.INBOX, got[0]), encoding="utf-8").read().splitlines():
            if u"按 verdict 分" in ln or u"尺退出码" in ln or ln.startswith("- "):
                print("    " + ln[:150])

    head("8 挂载件：锚、字节等式、可编译、幂等（只动临时副本，绝不碰跑批本体）")
    copy_loop = os.path.join(tmp, "loop_copy.py")
    shutil.copyfile(LIVE_LOOP, copy_loop)
    before = len(io.open(copy_loop, encoding="utf-8").read().splitlines())
    menv = dict(env, CNX_MOUNT_LOOP=copy_loop)
    for tag in ("", "--apply", "--apply"):
        r = subprocess.run([sys.executable, MOUNTER] + ([tag] if tag else []),
                           capture_output=True, env=menv, timeout=600)
        print("  [%s] exit=%d %s" % (tag or "DRY", r.returncode,
                                     (r.stdout or b"").decode("utf-8", "replace").strip().replace("\n", " ⏎ ")[:300]))
    after = len(io.open(copy_loop, encoding="utf-8").read().splitlines())
    print("  行数 %d 到 %d（+%d）；原件行数现在=%d（应仍为 %d）" % (
        before, after, after - before,
        len(io.open(LIVE_LOOP, encoding="utf-8").read().splitlines()), before))

    head("9 挂载块经跑批自己的 run() 真跑一拍（证的是调用形制，不是我抄的一份）")
    mm = load(MOUNTER, "mounter")
    lp = load(copy_loop, "loop_copy")
    lp.LC = deploy
    logs = []
    lp.log = lambda msg: logs.append(msg)
    body = textwrap.dedent(mm.DELTA.strip("\n"))
    src = "def _probe():\n" + "".join("    " + l + "\n" for l in body.split("\n"))
    ns = {"run": lp.run, "PY": lp.PY, "os": lp.os, "i": 99, "log": lp.log, "LC": deploy}
    exec(compile(src, "delta_probe", "exec"), ns)
    ns["_probe"]()
    for l in logs:
        print("  LOG: " + l[:240])
    rows2 = [f for f in sorted(os.listdir(deploy)) if False]
    patrol_out = [f for f in sorted(os.listdir(os.path.join(deploy, "patrol")))
                  if f.startswith("_absorption_state")]
    print("  这条腿在部署预览里写出的状态件：%s" % (patrol_out or "（无）"))
    if patrol_out:
        print("   最后一行：" + io.open(os.path.join(deploy, "patrol", patrol_out[-1]),
                                        encoding="utf-8").read().splitlines()[-1])

    head("10 收尾：现场都在临时目录，随本次一起清掉")
    print("  tmp=%s" % tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    print("  清完还在=%s" % os.path.isdir(tmp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
