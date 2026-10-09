# -*- coding: utf-8 -*-
"""夜里最后那一次跑批（一条命令出全套交接件）。

为什么要有：23:00 前那半小时我自己也可能已经撞闸，所以把『该出哪几份件』写成一条命令，
到点只要跑一发；每份都现算，不引用我记忆里的数字。
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")

JOBS = [
    (u"下午到夜里值守报告", "evening_report_r1.py", []),
    (u"夜版交接稿（不重写早版）", "handover_r1.py", ["--night"]),
    (u"夜间终判（谁撑到几点）", "_night_verdict_r1.py", ["12:00"]),
    (u"额度潮证据件", "_quota_wave_evidence_r1.py", []),
    (u"交班条（当刻现值）", "write_watch_note_r1.py", []),
]
ARTIFACTS = [
    os.path.join(LC, "EVENING_REPORT_0929.md"),
    os.path.join(HERE, "HANDOVER_0929_night.md"),
    os.path.join(LC, "NIGHT_VERDICT_0929.txt"),
    os.path.join(LC, "QUOTA_WAVE_0929.md"),
    os.path.join(LC, "EVENING_WATCH_NOTE_0929.md"),
]


def main():
    print("=== 夜终跑批 %s ===" % time.strftime("%H:%M:%S"))
    for name, script, args in JOBS:
        t0 = time.time()
        try:
            p = subprocess.run([PY, os.path.join(HERE, script)] + args, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", env=ENV,
                               timeout=1800, cwd=HERE)
            tail = [x.strip() for x in (p.stdout or "").split(chr(10)) if x.strip()]
            print("  %-22s rc=%d  %.0f 分  %s" % (name, p.returncode, (time.time() - t0) / 60.0,
                                                  (tail[-1][:120] if tail else "无输出")))
            if p.returncode:
                err = [x.strip() for x in (p.stderr or "").split(chr(10)) if x.strip()]
                if err:
                    print("      stderr: %s" % err[-1][:150])
        except Exception as e:
            print("  %-22s 失败：%s: %s" % (name, type(e).__name__, str(e)[:120]))
    print("--- 产物（尺寸/时刻，跑批后回读）---")
    for a in ARTIFACTS:
        if os.path.isfile(a):
            print("  %-34s %7d B  %s" % (os.path.basename(a), os.path.getsize(a),
                                          time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(a)))))
        else:
            print("  %-34s 缺！" % os.path.basename(a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
