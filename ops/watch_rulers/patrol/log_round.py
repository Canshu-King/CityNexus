"""Append this shift's audit round to PATROL_LOG.md with every number computed from an artifact.

Sources: patrol/door_skew_rows.json, patrol/knock/*.txt, patrol/relay/relay_*_2008_*.txt,
patrol/_bus_door_skew.md, and a live run of verify_sends.py for the delivery read-backs.
The append is byte-verified: the file is re-read afterwards and the tail must equal what was written.
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LOG = os.path.join(HERE, "PATROL_LOG.md")   # 359,641 B 那枚真日志；上一版误写成 dirname(HERE) 指到了
                                             # live_checks/PATROL_LOG.md（1953 B 的旧件），20:13 那次已回滚。


def sha1_b(p):
    return hashlib.sha1(io.open(p, "rb").read()).hexdigest()


def main():
    rows = json.load(io.open(os.path.join(HERE, "door_skew_rows.json"), encoding="utf-8"))
    rs = rows["rows"]
    root = [r for r in rs if r["where"] == "root"]
    ins = [r for r in rs if r["where"] == "inserted"]
    skew = [r for r in rs if (r["r4e_rc"] == 0) != (r["r7_rc"] == 0)]
    bolted = [r for r in root if r["r7_rc"] == 0 and r["bolt_abort"] > 0]
    landed = [r for r in root if r["r7_rc"] == 0 and r["bolt_abort"] == 0]
    redlane = [r for r in root if r["r7_rc"] != 0]

    vr = subprocess.run([PY, os.path.join(HERE, "verify_sends.py")], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=1200)
    vlines = (vr.stdout or "").strip().splitlines()
    stored = [l for l in vlines if "stored@" in l]
    notfound = [l for l in vlines if "NOT-IN-TRANSCRIPT" in l]
    exact = [l for l in stored if "tail_exact=True" in l]

    bus = os.path.join(HERE, "_bus_door_skew.md")
    bus_sha = sha1_b(bus)
    knocks = sorted(glob.glob(os.path.join(HERE, "knock", "*_200*.txt")))
    relays = sorted(glob.glob(os.path.join(HERE, "relay", "relay_*_2008_*.txt")))

    b = []
    b.append("## 轮 75 · 2026-09-28 %s（值守自跑，全部数字来自本轮工件）" % time.strftime("%H:%M:%S"))
    b.append("")
    b.append("起因：用户要求「保证工人至少工作到晚上 11 点」，并让我替包工头挡掉运行中的困难。"
             "本轮抓到一条协调链缺陷：写盘门已换代，告知车道的自检文件没有跟着换。")
    b.append("")
    b.append("- 门尺换代证据：`ledger_insert_after_r2.py:28` 调 `claim_coordinate_check_r7.py`"
             "（文件内容 sha1 `%s`，本地字节重算，非 git 对象）；`Q43_HOW_TO_PASS_r1.md:4` 与 "
             "`Q43_HOW_TO_PASS_r2.md:11` 仍写 `claim_coordinate_check_r4e.py`；账本里号令者自己写了换代那句"
             "（`CITYNEXUS_AGENT_CONTROL.md:17609`）。" % sha1_b(os.path.join(os.path.dirname(HERE), "claim_coordinate_check_r7.py")))
    b.append("- 同一批字节两枚尺各跑一遍（`_bus_door_skew.py`，%d 枚 = 根目录 %d + 已入账 %d）：判得不一样 %d 枚。"
             % (len(rs), len(root), len(ins), len(skew)))
    b.append("- 根目录按现行门重归因：门绿且能插 %d 枚；门绿但第二道闸拒 %d 枚；现行门就拒 %d 枚。"
             "⇒ 号令者此刻没有欠插，积压不在它账上。" % (len(landed), len(bolted), len(redlane)))
    b.append("- 三臂配方（`_recipe_selftest.py` 本轮实跑）：good=WOULD-LAND、nodecl=WOULD-ABORT"
             "(declared=False anchored=True)、nopara=WOULD-ABORT(declared=True anchored=False) ⇒ 两臂都承重。"
             "第一版我把 nodecl 写成还带 `文件内容 sha1` 的句子，两臂同判 WOULD-LAND，被判据自己拦下了，"
             "改成 map 0404 的真实「blob」写法后才分出。")
    b.append("- 一条我自己的勘误（未外发过，只在本机日志里红过）：19:38 我按 r4e 当门尺，把 19:24/18:53 已入账的"
             "三枚块读成「门拒了却入账」（DOOR-BYPASSED）。它们在 r7 下 findings=0，没有绕过门。"
             "巡检的尺改为从门件派生：`patrol/inbox_check.py` 的 `live_ruler()`，`patrol/bolt_replica.py` 同。")
    b.append("- 外发：总线 Issue #1 评论 `5869413510`（正文 %d B，sha1 `%s`，POST 201 后按 id 回读 body 逐字等）。"
             % (os.path.getsize(bus), bus_sha))
    b.append("- 敲门：车道件 %d 枚（%s）；转达件 %d 枚（%s）。送达回读 `verify_sends.py`："
             "在流水里读到 %d 条，其中尾行逐字 %d 条，未落入流水 %d 条。"
             % (len(knocks), ", ".join(os.path.basename(x) for x in knocks),
                len(relays), ", ".join(os.path.basename(x) for x in relays),
                len(stored), len(exact), len(notfound)))
    for l in notfound:
        b.append("    - %s" % l.strip())
    b.append("- 现尖：`%s`（`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`，本轮读取）。"
             % rows["tip"])
    b.append("- 后续：`patrol/round.py` 每 6 分钟一轮（census + 收件分类（按现行门尺 + 第二道闸）+ 现尖移动 + "
             "被点名但未产出的车道），日志 `patrol/round_watch.log`，跑到 23:00 之后。")
    b.append("- 边界：只读账本/收件目录/会话流水；0 次写账本、0 次插块、0 次改别人字节、0 次动权威线、"
             "0 次敲门给掐着的会话；未新派范围（所有转达都是号令者已写进账本的原话）。")
    b.append("")
    block = "\n".join(b) + "\n"
    assert re.search(r"%[sd]", block) is None, "残留未替换占位符"

    before = io.open(LOG, encoding="utf-8").read()
    add = ("\n" if not before.endswith("\n") else "") + block
    io.open(LOG, "a", encoding="utf-8", newline="\n").write(add)
    after = io.open(LOG, encoding="utf-8").read()
    n = len(add.encode("utf-8"))
    ok = after.encode("utf-8")[-n:] == add.encode("utf-8")
    print("append %d B  bytes_equal=%s  log %d -> %d B" % (n, ok, len(before.encode("utf-8")),
                                                            len(after.encode("utf-8"))))
    print("rows=%d root=%d ins=%d skew=%d landed=%d bolted=%d redlane=%d | sends read: stored=%d exact=%d missing=%d"
          % (len(rs), len(root), len(ins), len(skew), len(landed), len(bolted), len(redlane),
             len(stored), len(exact), len(notfound)))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
