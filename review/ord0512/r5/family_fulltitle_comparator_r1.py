"""ORD-0512 family comparison, full titles r1 -- two logs' red sets compared as multisets of whole titles.

The family diff this lane ships cuts each title at its first em dash, because several accepted map gates
carry a dash inside a title. That is right for naming arms and wrong for counting them: three widths of one
arm (`@360`, `@390`, `@414`) collapse into a single `reach`, and two generations whose failure counts differ
by three then read as identical sets. This keeps the whole title and compares multisets, so a difference in
how many times an arm ran cannot hide.

usage: python ord0512_family_fulltitle_r1.py <base.log> <candidate.log> [out.json]
"""
import io
import json
import re
import sys
from collections import Counter

BLOCK = re.compile(r"^\s{4}\[([a-z-]+)\] › (\S+) › (\S.*)$", re.M)


def items(path):
    text = io.open(path, encoding="utf-8", errors="replace").read()
    return ["%s :: %s :: %s" % (project, location.replace("\\", "/"), title.strip())
            for project, location, title in BLOCK.findall(text)]


def main() -> int:
    base, cand = items(sys.argv[1]), items(sys.argv[2])
    cb, cc = Counter(base), Counter(cand)
    out = {
        "base_failures": len(base),
        "candidate_failures": len(cand),
        "distinct_base": len(cb),
        "distinct_candidate": len(cc),
        "only_on_base_full_titles": sorted((cb - cc).elements()),
        "only_on_candidate_full_titles": sorted((cc - cb).elements()),
        "base_set": sorted(cb),
        "candidate_set": sorted(cc),
        "parser": "full title, multiset; no truncation at the em dash",
    }
    text = json.dumps(out, indent=1, ensure_ascii=False)
    if len(sys.argv) > 3:
        io.open(sys.argv[3], "w", encoding="utf-8", newline="\n").write(text)
    sys.stdout.buffer.write((text[:1200] + "\n").encode("utf-8", "replace"))
    print("WROTE=%s" % (sys.argv[3] if len(sys.argv) > 3 else "stdout only"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
