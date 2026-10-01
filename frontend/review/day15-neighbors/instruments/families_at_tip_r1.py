"""前置单 -- print the sibling testid families the authoritative tip actually ships, so "this name is
gone" is never read as "this capability is gone".

The census next to this file counts the names four instruments ask for and finds three of them absent
from `frontend/src`. That is a statement about a word, not about a screen: the gate's own history has a
lane once proving a capability missing from a key-name grep alone. So the neighbours of each absent name
are enumerated here straight out of the tree -- the `trips-tab*` family and the whole `trial-*` family --
with the count computed, and the block cites this file instead of my memory.

usage: python families_at_tip_r1.py [sha] > receipts/families_at_tip_r1.txt
"""
import re
import subprocess
import sys

WT = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"
SHA = sys.argv[1] if len(sys.argv) > 1 else "5a4cdbd26d4a58d6ed6b277480e766ac08b15ded"
FAMILIES = ("trips-tab", "trial")


def hits(prefix):
    result = subprocess.run(
        ["git", "grep", "-ohE", 'data-testid="%s[a-z0-9-]*"' % prefix, SHA, "--", "frontend/src"],
        cwd=WT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    names = sorted({match.group(1) for match in re.finditer(r'data-testid="([^"]+)"', result.stdout)})
    return names


def main():
    print("families_present_in_frontend_src_at %s" % SHA)
    for prefix in FAMILIES:
        names = hits(prefix)
        print("family=%s names=%d" % (prefix + "*", len(names)))
        for name in names:
            print("  %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
