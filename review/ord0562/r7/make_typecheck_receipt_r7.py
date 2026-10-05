# -*- coding: utf-8 -*-
"""Turn the two byteless typecheck receipts into one file that carries lines a reader can open.

`npx tsc -p <project> --noEmit` writes nothing on success, so the captured files are zero bytes and cannot
be cited as path:line by the ledger gate. The command, its rc and the captured size are written here so the
receipt is a real line, not an absence.
"""

import io
import os
import subprocess

WT = r"D:/moodle/_qoder_ord0568_r3_20261005/wt/frontend"
R7 = r"D:/moodle/_ord0568_r3/r7"
OUT = os.path.join(R7, "typecheck_r7.txt")

env = dict(os.environ)
for gone in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY"):
    env.pop(gone, None)

lines = ["ORD-0562 r6 typecheck, run in this pass from the re-cut branch worktree."]
failures = []
for project in ("tsconfig.check.json", "tsconfig.typecheck.json"):
    cap = os.path.join(R7, "typecheck_%s.txt" % ("check" if "check.json" in project else "typecheck"))
    proc = subprocess.run(["node", os.path.join(WT, "node_modules", "typescript", "bin", "tsc"),
                           "-p", project, "--noEmit"],
                          cwd=WT, capture_output=True, env=env)
    body = proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")
    with io.open(cap, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    size = os.path.getsize(cap)
    lines.append("$ node node_modules/typescript/bin/tsc -p %s --noEmit" % project)
    lines.append("  rc=%d  captured output=%d bytes (no diagnostics)" % (proc.returncode, size))
    if proc.returncode != 0 or size != 0:
        failures.append(project)
        lines.append(body[:2000])

text = "\n".join(lines) + "\n"
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)
print(text)
if failures:
    raise SystemExit("REFUSED: " + ", ".join(failures))
print("OK: both typecheck projects returned rc=0 with no diagnostics")
