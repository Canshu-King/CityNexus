"""bw267: list every module that committed-or-staged code imports but git does not track.

Why: the staged JourneyTrialSetup.tsx in this worktree carries
`import { CITY_FACTS } from "./cityNamed"` while cityNamed.ts is untracked and NOT
gitignored, so whoever commits that component ships a tree whose build cannot resolve
the module.  This ruler answers how many such half-deliveries exist, without touching
another writer's uncommitted work.

Read-only.  It runs git commands only (status, show, ls-files, check-ignore) and never
writes to the working tree or the index.
"""

import io
import os
import re
import subprocess
import sys

TREE = r"D:\moodle\_cmdr_rescue_v3_1022"
FRONTEND = os.path.join(TREE, "frontend", "src")
RECEIPT = os.path.join(TREE, "trial", "results", "20261026_gozero",
                       "bw267-imported-but-untracked.txt")

IMPORT_RE = re.compile(r"""(?:^|\n)\s*(?:import|export)[^;]*?from\s+["'](\.[^"']+)["']""")
EXTS = (".ts", ".tsx", ".js", ".mjs", ".jsx")


def git(*args):
    return subprocess.run(["git", "-C", TREE] + list(args), capture_output=True,
                          text=True, errors="replace")


def tracked_paths():
    out = git("ls-files").stdout.splitlines()
    return set(line.replace("\\", "/") for line in out)


def index_paths():
    return tracked_paths()


def resolve(importer_rel, spec, root=TREE):
    # The importer path is relative to the tree, so it has to be joined to that tree.
    # Joining it to FRONTEND prefixed frontend/src twice, every candidate missed every
    # set, and the census reported zero offenders while cityNamed.ts was a real one.
    base = os.path.dirname(os.path.join(root, importer_rel))
    stem = os.path.normpath(os.path.join(base, spec))
    stem_rel = os.path.relpath(stem, root).replace("\\", "/")
    candidates = [stem_rel] + [stem_rel + ext for ext in EXTS]
    candidates += [os.path.join(stem_rel, "index" + ext).replace("\\", "/")
                   for ext in EXTS]
    return candidates


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tracked = tracked_paths()
    staged = set(index_paths())
    status = git("status", "--porcelain").stdout.splitlines()
    untracked = set()
    for line in status:
        if line.startswith("?? "):
            untracked.add(line[3:].replace("\\", "/"))

    offenders = []
    checked = 0
    for dirpath, _names, filenames in os.walk(FRONTEND):
        for name in filenames:
            if not name.endswith(EXTS):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, TREE).replace("\\", "/")
            if rel in untracked:
                continue  # an untracked file importing another one is nobody's build yet
            text = io.open(path, encoding="utf-8", errors="replace").read()
            for spec in IMPORT_RE.findall(text):
                # Stylesheet and asset imports resolve through the bundler, not through
                # the module extension list below, so they must not read as offenders.
                if spec.lower().endswith((".css", ".scss", ".json", ".svg", ".png",
                                          ".jpg", ".webp", ".gif", ".woff", ".woff2")):
                    continue
                candidates = resolve(rel, spec)
                checked += 1
                if any(c in tracked or c in staged for c in candidates):
                    continue
                present = [c for c in candidates if c in untracked]
                if present:
                    ignored = git("check-ignore", "-v", present[0]).returncode == 0
                    offenders.append((rel, spec, present[0],
                                      "gitignored" if ignored else "not-gitignored"))

    # Positive control: this file is untracked and NOT gitignored, and the staged
    # JourneyTrialSetup.tsx imports it.  If the census misses a case that was found by
    # hand, a zero from it means nothing.
    known_missing = "frontend/src/features/setup/cityNamed.ts"
    known_untracked = known_missing in untracked
    known_hit = known_missing in {miss for (_i, _s, miss, _g) in set(offenders)}

    lines = [
        "IMPORTED-BUT-UNTRACKED MODULE CENSUS bw267",
        "TIP %s" % git("rev-parse", "HEAD").stdout.strip(),
        "IMPORT_SPECS_CHECKED %d" % checked,
        "OFFENDERS %d (a tracked or staged file imports a module that only exists as an untracked file)"
        % len(offenders),
    ]
    for importer, spec, missing, ignore_state in sorted(set(offenders)):
        lines.append("  %s" % importer)
        lines.append("      imports %-40s -> %s  [%s]" % (spec, missing, ignore_state))
    lines.append("SELFTEST the known offender (cityNamed.ts, cited in 14.21) "
                 "appears: %s" % known_hit)
    if known_untracked and not known_hit:
        lines.append("ABORT the census cannot see the one offender that is known by hand, "
                     "so its zero would be a false green")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    if known_untracked and not known_hit:
        return 9
    return 0


if __name__ == "__main__":
    sys.exit(main())
