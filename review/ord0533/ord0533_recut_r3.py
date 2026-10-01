"""ORD-0533 r3 recut -- re-apply this order's dictionary insert onto the bytes the line actually holds.

Why this file exists: the landing sequencer refused r2 with "1 file does not merge onto the lane's own
generation bytes", and the named file is `frontend/src/i18n/LocaleContext.tsx`.  Measured here rather
than guessed: the blob at r2's base is ae26f33aa3753b93a91ecbfc4da1e56713ddcb51 while the current tip
holds 1908117c, moved by ORD-0528's commit.  A three-way merge calls that clean (it does -- `git
merge-tree` returns a tree with no conflict section), and the sequencer still refuses it, because an
insert carried from a stale generation is not the same claim as an insert made on the bytes that are
actually there.  So this tool does the second thing.

The rules it enforces are the ones the order set for this hot file:

* contiguous insert only -- this order's lines are added, none of another lane's lines are edited,
  and that is proved by rebuilding the original bytes from the result and comparing, not asserted in
  prose;
* anchors must be unique, so an insert cannot land in the wrong book;
* the counts the delivery quotes are derived from the file (keys per book before and after), because
  the r1 block quoted a number that counted the wrong thing;
* the base bytes are checked against the tip's own blob, which is the exact equality the door wants;
* line endings survive: this file is LF on this line since ORD-0532, and a rewrite that flips it
  would be the same defect ORD-0526 just hit with `.gitignore`.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0533/ord0533_recut_r3.py
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = ROOT / "frontend/src/i18n/LocaleContext.tsx"
TIP = "514b397f96f3b5165b24865f4a544ab6f8020084"
R2_BASE_BLOB = "ae26f33aa3753b93a91ecbfc4da1e56713ddcb51"

EN_ANCHOR = '  "poiImport.channelLabel": "Channel",'
ZH_ANCHOR = '  "poiImport.channelLabel": "通道",'

EN_INSERT = (
    "  // ORD-0533: this badge is rendered by PoiImportPanel.tsx and had no entry in either book, so the\n"
    "  // key name itself was what the traveller read.  The words below say only what this screen already\n"
    "  // promises elsewhere (scopeHint and unsupportedNoFetch): nothing is opened, nothing is fetched.\n"
    '  "poiImport.channelLocal": "Local parse, no links opened",\n'
)
ZH_INSERT = (
    "  // ORD-0533：这枚徽章由 PoiImportPanel.tsx 渲染，两本里都没有它，所以旅客读到的是键名本身。\n"
    "  // 下面这句只复述这一屏已经说过的话（scopeHint 与 unsupportedNoFetch）：不打开、不抓取。\n"
    '  "poiImport.channelLocal": "本地解析，不打开链接",\n'
)
KEY = '"poiImport.channelLocal":'


def blob_of(data: bytes) -> str:
    finished = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"], input=data, capture_output=True, check=True
    )
    return finished.stdout.decode().strip()


def count_key(text: str) -> int:
    # The entries are indented, so a bare "\n" + key probe never matches -- the first cut of this
    # helper made `count_key(before) == 0` pass for the wrong reason.  Match the declaration shape.
    return sum(1 for line in text.splitlines() if line.strip().startswith(KEY))


def main() -> int:
    original = TARGET.read_bytes()
    before = original.decode("utf-8")
    digest_before = hashlib.sha256(original).hexdigest()

    # 1. the bytes I am inserting into are the tip's bytes, not my old generation's
    tip_blob = subprocess.run(
        ["git", "rev-parse", f"{TIP}:frontend/src/i18n/LocaleContext.tsx"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert blob_of(original) == tip_blob, (blob_of(original), tip_blob)
    assert tip_blob != R2_BASE_BLOB, "r2's base blob is still in place; nothing to re-cut"

    # 2. the defect is still live on these bytes
    assert count_key(before) == 0, count_key(before)

    # 3. one anchor per book, so the insert cannot land in the wrong list
    for anchor in (EN_ANCHOR, ZH_ANCHOR):
        assert before.count("\n" + anchor + "\n") == 1, anchor[:40]

    after = before.replace(
        "\n" + EN_ANCHOR + "\n", "\n" + EN_ANCHOR + "\n" + EN_INSERT, 1
    ).replace(
        "\n" + ZH_ANCHOR + "\n", "\n" + ZH_ANCHOR + "\n" + ZH_INSERT, 1
    )

    # 4. derived counts, not transcribed ones: one key per book, seven lines added, nothing else touched
    assert count_key(after) == 2, count_key(after)
    lines_before, lines_after = before.splitlines(), after.splitlines()
    added = len(lines_after) - len(lines_before)
    assert added == len(EN_INSERT.splitlines()) + len(ZH_INSERT.splitlines()), added
    stripped = [line for line in lines_after if line not in
                (EN_INSERT + ZH_INSERT).splitlines()]
    assert stripped == lines_before, "this insert edited somebody else's line"

    new_bytes = after.encode("utf-8")
    assert b"\r" not in new_bytes, "the insert introduced a CR into an LF file"
    TARGET.write_bytes(new_bytes)
    restored = TARGET.read_bytes()
    assert hashlib.sha256(restored).hexdigest() == hashlib.sha256(new_bytes).hexdigest()

    print(
        f"base_blob_at_tip={tip_blob}\n"
        f"local_bytes_sha256_before={digest_before}\n"
        f"local_bytes_sha256_after={hashlib.sha256(restored).hexdigest()}\n"
        f"lines_added={added} keys_now_in_books={count_key(after)}\n"
        f"anchors={'channelLabel en+zh'} edited_foreign_lines=0 cr_introduced=0"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
