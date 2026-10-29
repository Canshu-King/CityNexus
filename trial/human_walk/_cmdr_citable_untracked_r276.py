"""bw276: resolve the citations the audit lists as present-but-untracked into real paths.

Section 14.23 names thirty-three documents that are cited by the shift reports but never
committed.  The audit prints the cited name, which is often a bare basename, so this ruler
maps each name back to the file on disk under trial/, reports what it would cost to commit
them, and refuses to guess when a name answers to more than one path.
"""

import io
import json
import os
import re
import subprocess
import sys

TREE = r"D:\moodle\_cmdr_rescue_v3_1022"
AUDIT = os.path.join(TREE, "trial", "results", "20261026_gozero",
                     "by179-cited-artifact-audit.txt")
RECEIPT = os.path.join(TREE, "trial", "results", "20261026_gozero",
                       "bw276-citable-untracked-paths.txt")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    names = []
    for line in io.open(AUDIT, encoding="utf-8").read().splitlines():
        match = re.match(r"^\s+present-but-untracked\s+(\S+)", line)
        if match:
            names.append(match.group(1))
    # A parsed artifact name always carries an extension.  Taking the wrong field once
    # handed back "(cited", which then resolved to nothing and looked like an empty result
    # rather than a broken reader.
    malformed = [name for name in names if "." not in os.path.basename(name)]
    if not names or malformed:
        print("ABORT the audit lines did not parse cleanly: %d names, %d malformed %s"
              % (len(names), len(malformed), malformed[:3]))
        return 8

    index = {}
    for dirpath, dirnames, filenames in os.walk(os.path.join(TREE, "trial")):
        dirnames[:] = [d for d in dirnames if d not in {"__pycache__", "node_modules",
                                                        ".pytest_cache"}]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, TREE).replace("\\", "/")
            index.setdefault(name, []).append(rel)

    resolved, ambiguous, absent = [], [], []
    for name in sorted(set(names)):
        candidates = [c for c in index.get(os.path.basename(name), [])]
        if not candidates:
            absent.append(name)
        elif len(candidates) == 1:
            full = os.path.join(TREE, candidates[0])
            resolved.append((candidates[0], os.path.getsize(full)))
        else:
            # A cited name that matches several files is not something to commit blind.
            ambiguous.append((name, candidates))

    total = sum(size for _path, size in resolved)
    tracked = set(subprocess.run(["git", "-C", TREE, "ls-files"], capture_output=True,
                                 text=True, errors="replace").stdout.split())
    already = [row for row in resolved if row[0] in tracked]
    to_add = [row for row in resolved if row[0] not in tracked]

    lines = [
        "CITABLE UNTRACKED ARTIFACTS bw276",
        "CITED_NAMES_FROM_AUDIT %d" % len(set(names)),
        "RESOLVED_TO_ONE_PATH %d  AMBIGUOUS %d  NO_FILE_FOUND %d"
        % (len(resolved), len(ambiguous), len(absent)),
        "ALREADY_TRACKED %d  STILL_UNTRACKED %d" % (len(already), len(to_add)),
        "BYTES_TO_ADD %d (%.2f MiB)" % (total, total / 1048576.0),
        "LARGEST_FIVE %s" % json.dumps(
            [(p, s) for p, s in sorted(to_add, key=lambda r: -r[1])[:5]],
            ensure_ascii=False),
        "PATHS_STILL_UNTRACKED",
    ]
    lines.extend("  %s" % path for path, _size in sorted(to_add))
    if ambiguous:
        lines.append("AMBIGUOUS_NAMES (not committed blind)")
        lines.extend("  %s -> %s" % (name, ", ".join(cands)) for name, cands in ambiguous)
    if absent:
        lines.append("NO_FILE_ON_DISK_UNDER_TRIAL")
        lines.extend("  %s" % name for name in absent)
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines[:12]:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
