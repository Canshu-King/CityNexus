# -*- coding: utf-8 -*-
"""inbox_preflight.py — 用「写盘门自己那一版尺」逐枚预检收件目录里的待插块。

只读：跑的是 ledger_insert_after.py:28 调的那一枚尺（claim_coordinate_check_r4e.py --text <文件> --expect-clean），
不碰账本、不搬文件。目的：把会被 REFUSE 的块和它咬的具体 token 先摆出来，省号令者一轮 900 秒超时。

用法：python -X utf8 inbox_preflight.py
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROCESSED = os.path.join(INBOX, "_processed")
DOOR = "claim_coordinate_check_r4e.py"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inbox_preflight.json")


def main():
    files = sorted(glob.glob(os.path.join(INBOX, "*.md")))
    rows = []
    for p in files:
        name = os.path.basename(p)
        mtime = os.stat(p).st_mtime
        wait_min = (time.time() - mtime) / 60.0
        t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(LC, DOOR), "--text", p, "--expect-clean"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
        verdict = "PASS" if r.returncode == 0 else "REFUSE"
        # 门的每一枚 finding 都长这样：  "  line 40 F3_bare_numeric_claim NUMBER_WITHOUT_COORDINATE | 3 个 | no class matched"
        offenders = [l.strip() for l in out if re.match(r"^\s*line \d+ \w+ \w+ \|", l)]
        summary = [l.strip() for l in out if "overall Q43_GATE" in l or "ADVISORY" in l]
        rows.append({"file": name, "bytes": os.path.getsize(p), "wait_min": round(wait_min, 1),
                     "door_rc": r.returncode, "verdict": verdict, "secs": round(time.time() - t0, 1),
                     "tail": out[-3:], "summary": summary, "findings_n": len(offenders),
                     "offenders": offenders})
        print("%-28s %6s B  等 %5.0f 分  %s rc=%d findings=%d (%.1fs)" % (name, os.path.getsize(p), wait_min,
                                                                        verdict, r.returncode,
                                                                        len(offenders), time.time() - t0))
        for o in offenders[:4]:
            print("      " + o[:200])
        sys.stdout.flush()
    npass = sum(1 for x in rows if x["verdict"] == "PASS")
    # 反控：拿一枚「已经入账」的块用同一枚尺回跑，必须 GREEN——否则上面那批 RED 就可能是尺坏了而不是块坏了
    ctrl = os.path.join(PROCESSED, "qoder-0388_0420.md.inserted_042148")
    ctrl_rc = ctrl_verdict = None
    if os.path.exists(ctrl):
        cr = subprocess.run([sys.executable, os.path.join(LC, DOOR), "--text", ctrl, "--expect-clean"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        ctrl_rc = cr.returncode
        ctrl_verdict = "GREEN" if cr.returncode == 0 else "RED"
    print("\n合计 待插 %d 枚：门绿 %d 枚 / 会拒 %d 枚（尺 = %s，与 ledger_insert_after.py:28 同一枚）"
          % (len(rows), npass, len(rows) - npass, DOOR))
    print("反控（已入账块回跑同一枚尺）：%s rc=%s" % (os.path.basename(ctrl), ctrl_rc))
    door_path = os.path.join(LC, DOOR)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "door": DOOR,
         "door_sha1_local": hashlib.sha1(io.open(door_path, "rb").read()).hexdigest(),
         "door_bytes": os.path.getsize(door_path),
         "total": len(rows), "pass": npass, "refuse": len(rows) - npass,
         "control_block": os.path.basename(ctrl), "control_rc": ctrl_rc, "control_verdict": ctrl_verdict,
         "rows": rows},
        ensure_ascii=False, indent=1))
    print("写收据 %s（%d B）" % (os.path.basename(OUT), os.path.getsize(OUT)))


main()
