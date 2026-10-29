"""bw281: prove the shape _push_rulers_r2 now uses actually protects a concurrent writer.

The leg used to run `git add -- <its own path>` followed by a bare `git commit -m msg`.
This builds a throwaway repository with one staged entry of ours and one of another writer,
then runs both shapes: the bare commit must sweep the foreign entry, the pathspec commit must
not.  Without the first arm passing, the second proves nothing.
"""

import io
import os
import subprocess
import sys
import tempfile

def sh(args, cwd):
    done = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                          errors="replace")
    return done.returncode, done.stdout, done.stderr


def build(box):
    sh(["init", "-q"], box)
    sh(["config", "user.email", "gate@example.invalid"], box)
    sh(["config", "user.name", "gate"], box)
    io.open(os.path.join(box, "ours.py"), "w", encoding="utf-8").write("ruler = 1\n")
    io.open(os.path.join(box, "theirs.py"), "w", encoding="utf-8").write("lane = 1\n")
    sh(["add", "ours.py", "theirs.py"], box)
    sh(["commit", "-q", "-m", "seed"], box)
    # both writers edit their own file; the other one stages theirs and walks off
    io.open(os.path.join(box, "ours.py"), "a", encoding="utf-8").write("ours = 2\n")
    io.open(os.path.join(box, "theirs.py"), "a", encoding="utf-8").write("theirs = 2\n")
    sh(["add", "theirs.py"], box)


def carried(sha, box):
    rc, out, _ = sh(["show", "--name-only", "--format=", sha], box)
    return [line.strip() for line in out.splitlines() if line.strip()]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lines = ["COMMIT SHAPE PROTECTION PROBE bw281"]

    box = tempfile.mkdtemp(prefix="cmdr_shape_bare_")
    build(box)
    rc, out, err = sh(["commit", "-q", "-m", "bare shape"], box)
    bare = carried("HEAD", box) if rc == 0 else []
    lines.append("BARE_COMMIT carried=%s foreign_swept=%s" % (sorted(bare), "theirs.py" in bare))

    box2 = tempfile.mkdtemp(prefix="cmdr_shape_pathspec_")
    build(box2)
    rc2, out2, err2 = sh(["commit", "-q", "-m", "pathspec shape", "--", "ours.py"], box2)
    pathspec = carried("HEAD", box2) if rc2 == 0 else []
    left = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=box2,
                          capture_output=True, text=True, errors="replace").stdout.split()
    lines.append("PATHSPEC_COMMIT carried=%s foreign_still_staged=%s"
                 % (sorted(pathspec), "theirs.py" in left))

    ok = ("theirs.py" in bare and pathspec == ["ours.py"] and "theirs.py" in left)
    lines.append("VERDICT %s" % ("PROTECTED" if ok else "PROBE_RED"))
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    receipt = os.path.join(root, "trial", "results", "20261026_gozero",
                           "bw281-commit-shape-protection.txt")
    io.open(receipt, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % receipt)
    return 0 if ok else 9


if __name__ == "__main__":
    sys.exit(main())
