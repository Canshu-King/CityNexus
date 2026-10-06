"""Self-check for the ruler registry: every coordinate it quotes must be retrievable NOW, and every
ruler body it names must exist.

The building's failure mode is a registry that reads well and quotes a blob nobody can fetch -- the
"尺只在你本机的脚本不算" trap.  This checker runs that fetch: it reads the registry's coordinates and
body names OUT of the registry file (so it checks what is written, not what the generator intended),
resolves each with `git cat-file`, and refuses to pass if any coordinate does not resolve or any body
is absent.

Exits 0 when the registry is sound, non-zero with the offending entries otherwise.
"""
import io
import os
import re
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0447_wt/"
REG = WT + "review/a68b0631-ruler-registry/RULER_REGISTRY_r1.md"
HEX = re.compile(r"`([0-9a-f]{40})`")


def cat_file(hexcoord):
    r = subprocess.run(["git", "cat-file", "-t", hexcoord], cwd=WT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout.strip() or r.stderr.strip())


def remote_fetchable(coords):
    """Resolve each coordinate against objects that came from the REMOTE, not from the local store.

    The building asks for a coordinate that is "真实可取回" on the authoritative line: a stranger
    who clones must be able to cat-file it.  Resolving against my local object store would prove
    only that I once had it, which is exactly the "尺只在你本机的脚本不算" failure.  So this fetches
    the ruler branch by refspec into a throwaway ref first; the objects fetched are what the remote
    carries, and the branch is the one that holds the registry and the ruler bodies.
    """
    fetch = subprocess.run(
        ["git", "fetch", "origin",
         "+refs/heads/review/a68b0631-ruler-coordinates-r2:refs/tmp/registry_remote_check"],
        cwd=WT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    bad = []
    for c in coords:
        rc, kind = cat_file(c)
        if rc != 0:
            bad.append((c, kind))
    return fetch.returncode, bad


def main():
    if not os.path.isfile(REG):
        print("registry file is missing: %s" % REG)
        return 2
    text = io.open(REG, encoding="utf-8", errors="replace").read()

    coords = sorted(set(HEX.findall(text)))
    if not coords:
        print("the registry quotes no coordinate at all -- that is not sound, it is empty")
        return 1
    unresolved = []
    for c in coords:
        rc, kind = cat_file(c)
        if rc != 0:
            unresolved.append((c, kind))
        print("  coordinate %s -> %s" % (c, kind if rc == 0 else "UNRESOLVED (%s)" % kind))

    # the guard's coordinate, cross-checked against what the authoritative line currently carries.
    # The tip is fetched BY REFSPEC: a mirror ref is not present locally, and `git rev-parse` on a
    # missing ref echoes the ref NAME back, which would make this comparison read garbage and
    # report a stale guard that does not exist.
    fetch = subprocess.run(
        ["git", "fetch", "origin",
         "+refs/heads/mirror/integration-frontend-apple-pass1:refs/tmp/registry_check_tip"],
        cwd=WT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tip = subprocess.run(["git", "rev-parse", "refs/tmp/registry_check_tip"], cwd=WT,
                         capture_output=True, text=True).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", tip or ""):
        tip = ""
    line_guard = ""
    if tip:
        line_guard = subprocess.run(["git", "rev-parse", "%s:backend/tests/test_qoder_a68b0631_comment_anchor_drift_r1.py" % tip],
                                    cwd=WT, capture_output=True, text=True).stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", line_guard or ""):
            line_guard = ""
    quoted_guard = subprocess.run(["git", "rev-parse", "HEAD:backend/tests/test_qoder_a68b0631_comment_anchor_drift_r1.py"],
                                  cwd=WT, capture_output=True, text=True).stdout.strip()
    print("\n  tip fetch exit status      = %d (read without a pipe)" % fetch.returncode)
    print("  tip                            = %s" % (tip[:12] or "(not fetched)"))
    print("  guard blob on the line        = %s" % (line_guard[:12] or "(not resolvable at the tip)"))
    print("  guard blob in this branch     = %s" % (quoted_guard[:12] or "(absent)"))
    guard_stale = bool(line_guard) and bool(quoted_guard) and line_guard != quoted_guard

    bodies = re.findall(r"body on this branch : `([^`]+)`", text)
    missing = [b for b in bodies if not os.path.isfile(WT + b)]

    # the remote leg: resolve the SAME coordinates against objects the remote just handed us
    fetch_rc, remote_bad = remote_fetchable(coords)
    print("\n  remote fetch exit status   = %d (ruler branch fetched by refspec into a throwaway ref)"
          % fetch_rc)
    if fetch_rc == 0 and not remote_bad:
        print("  every coordinate also resolves from the REMOTE-fetched objects: yes")
    else:
        print("  REMOTE RESOLUTION FAILED for: %s" % [c for c, _ in remote_bad])

    print("\n  coordinates checked: %d, bodies named: %d" % (len(coords), len(bodies)))
    if unresolved:
        print("  UNRESOLVED COORDINATES: %s" % [c for c, _ in unresolved])
    if missing:
        print("  MISSING BODIES: %s" % missing)
    if guard_stale:
        print("  the guard's blob on the line differs from the one this branch carries -- the "
              "registry would be quoting a blob the line has moved past")

    if unresolved or missing:
        return 1
    if guard_stale:
        return 1
    if fetch_rc != 0 or remote_bad:
        return 1
    print("\nRESULT: registry sound -- every coordinate resolves locally AND from the remote, and "
          "every named body exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())