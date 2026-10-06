"""Background bus watcher: re-run the proven `bus_new.py` cursor reader until anything newer than a
watermark shows up, print it, and exit. Cheap because bus_new.py walks with `since=` and caches.

Usage: python watch_bus.py <watermark_id> [--max-minutes N] [--interval S]
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("watermark", type=int)
    ap.add_argument("--max-minutes", type=float, default=12.0)
    ap.add_argument("--interval", type=float, default=45.0)
    a = ap.parse_args()
    end = datetime.now(timezone.utc) + timedelta(minutes=a.max_minutes)
    seen = a.watermark
    ticks = 0
    while True:
        ticks += 1
        p = subprocess.run([sys.executable, "bus_new.py", str(seen),
                            "--repo", "Canshu-King/CityNexus-Workspace"],
                           cwd=HERE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        out = p.stdout or ""
        n = None
        for line in out.splitlines():
            if line.startswith("repo=") and "above_" in line:
                try:
                    n = int(line.split("above_")[-1].split("=")[-1])
                except ValueError:
                    n = None
        if n:
            print("NEW=" + str(n), flush=True)
            print(out, flush=True)
            for line in out.splitlines():
                if line.startswith("id="):
                    try:
                        seen = max(seen, int(line.split("=")[1].split(" ")[0]))
                    except (ValueError, IndexError):
                        pass
            print("HIGHEST_SEEN=%d" % seen, flush=True)
            return 0
        print("tick", ticks, "| nothing newer than", seen, "| deadline",
              end.astimezone(timezone(timedelta(hours=8))).strftime("%H:%M"),
              "| rc", p.returncode, flush=True)
        if datetime.now(timezone.utc) >= end:
            print("WATCH_TIMEOUT after %d ticks; nothing newer than %d" % (ticks, seen), flush=True)
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())
