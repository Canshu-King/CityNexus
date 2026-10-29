"""Commit gate: a commit may carry only the paths it names, and another writer's index stays intact.

Twice inside two minutes this session ran ``git add -- <my files>`` followed by ``git commit -m ...``
with no pathspec, and each time the sweep also landed the concurrent writer's 22 staged frontend files
under my commit message.  Both were undone with ``git reset --soft`` and a pathspec re-commit, but a
rule I have to remember is not a rule -- so the rule now lives in the door that writes.

What it refuses:
  * a commit whose tree differs from the paths named on the command line (rolled back, rc=3);
  * a foreign staged entry that disappeared from the index (rolled back, rc=4);
  * a named path that is not in the tree, or no path at all (rc=2), because a pathspec commit of
    nothing is how a half-staged edit slips in silently;
  * with --expect-clean, a named path that still differs from the index after staging -- that is a
    concurrent edit to the very file being delivered.

--selftest builds a throwaway repository, stages a file that is NOT part of the claimed delivery, and
proves the gate bites: the no-pathspec shape sweeps it away, the gate does not.
"""
import argparse
import io
import os
import subprocess
import sys
import tempfile

# trial/human_walk/<this file> sits two directories under the repository root, so the root is three
# dirname() calls away.  With one fewer the gate looked for trial/trial/... and refused a real delivery
# -- a wrong REFUSE is still a broken instrument, so it is pinned here and asserted in --selftest.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def git(*args, cwd=ROOT):
    done = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("ABORT git %s -> %s" % (" ".join(args), done.stderr.strip()[:300]))
    return done.stdout


def staged(cwd):
    return {l.strip() for l in git("diff", "--cached", "--name-only", cwd=cwd).splitlines() if l.strip()}


