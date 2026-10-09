# -*- coding: utf-8 -*-
"""C 盘余量与「可清理项」清单：按 mtime 分档数出能放出多少，交人点单。

为什么要现取（10-04 18:2x 实测）：C 只剩四个多 GB，而所有会话的任务流水都写在 C 上
——车队先撑不住的是 C，不是 D。半天里 C 从六点多 GB 掉到四个多 GB，照这个斜率今晚就可能满，
满了之后不只是值守看不见，是**所有会话连自己的流水都写不进去**。

只数、不删：这是别人（Qoder 应用自身）的数据目录，删哪一档要人来点。
判据也写清楚：分档只看文件自己的 mtime；`<1 天` 那一档永远不碰（正在写）。
"""
import io
import json
import os
import sys
import time

ROOT = u"C:/Users/仓鼠王/.qoder"
LOGS = os.path.join(ROOT, u"logs")
SNAP = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_c_headroom_snap.txt"
MODE = u"read"
for a in sys.argv[1:]:
    if a.startswith("--snap"):
        MODE = u"snap"
    elif a.startswith("--reprint"):
        MODE = u"reprint"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if MODE == u"reprint":
    if not os.path.exists(SNAP):
        sys.stdout.write(u"NO_SNAPSHOT_YET\n")
        sys.exit(3)
    sys.stdout.write(io.open(SNAP, encoding="utf-8").read())
    sys.exit(0)

import ctypes


def free_gb(drive):
    a = ctypes.c_ulonglong(0); t = ctypes.c_ulonglong(0); f = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(drive, ctypes.byref(a), ctypes.byref(t), ctypes.byref(f))
    return a.value / 2 ** 30, t.value / 2 ** 30


def bucket(sub):
    now = time.time()
    out = {"<1d": [0, 0], "1-3d": [0, 0], "3-7d": [0, 0], ">7d": [0, 0]}
    for root, _ds, files in os.walk(os.path.join(LOGS, sub)):
        for fn in files:
            try:
                st = os.stat(os.path.join(root, fn))
            except Exception:
                continue
            d = (now - st.st_mtime) / 86400.0
            k = "<1d" if d < 1 else "1-3d" if d < 3 else "3-7d" if d < 7 else ">7d"
            out[k][0] += st.st_size
            out[k][1] += 1
    return out

cf, ct = free_gb(u"C:/")
df_, dt = free_gb(u"D:/")
runs = bucket("runs")
sess = bucket("sessions")
ge7 = (runs[">7d"][0] + sess[">7d"][0]) / 2 ** 30
ge3 = ge7 + (runs["3-7d"][0] + sess["3-7d"][0]) / 2 ** 30
text = (u"read_at=%s\nC_free_GB=%.2f C_total_GB=%.2f D_free_GB=%.2f\n"
        u"runs_lt1d=%.2f runs_1_3d=%.2f runs_3_7d=%.2f runs_gt7d=%.2f\n"
        u"sessions_lt1d=%.2f sessions_1_3d=%.2f sessions_3_7d=%.2f sessions_gt7d=%.2f\n"
        u"reclaim_gt7d_GB=%.2f reclaim_gt3d_GB=%.2f\n"
        u"runs_files=%d sessions_files=%d\n"
        % (time.strftime("%Y-%m-%d %H:%M:%S"), cf, ct, df_,
           runs["<1d"][0] / 2 ** 30, runs["1-3d"][0] / 2 ** 30, runs["3-7d"][0] / 2 ** 30,
           runs[">7d"][0] / 2 ** 30,
           sess["<1d"][0] / 2 ** 30, sess["1-3d"][0] / 2 ** 30, sess["3-7d"][0] / 2 ** 30,
           sess[">7d"][0] / 2 ** 30, ge7, ge3,
           sum(v[1] for v in runs.values()), sum(v[1] for v in sess.values())))
io.open(SNAP, "w", encoding="utf-8", newline="\n").write(text)
sys.stdout.write(text)
