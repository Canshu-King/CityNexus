#!/usr/bin/env python
"""Shared frontend store audit (提案工, ORD-0557 blocker report).

Nothing is installed, moved or deleted.  The tool only asks, for each package that this lane's gates
need, whether the shared store that every lane's `frontend/node_modules` junction points at actually
contains it, and compares that against two stores that are known to be complete.

    python store_audit_0557_r1.py
"""
from __future__ import annotations

import os
import subprocess
import sys

STORES = {
    "shared(CityNexus)": r"D:/moodle/CityNexus/frontend/node_modules",
    "cmdr_ref": r"D:/moodle/_qoder_cmdr_ref_20260921/frontend/node_modules",
    "integration_20260919": r"D:/moodle/_qoder_integration_20260919/frontend/node_modules",
}
PKGS = ["@babel/core", "@dnd-kit/core", "@dnd-kit/sortable", "@dnd-kit/utilities",
        "@vitejs/plugin-react", "typescript", "vite", "@playwright/test"]
LANE = r"D:/moodle/_qoder_tiaanianggong_0555/frontend/node_modules"


def junction_target(path):
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Item -LiteralPath '%s' -Force).Target" % path],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout.strip()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lines = ["shared store audit -- read-only probe, nothing installed or deleted", ""]
    lines.append("this lane's frontend/node_modules resolves to: %s" % (junction_target(LANE) or "(a real directory)"))
    lines.append("")
    header = "%-22s" % "package"
    for name in STORES:
        header += " %-20s" % name
    lines.append(header)
    missing_here = []
    for p in PKGS:
        row = "%-22s" % p
        for name, root in STORES.items():
            has = os.path.isdir(os.path.join(root, *p.split("/")))
            row += " %-20s" % ("present" if has else "MISSING")
            if name.startswith("shared") and not has:
                missing_here.append(p)
        lines.append(row)
    lines.append("")
    for name, root in STORES.items():
        entries = len([x for x in os.listdir(root)]) if os.path.isdir(root) else -1
        lines.append("%s entry_count=%d" % (name, entries))
    lines.append("")
    lines.append("packages this lane's gates need but the shared store does not hold: %s" % (", ".join(missing_here) or "(none)"))
    text = "\n".join(lines)
    print(text)
    out = os.path.join(r"D:/moodle/_qoder_tiaanianggong_0555", "review", "tiaanianggong-0557", "store_audit_r1.txt")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    print("wrote %s" % out.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