def unstaged(paths, cwd):
    out = subprocess.run(["git", "diff", "--name-only", "--"] + list(paths), cwd=cwd,
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    return {l.strip() for l in out.splitlines() if l.strip()}


def committed_paths(sha, cwd):
    return {l.strip() for l in git("show", "--name-only", "--format=", sha, cwd=cwd).splitlines() if l.strip()}


def in_index_or_head(path, cwd):
    """Answer whether git already knows this module, in the index or in HEAD."""
    here = subprocess.run(["git", "ls-files", "--error-unmatch", path], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    if here.returncode == 0:
        return True
    there = subprocess.run(["git", "cat-file", "-e", "HEAD:%s" % path], cwd=cwd,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
    return there.returncode == 0


def unresolved_module_imports(paths, cwd):
    """Refuse a commit that ships a component whose relative import resolves to nothing.

    bw267/bw270 measured seven modules that exist only as untracked files while nine
    staged components already import them.  A pathspec commit of those components would
    publish a tree that cannot build, and the door -- not my memory -- has to stop it.
    The resolution rules come from the census ruler itself, so one definition of a module
    path serves both.  A module that this very delivery names counts as resolvable: the
    check runs before git add, so otherwise the gate refuses a complete delivery.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _cmdr_imported_but_untracked_r267 as census

    delivered = {p.replace("\\", "/") for p in paths}
    bad = []
    for rel in sorted(paths):
        if not rel.endswith(census.EXTS):
            continue
        full = os.path.join(cwd, rel)
        if not os.path.isfile(full):
            continue
        text = io.open(full, encoding="utf-8", errors="replace").read()
        for spec in census.IMPORT_RE.findall(text):
            if spec.lower().endswith((".css", ".scss", ".json", ".svg", ".png",
                                      ".jpg", ".webp", ".gif", ".woff", ".woff2")):
                continue
            candidates = census.resolve(rel, spec, cwd)
            if delivered & set(candidates):
                continue
            if not any(in_index_or_head(c, cwd) for c in candidates):
                bad.append("%s imports %s" % (rel, spec))
    return bad


def land(message_file, paths, cwd, expect_clean=False):
    mine = {p.replace("\\", "/") for p in paths}
    if not mine:
        print("REFUSE no paths named")
        return 2
    missing = [p for p in sorted(mine) if not os.path.exists(os.path.join(cwd, p))]
    if missing:
        print("REFUSE path not present", missing)
        return 2
    base = git("rev-parse", "HEAD", cwd=cwd).strip()
    unresolved = unresolved_module_imports(mine, cwd)
    if unresolved:
        print("REFUSE these paths import a module that exists in neither the index nor HEAD:")
        for item in unresolved[:8]:
            print("   ", item)
        print("     add the module itself to the same delivery, or drop the importer.")
        return 6
    foreign_before = staged(cwd) - mine
    git("add", "--", *sorted(mine), cwd=cwd)
    if expect_clean:
        left = unstaged(sorted(mine), cwd)
        if left:
            print("REFUSE these paths still differ from the index after staging", sorted(left))
            return 5
    # The pathspec is the whole point: git then reads the tree for these paths only and leaves every
    # other index entry exactly where its owner put it.
    git("commit", "-q", "-F", message_file, "--", *sorted(mine), cwd=cwd)
    sha = git("rev-parse", "HEAD", cwd=cwd).strip()
    got = committed_paths(sha, cwd)
    foreign_after = staged(cwd)
    print("HEAD", sha)
    print("COMMIT_PATHS", len(got), sorted(got))
    print("FOREIGN_STAGED before=%d after=%d" % (len(foreign_before), len(foreign_after)))
    extra = got - mine
    if extra:
        print("ROLLED_BACK this commit carried files nobody named", sorted(extra)[:6])
        git("reset", "--soft", base, cwd=cwd)
        return 3
    if not (foreign_before - foreign_after):
        print("OK foreign index untouched")
        return 0
    print("ROLLED_BACK swallowed another writer's staged files", sorted(foreign_before - foreign_after)[:6])
    git("reset", "--soft", base, cwd=cwd)
    return 4


def selftest():
    # The first arm is the ROOT arithmetic itself: with one dirname() too few the gate looked for
    # trial/trial/... and refused a delivery whose files were all really there.  A wrong REFUSE is a
    # broken instrument, so the depth is pinned before anything else runs.
    own = os.path.join(ROOT, "trial", "human_walk", os.path.basename(__file__))
    if not os.path.isfile(own):
        print("SELFTEST_RED ROOT does not contain this file", ROOT)
        return 1
    print("ROOT_ARM", os.path.isdir(os.path.join(ROOT, "backend")) and os.path.isdir(os.path.join(ROOT, "frontend")))
    box = tempfile.mkdtemp(prefix="cmdr_gate_r119_")
    git("init", "-q", cwd=box)
    git("config", "user.email", "gate@example.invalid", cwd=box)
    git("config", "user.name", "gate", cwd=box)
    io.open(os.path.join(box, "mine.txt"), "w", encoding="utf-8").write("mine\n")
    io.open(os.path.join(box, "theirs.tsx"), "w", encoding="utf-8").write("theirs\n")
    git("add", "mine.txt", "theirs.tsx", cwd=box)
    git("commit", "-q", "-m", "seed", cwd=box)
    # The other writer stages their work and walks off; I then deliver only my own file.
    io.open(os.path.join(box, "theirs.tsx"), "a", encoding="utf-8").write("their new line\n")
    io.open(os.path.join(box, "mine.txt"), "a", encoding="utf-8").write("my new line\n")
    git("add", "theirs.tsx", cwd=box)
    msg = os.path.join(box, "msg.txt")
    io.open(msg, "w", encoding="utf-8").write("gate selftest delivery\n")
    # Control one: the shape of the mistake -- commit with no pathspec.  It must eat the foreign entry.
    git("add", "mine.txt", cwd=box)
    git("commit", "-q", "-m", "control no pathspec", cwd=box)
    control = committed_paths(git("rev-parse", "HEAD", cwd=box).strip(), box)
    git("reset", "--hard", "-q", "HEAD~1", cwd=box)
    # That reset took both edits out of the tree; put the foreign one back the way its owner left it, or
    # the control proves nothing about what the gate is meant to protect.
    io.open(os.path.join(box, "theirs.tsx"), "a", encoding="utf-8").write("their new line\n")
    io.open(os.path.join(box, "mine.txt"), "a", encoding="utf-8").write("my new line\n")
    git("add", "theirs.tsx", cwd=box)
    if "theirs.tsx" not in control:
        print("SELFTEST_RED the control did not reproduce the sweep"); return 1
    rc = land(msg, ["mine.txt"], box)
    after = staged(box)
    if rc != 0 or "theirs.tsx" not in after:
        print("SELFTEST_RED gate rc=%d foreign_left=%s" % (rc, sorted(after))); return 2
    head_paths = committed_paths(git("rev-parse", "HEAD", cwd=box).strip(), box)
    if head_paths != {"mine.txt"}:
        print("SELFTEST_RED gate committed", sorted(head_paths)); return 3
    # Control two: a path that is not in the tree is refused before anything is written.
    rc2 = land(msg, ["no-such-file.txt"], box)
    print("SELFTEST_CONTROL_TWO rc=%d expected=2" % rc2)
    if rc2 != 2:
        print("SELFTEST_RED gate accepted a path that does not exist"); return 4
    # Control four: a component whose relative import resolves to nothing must be refused,
    # and the very same delivery passes once the module itself is named with it.
    io.open(os.path.join(box, "broken.tsx"), "w", encoding="utf-8").write(
        'import { thing } from "./absent";\nexport const broken = thing;\n')
    rc3 = land(msg, ["broken.tsx"], box)
    print("SELFTEST_CONTROL_FOUR_REFUSE rc=%d expected=6" % rc3)
    if rc3 != 6:
        print("SELFTEST_RED the gate shipped an import that resolves to no module"); return 5
    io.open(os.path.join(box, "absent.ts"), "w", encoding="utf-8").write(
        "export const thing = 1;\n")
    rc4 = land(msg, ["broken.tsx", "absent.ts"], box)
    print("SELFTEST_CONTROL_FOUR_ACCEPT rc=%d expected=0" % rc4)
    if rc4 != 0:
        print("SELFTEST_RED the gate refused a delivery that named its own module"); return 6
    print("SELFTEST_OK control swept theirs.tsx into the commit; the gate committed only mine.txt, "
          "left theirs.tsx staged, refused a path that is not in the tree, refused an unresolvable "
          "import, and accepted it once the module was named too")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("-m", "--message-file")
    ap.add_argument("--expect-clean", action="store_true")
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.message_file or not a.paths:
        print("USE --selftest | -m <file> <paths...>")
        sys.exit(2)
    sys.exit(land(a.message_file, a.paths, ROOT, expect_clean=a.expect_clean))
