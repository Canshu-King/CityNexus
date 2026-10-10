"""一条命令的值守拍：本机钟点 + 六条 Qoder 会话写入新鲜度 + 两条 Codex 任务的落盘新鲜度。

不截图、不抢前台、不调模型 —— 只读文件系统时间戳。
用法： python beat.py            # 一次拍
      python beat.py 2 300      # 2 拍，每拍之间 sleep 300s（用于"守到某点"）
"""
import glob
import os
import subprocess
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LANES = {
    "494abfd7": "包工头494abfd7",
    "8ccd71d8": "F 8ccd71d8",
    "aad2d1f2": "HJ-P3 aad2d1f2",
    "e345b9d6": "D e345b9d6",
    # 09-25 20:11 勘误：这辆在总线上的自署是「B c01d72a3」（见 5831148052 / 5831584344），
    # 我先前标的 "C" 是沿用旧名册 ⇒ 以后一律带 id 报，别再单独说某个字母。
    "c01d72a3": "B c01d72a3",
    "d2305848": "E d2305848",
}
# Codex 侧：任务 -> 它自己的落盘目录（相对 D:\moodle）
CODEX = {
    "Harness": [r"_hermes_validation_worktree"],
    "MissionA": [r"CityNexus-RevolutionLab-R7-5", r"CityNexus-RevolutionLab-R7-4",
                 r"CityNexus-RevolutionLab-R7-3"],
}
ROOT = r"D:\moodle"
SKIP = ("\\.git\\", "\\node_modules\\", "\\__pycache__\\", "\\dist\\")


def lane_age(key):
    try:
        p = glob.glob(os.path.join(BASE, key + "*.jsonl"))[0]
        return (time.time() - os.stat(p).st_mtime) / 60.0
    except Exception:
        return -1.0


def codex_fresh(dirs, minutes):
    """返回最近 minutes 分钟内被改过的文件数与最新一个（跳过 .git/node_modules/__pycache__）。"""
    newest, count = None, 0
    cutoff = time.time() - minutes * 60
    for d in dirs:
        root = os.path.join(ROOT, d)
        if not os.path.isdir(root):
            continue
        for dp, dns, fns in os.walk(root):
            if any(s in dp for s in SKIP):
                dns[:] = []
                continue
            for f in fns:
                fp = os.path.join(dp, f)
                try:
                    m = os.stat(fp).st_mtime
                except OSError:
                    continue
                if m >= cutoff:
                    count += 1
                    if newest is None or m > newest[0]:
                        newest = (m, fp)
    if not newest:
        return 0, None
    return count, (round((time.time() - newest[0]) / 60.0, 1), os.path.relpath(newest[1], ROOT))


def beat():
    try:
        clock = subprocess.run(["date", "+%H:%M:%S %z"], capture_output=True).stdout.decode().strip()
    except Exception:
        clock = time.strftime("%H:%M:%S")
    lanes = " ".join(f"{n}:{lane_age(k):.1f}m" for k, n in LANES.items())
    parts = []
    for name, dirs in CODEX.items():
        cnt, newest = codex_fresh(dirs, 20)
        tail = f" 最新 {newest[0]}m 前 {os.path.basename(newest[1])}" if newest else ""
        parts.append(f"{name}: 近20分钟改过 {cnt} 件{tail}")
    print(f"[{clock}] Qoder {lanes} | Codex " + " | ".join(parts), flush=True)


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    gap = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    for i in range(rounds):
        beat()
        if i < rounds - 1 and gap:
            time.sleep(gap)


if __name__ == "__main__":
    main()
