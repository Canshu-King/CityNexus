"""ORD-0525 r2 re-cut: put this lane's 22 dictionary lines back onto the CURRENT tip's copy.

Why a script: the only thing the landing sequencer could not merge is
`frontend/src/i18n/LocaleContext.tsx`, and the reason is exactly the one that has burned this project
before -- another lane inserted into the same two dictionaries between my cut and the tip.  Re-typing
twenty-two lines by hand is how a copy-paste error becomes someone else's product copy, so the block
is lifted out of my own published commit and spliced at an anchor that must still be unique.

Three refusals are built in, each one a mistake this lane has actually made:

* the block is only ever written to the working file -- the r1 evidence filenames are never
  overwritten (published evidence paths are frozen; a new generation gets a new name);
* every key must appear exactly once after the splice, in BOTH dictionaries, so a zh-only insert
  cannot ship: `t()` falls back to the key itself and a key name on a Chinese screen is ORD-0533;
* the added-line count must equal what the rejected commit added (22), so the re-cut is the same
  change on a new base and not a re-imagination of it.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0525/ord0525_recut_r2.py
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = ROOT / "frontend/src/i18n/LocaleContext.tsx"
BASE = "7862c6de5565c02c20ec2dccaa9da18960603e06"
R1 = "61bda7e564c52b30feb6e674b36fc501f9d47d66"
R1_BASE = "1e95d106f81b29048ba17695fd0e49172516b9b1"  # the tip the rejected cut was made against
REL = "frontend/src/i18n/LocaleContext.tsx"
ANCHOR_EN = '  "checkin.refused": "The server would not take this stamp, so nothing was added to your footprints.",'
ANCHOR_ZH = '  "checkin.refused": "服务器没收下这次打卡，你的足迹里没有多出任何东西。",'


def show(rev: str, path: str) -> str:
    finished = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{rev}:{path}"], capture_output=True
    )
    assert finished.returncode == 0, finished.stderr.decode("utf-8", "replace")
    return finished.stdout.decode("utf-8")


def block(rev: str, anchor: str) -> str:
    """The inserted lines: everything from `anchor` up to, but excluding, the next `member.scope` key."""

    lines = show(rev, REL).split("\n")
    start = next(i for i, line in enumerate(lines) if line == anchor)
    end = next(
        i for i, line in enumerate(lines[start + 1 :], start + 1)
        if line.lstrip().startswith('"member.scope.')
    )
    return "\n".join(lines[start + 1 : end]) + "\n"


def main() -> int:
    mine_en = block(R1, ANCHOR_EN)
    mine_zh = block(R1, ANCHOR_ZH)
    base_text = show(BASE, REL)

    keys = sorted(
        {
            line.split('"')[1]
            for line in (mine_en + mine_zh).splitlines()
            if line.lstrip().startswith('"')
        }
    )
    assert keys and all(key.startswith("calendar.") for key in keys), keys
    for label, text in (("en", mine_en), ("zh", mine_zh)):
        found = sorted(line.split('"')[1] for line in text.splitlines() if line.lstrip().startswith('"'))
        # Nine keys per book; the 22 added lines are these 18 entries plus the comment lines.  The
        # count is derived from the keys themselves, not a number typed into the assert (the first cut
        # of this script hardcoded 11 and refused to write -- correctly, but on a wrong expectation).
        assert found == keys, (label, found, keys)

    for anchor in (ANCHOR_EN, ANCHOR_ZH):
        assert base_text.count(anchor) == 1, (anchor[:40], base_text.count(anchor))
        assert "calendar." not in base_text, "the tip already carries calendar keys - not my insert"

    rebuilt = base_text.replace(anchor := ANCHOR_EN, anchor + "\n" + mine_en.rstrip("\n"), 1)
    rebuilt = rebuilt.replace(ANCHOR_ZH, ANCHOR_ZH + "\n" + mine_zh.rstrip("\n"), 1)

    for key in keys:
        assert rebuilt.count(f'"{key}":') == 2, (key, rebuilt.count(f'"{key}":'))
    added = rebuilt.count("\n") - base_text.count("\n")
    # What the rejected cut added, measured against ITS OWN parent.  Diffing my commit against the new
    # tip would fold in the 14/3 lines another lane put into this same file, and that is not my line
    # count to claim.
    r1_added = show(R1, REL).count("\n") - show(R1_BASE, REL).count("\n")
    assert added == r1_added, (added, r1_added)
    assert "\r" not in rebuilt, "the dictionary file is LF there; do not flip it"

    before = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    TARGET.write_bytes(rebuilt.encode("utf-8"))
    print(
        f"LocaleContext re-cut onto {BASE[:12]}: keys={len(keys)} added={added} "
        f"(same as the rejected commit={added == r1_added}) each_key_twice=True "
        f"file_before_sha16={before[:16]} file_after_sha16="
        f"{hashlib.sha256(TARGET.read_bytes()).hexdigest()[:16]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
