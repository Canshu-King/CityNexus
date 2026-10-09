"""Read-only diagnostic: why does a Q43-GREEN inbox block still not land?

Checks the two OTHER arms that the writer (ledger_insert_after.py) applies:
  1) the exact anchor line must occur EXACTLY ONCE in the local ledger, else every block ABORTs;
  2) every full 40-hex coordinate in the block must resolve via `git cat-file -t` in D:/moodle/CityNexus.
Writes nothing except its own report file.
"""
import io
import os
import re
import subprocess
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
REPO = r"D:\moodle\CityNexus"
ANCHOR = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
RULER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "claim_coordinate_check_r4e.py")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"


def door(text_path):
    r = subprocess.run([PY, RULER, "--text", text_path, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    verdict = "GREEN" if r.returncode == 0 else "RED"
    n = len(re.findall(r"^\s*[-*]?\s*line \d+", r.stdout or "", re.M))
    return verdict, r.returncode, n, (r.stdout or "").strip().splitlines()[-1:]


def main():
    led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    lines = []
    lines.append("[%s] read-only diagnostic: green-but-uninserted" % time.strftime("%H:%M:%S"))
    lines.append("ledger: %s  bytes=%d  mtime=%s" % (LEDGER, os.path.getsize(LEDGER),
                 time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(LEDGER)))))
    lines.append("anchor exact-line occurrences=%d  (writer aborts a block unless this is 1)" % led.count(ANCHOR))
    lines.append("'## ORDERS' occurrences=%d" % led.count("## ORDERS"))
    roots = sorted([f for f in os.listdir(INBOX) if f.endswith(".md")])
    lines.append("inbox root blocks=%d" % len(roots))
    for f in roots:
        p = os.path.join(INBOX, f)
        verdict, rc, nfind, tail = door(p)
        body = io.open(p, encoding="utf-8", errors="replace").read()
        toks = sorted(set(HEX40.findall(body)))
        unres = []
        for h in toks:
            r = subprocess.run(["git", "-C", REPO, "cat-file", "-t", h],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode:
                unres.append(h)
        age_min = (time.time() - os.path.getmtime(p)) / 60.0
        lines.append("  %-22s door=%s rc=%d findings~%d hex40=%d unresolvable=%d age=%.0fmin  %s" % (
            f, verdict, rc, nfind, len(toks), len(unres), age_min,
            (unres[0][:12] + "...") if unres else ""))
        if verdict == "GREEN":
            lines.append("      GREEN-AND-%s: unresolvable=%d  first=%s" % (
                "STUCK" if age_min > 20 else "FRESH", len(unres),
                body.splitlines()[0][:80]))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "green_stuck_report.txt")
    txt = chr(10).join(lines) + chr(10)
    io.open(out, "w", encoding="utf-8", newline=chr(10)).write(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
