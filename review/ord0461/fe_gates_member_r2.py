"""ORD-0461 r2: the three frontend gates at the head that will be pushed, each exit code captured by its own run."""
import io
import os
import subprocess

WT = "D:/moodle/_qoder_rel_ord0461_wt"
FRONTEND = WT + "/frontend"
OUT = "D:/moodle/_qoder_rel_ord0461_wk/r2_fe_gates_r1.txt"
npx = "npx.cmd" if os.name == "nt" else "npx"

head = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True,
                      text=True).stdout.strip()
lines = ["head=%s" % head, "worktree_dirty=%s" % (
    subprocess.run(["git", "-C", WT, "status", "--porcelain"], capture_output=True,
                   text=True).stdout.strip().replace("\n", " | ") or "clean")]
for label, project in (("check", "tsconfig.check.json"), ("typecheck", "tsconfig.typecheck.json")):
    result = subprocess.run([npx, "tsc", "-p", project, "--noEmit"], cwd=FRONTEND,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (result.stdout or "") + (result.stderr or "")
    lines.append("tsc_%s_rc=%d output_bytes=%d" % (label, result.returncode, len(out.encode("utf-8"))))
    lines.append("tsc_%s_dir=%s" % (label, FRONTEND))
    if out.strip():
        lines.append("tsc_%s_first_line=%s" % (label, out.strip().splitlines()[0][:160]))
build = subprocess.run([npx, "vite", "build"], cwd=FRONTEND, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
bout = (build.stdout or "") + (build.stderr or "")
lines.append("vite_rc=%d" % build.returncode)
lines += ["vite_" + l.strip() for l in bout.splitlines()
          if "built in" in l or "error" in l.lower()][:4]
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
io.open("D:/moodle/_qoder_rel_ord0461_wk/r2_fe_gates_stdout.txt", "w", encoding="utf-8",
        newline="\n").write("\n".join(lines) + "\n")
