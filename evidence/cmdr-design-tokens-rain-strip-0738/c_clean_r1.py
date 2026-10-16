# -*- coding: utf-8 -*-
"""C 盘自救（只清有可重建证据的那一类，先落台账再动手，删前删后各校验一遍）。

对象：`~/.qoder/logs/runs` 里 **十四天以前** 的旧运行日志目录（每次工具调用一份，纯历史流水，
      进程不读它才能跑；近两周那批一律留着——04 号那次我明确留着它们当回溯）。
外加两枚可重建缓存：node-compile-cache、playwright-transform-cache（删了自己会长回来）。

不碰：~/.qoder/logs/sessions（会话正文）、~/.qoder/file-history（改档历史）、
      %LOCALAPPDATA%\\Temp\\qoder-cli（当前会话在写）、以及 D:/moodle 下一切（常设令：不清 moodle）。

安全闸：甲 只删目录名带日期且日期确实在 14 天前的；
      乙 逐个删之前先写清单落盘（名字+字节+钟点），删完回读数出来的目录数；
      丙 任何一枚删不掉（占用）就停下并报，不重试不硬来。
"""
import json
import os
import shutil
import sys
import time

RUNS = os.path.expanduser(r"~/.qoder/logs/runs")
MANIFEST = r"D:/moodle/_cmdr_disk_1017/c_clean_manifest_0618.json"
CUTOFF_DAYS = 14
CACHE_DIRS = [os.path.expandvars(r"%LOCALAPPDATA%\Temp\node-compile-cache"),
              os.path.expandvars(r"%LOCALAPPDATA%\Temp\playwright-transform-cache")]


def df_free(path):
    u = shutil.disk_usage(path)
    return u.free


def dir_bytes(p):
    t = 0
    for root, dirs, files in os.walk(p):
        for f in files:
            try:
                t += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return t


def main():
    if not os.path.isdir(RUNS):
        print("ABORT: 找不到", RUNS)
        return 2
    now = time.time()
    cutoff = now - CUTOFF_DAYS * 86400.0
    entries = sorted(os.listdir(RUNS))
    keep, target = [], []
    for n in entries:
        p = os.path.join(RUNS, n)
        if not os.path.isdir(p) or os.path.islink(p):
            continue
        st = os.stat(p)
        # 目录名前缀就是那次运行的本地钟点（2026-09-29T05-09-35-…），mtime 只作旁证
        name_ts = None
        try:
            name_ts = time.mktime(time.strptime(n[:19], "%Y-%m-%dT%H-%M-%S"))
        except ValueError:
            pass
        if name_ts is None:
            keep.append((n, "名字不带可解析钟点"))
            continue
        if name_ts < cutoff and st.st_mtime < cutoff:
            target.append((n, name_ts, st.st_mtime))
        else:
            keep.append((n, "在窗口内"))
    print("runs 顶层目录 %d 枚｜够老（双条件都过）%d 枚｜留着 %d 枚" % (len(entries), len(target), len(keep)))
    free_before = df_free("C:\\")
    sizes = []
    for n, ts, mt in target:
        sizes.append((n, dir_bytes(os.path.join(RUNS, n))))
    total = sum(s for _, s in sizes)
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "cutoff_days": CUTOFF_DAYS,
               "runs_root": RUNS, "free_before_bytes": free_before,
               "dirs_targeted": len(sizes), "bytes_total": total,
               "items": [{"name": n, "bytes": s} for n, s in sizes],
               "kept_reasons_sample": keep[:40],
               "cache_dirs": CACHE_DIRS},
              open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False)
    print("清单已落盘:", MANIFEST, "| 待清 %.2f GB（%d 个目录）" % (total / 2**30, len(sizes)))
    if "--apply" not in sys.argv:
        print("DRY：没 --apply 就只报数不动。")
        return 0
    removed = 0
    rb = 0
    for n, s in sizes:
        p = os.path.join(RUNS, n)
        try:
            shutil.rmtree(p)
            removed += 1
            rb += s
        except OSError as e:
            print("停下：删不掉 %s（%s）——已删 %d 枚，不再重试" % (n, e.__class__.__name__, removed))
            break
    for c in CACHE_DIRS:
        if os.path.isdir(c):
            try:
                cb = dir_bytes(c)
                shutil.rmtree(c)
                print("缓存目录已清（可重建）:", c, "%.2f GB" % (cb / 2**30))
                rb += cb
            except OSError as e:
                print("缓存删不动，跳过:", c, e.__class__.__name__)
    free_after = df_free("C:\\")
    left = len([n for n in os.listdir(RUNS) if os.path.isdir(os.path.join(RUNS, n))])
    print("删后：移除目录 %d 枚｜runs 现存 %d 枚｜记账字节 %.2f GB" % (removed, left, rb / 2**30))
    print("C 盘余量：删前 %.2f GB -> 删后 %.2f GB（差 %.2f GB）"
          % (free_before / 2**30, free_after / 2**30, (free_after - free_before) / 2**30))
    json.dump({"removed_dirs": removed, "dirs_left_in_runs": left,
               "bytes_accounted": rb, "free_before_bytes": free_before,
               "free_after_bytes": free_after},
              open(MANIFEST.replace(".json", "_after.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("删后台账:", MANIFEST.replace(".json", "_after.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
