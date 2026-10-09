#!/usr/bin/env python3
"""ORD-0553 / 长瓦工 -- snapshot of the claim surface at the moment this lane took the file.

Point-in-time by nature: it runs the commander's own ruler and the remote ref list once and freezes
what they said, so the rollup can quote a reading that does not move under later ledger writes.
"""

import io
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "review", "changwagong")
RULER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_live_orders_reader_r1.py"
LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
FILE = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"


def run(cmd, cwd=None):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", shell=False, cwd=cwd)
    return p.returncode, p.stdout + p.stderr


def main():
    lines = []
    rc, out = run([sys.executable, RULER])
    claim_rows = [ln for ln in out.splitlines() if "账本第" in ln and "｜" in ln and ".tsx" in ln or ".ts`" in ln]
    hits = [ln for ln in claim_rows if "RealCityDiscoveryPanel" in ln]
    lines.append("ruler=%s rc=%d" % (RULER, rc))
    lines.append("claim_rows_total=%d" % len(claim_rows))
    lines.append("claim_rows_naming_this_file=%d" % len(hits))
    for ln in claim_rows:
        lines.append("  claim> %s" % ln.strip())
    # 逐字认领句式在账本全文里对本文件的命中（认领…`路径`）
    ledger = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
    pat = re.compile(u"认领[^\n]{0,140}?`([A-Za-z0-9_./\\-]+\\.tsx)`")
    named = [(i, m.group(1)) for i, ln in enumerate(ledger, 1)
             for m in [pat.search(ln)] if m and "RealCityDiscoveryPanel" in m.group(1)]
    lines.append("ledger_verbatim_claim_lines_naming_this_file=%d" % len(named))
    for i, f in named:
        lines.append("  ledger:%d %s" % (i, f))
    rc, refs = run(["git", "-C", "D:/moodle/CityNexus", "ls-remote", "--refs", "origin"])
    lanes = [ln.split("\t")[1].strip() for ln in refs.splitlines()
             if "\t" in ln and "0553" in ln and "refs/heads/review/" in ln]
    lines.append("remote_refs_with_0553=%d" % len(lanes))
    for ln in lanes:
        lines.append("  ref> %s" % ln)
    rc, tip = run(["git", "-C", "D:/moodle/CityNexus", "ls-remote", "origin",
                   "refs/heads/mirror/integration-frontend-apple-pass1"])
    lines.append("authoritative_tip_at_capture=%s" % (tip.split("\t")[0] if "\t" in tip else "UNREAD"))
    text = "\n".join(lines) + "\n"
    with io.open(os.path.join(OUT, "_claims_capture.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
