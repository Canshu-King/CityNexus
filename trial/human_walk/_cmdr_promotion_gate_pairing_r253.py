"""bw253: pair every writer that promotes a plan or a journey to SELECTED/ACTIVE with the
shared authority gate, and report whether the gate is visible in the same function.

This is a census, not a verdict.  "Not visible in the same function" does not mean the
route refused to ask - it means this ruler cannot see the answer from one function body,
and names the row that a walk has to settle.  Section 14.20 already settled one such row
by walking the real routes.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(ROOT, "backend", "app")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw253-promotion-gate-pairing.txt")

DEF_RE = re.compile(r"^(?:async )?def (\w+)")
ASSIGN_RE = re.compile(r"^\s*(\w[\w.]*)\.status = \"(ACTIVE|SELECTED)\"")
ROUTE_RE = re.compile(r"@app\.(get|post|patch|put|delete)\(\"([^\"]+)\"")
GATE_WORDS = ("plan_authority_blocker", "authority_blocker")


def functions(text):
    """Yield (name, start_line, end_line, body) for each top-level or nested def."""

    lines = text.splitlines()
    found = []
    for index, line in enumerate(lines):
        match = DEF_RE.match(line)
        if not match:
            continue
        indent = len(line) - len(line.lstrip())
        end = len(lines)
        for follower in range(index + 1, len(lines)):
            row = lines[follower]
            if not row.strip():
                continue
            if (len(row) - len(row.lstrip())) <= indent and not row.lstrip().startswith(")"):
                end = follower
                break
        found.append((match.group(1), index + 1, end, lines[index + 1:end]))
    return found


def route_for(lines, def_line):
    for cursor in range(def_line - 2, max(0, def_line - 12), -1):
        if cursor < 0:
            break
        match = ROUTE_RE.search(lines[cursor])
        if match:
            return "%s %s" % (match.group(1).upper(), match.group(2))
        if lines[cursor].strip() and not lines[cursor].lstrip().startswith("@"):
            break
    return "(no @app route decorator above it)"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = []
    for dirpath, _dirnames, filenames in os.walk(APP):
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            text = io.open(path, encoding="utf-8").read()
            lines = text.splitlines()
            for fname, start, end, body in functions(text):
                for offset, row in enumerate(body):
                    match = ASSIGN_RE.match(row)
                    if not match:
                        continue
                    target, status = match.group(1), match.group(2)
                    if not re.search(r"(plan|journey|new_plan|next_activity|activity|"
                                     r"current|execution|mission|intent|replacement)",
                                     target, re.I):
                        continue
                    asked = any(word in "\n".join(body) for word in GATE_WORDS)
                    rows.append({
                        "file": os.path.relpath(path, ROOT).replace("\\", "/"),
                        "line": start + offset + 1,
                        "target": target,
                        "status": status,
                        "function": fname,
                        "route": route_for(lines, start),
                        "gate_in_same_function": asked,
                    })

    rows.sort(key=lambda r: (not r["gate_in_same_function"], r["file"], r["line"]))
    asked = [r for r in rows if r["gate_in_same_function"]]
    unseen = [r for r in rows if not r["gate_in_same_function"]]
    lines_out = [
        "PROMOTION WRITERS PAIRED AGAINST THE SHARED AUTHORITY GATE bw253",
        "ROWS %d (gate visible in the same function %d, not visible %d)"
        % (len(rows), len(asked), len(unseen)),
        "NOTE: \"not visible\" is this ruler's limit, not a defect claim.",
        "GATE VISIBLE IN THE SAME WRITING FUNCTION",
    ]
    for row in asked:
        lines_out.append("  %s:%d %s.status=%s in %s [%s]"
                         % (row["file"], row["line"], row["target"], row["status"],
                            row["function"], row["route"]))
    lines_out.append("WRITERS WHERE THIS RULER CANNOT SEE THE GATE IN THE SAME FUNCTION")
    for row in unseen:
        lines_out.append("  %s:%d %s.status=%s in %s [%s]"
                         % (row["file"], row["line"], row["target"], row["status"],
                            row["function"], row["route"]))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines_out) + "\n")
    for line in lines_out:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
