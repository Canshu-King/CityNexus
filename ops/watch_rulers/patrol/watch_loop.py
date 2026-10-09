"""一轮一行：Codex（读 sqlite 判停）+ Qoder（读会话字节距上次写入分钟数）。追加进 watch_*.log。"""
import datetime
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "watch_loop.log")


def run(script, args):
    p = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, script)] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=180)
    return (p.stdout or "").strip() + ((p.stderr or "").strip()[:200] if p.returncode else "")


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    gap = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    for i in range(rounds):
        cx = run("codex_watch.py", ["1", "0"])
        qd = run("beat.py", ["1", "0"])
        stopped = [ln for ln in cx.splitlines() if "ACTION_NEEDED" in ln]
        block = "\n".join([cx] + (["  >>> " + s.strip() for s in stopped] if stopped else []) + [qd])
        with io.open(LOG, "a", encoding="utf-8", newline="\n") as f:
            f.write(block + "\n")
        print(block, flush=True)
        if stopped:
            print("STOP_DETECTED round=%d" % i, flush=True)
        if i + 1 < rounds:
            time.sleep(gap)


if __name__ == "__main__":
    main()
