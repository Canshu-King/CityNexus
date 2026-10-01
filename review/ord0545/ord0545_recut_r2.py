"""ORD-0545 r2 recut -- drop the badge's two dictionary entries on the bytes the line holds NOW.

Why r2 exists: the landing sequencer refused r1 for one file, and the file is the same hot one as
before.  Measured, not inferred: r1 edited LocaleContext blob
cec0651cb5d9e0d0df0f71ce4c2ca0f07bea379f (its base, the tip I read at 16:0x), while the current tip
dc9dc10fa769bd8c4f3712d9be0dacc2d54d29d5 holds 2d6c58d048bae9d10779127bf50a146c51d4b0ab, moved by
ORD-0542's commit 3d900cda at 15:58 -- landed after I read the tip, before the door read it.  The
panel and the copy table did not move at all; only the dictionary did, one added line above my anchor.

The deletion is not the interesting part.  What makes this an honest re-cut is the order it is proved
in:

  1. the bytes I am about to edit hash to the tip's own blob for that path -- r1 could not say this;
  2. the two entries I remove are exactly the seven lines ORD-0533 added, no more;
  3. the sentences survive: the halves I am deleting are byte-equal to the pair already in
     `poiImportCopy.ts`, so this is a move and not a reword;
  4. nothing else in the file changes -- rebuild the result minus my removal and compare;
  5. LF survives.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0545/ord0545_recut_r2.py
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TIP = "dc9dc10fa769bd8c4f3712d9be0dacc2d54d29d5"
DIC = "frontend/src/i18n/LocaleContext.tsx"
TABLE = "frontend/src/features/poiimport/poiImportCopy.ts"
PANEL = "frontend/src/features/poiimport/PoiImportPanel.tsx"
R1_BASE_BLOB = "cec0651cb5d9e0d0df0f71ce4c2ca0f07bea379f"
KEY_LINE = '"poiImport.channelLocal":'

EN_REMOVAL = (
    "  // ORD-0533: this badge is rendered by PoiImportPanel.tsx and had no entry in either book, so the\n"
    "  // key name itself was what the traveller read.  The words below say only what this screen already\n"
    "  // promises elsewhere (scopeHint and unsupportedNoFetch): nothing is opened, nothing is fetched.\n"
    '  "poiImport.channelLocal": "Local parse, no links opened",\n'
)
ZH_REMOVAL = (
    "  // ORD-0533：这枚徽章由 PoiImportPanel.tsx 渲染，两本里都没有它，所以旅客读到的是键名本身。\n"
    "  // 下面这句只复述这一屏已经说过的话（scopeHint 与 unsupportedNoFetch）：不打开、不抓取。\n"
    '  "poiImport.channelLocal": "本地解析，不打开链接",\n'
)


def blob_of(data: bytes) -> str:
    return subprocess.run(["git", "hash-object", "-w", "--stdin"], input=data,
                          capture_output=True, check=True).stdout.decode().strip()


def show(rev: str, path: str) -> bytes:
    finished = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True, check=True)
    return finished.stdout


def tip_blob(rev: str, path: str) -> str:
    return subprocess.run(["git", "rev-parse", f"{rev}:{path}"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def entry_value(line: str) -> str:
    _, _, tail = line.partition('": "')
    return tail.rstrip(",").rstrip('"')


def table_pair(text: str) -> tuple[str, str]:
    body = text.split("const COPY: Record<PoiImportCopyKey, { zh: string; en: string }> = {")[1]
    open_marker = "\n  channelLocal: {"
    at = body.index(open_marker) + len(open_marker)
    block = body[at: body.index("\n  }", at)]
    def half(name: str) -> str:
        start = block.index(f'{name}: "') + len(name) + 3
        return block[start: block.index('"', start)]
    return half("zh"), half("en")


def main() -> int:
    path = ROOT / DIC
    original = path.read_bytes()

    # 1. the bytes under my edit are the tip's bytes -- the exact condition r1 could not meet
    assert blob_of(original) == tip_blob(TIP, DIC), (blob_of(original), tip_blob(TIP, DIC))
    assert tip_blob(TIP, DIC) != R1_BASE_BLOB, "the tip is still r1's base; nothing to re-cut"

    before = original.decode("utf-8")
    entries = [line for line in before.splitlines() if KEY_LINE in line]
    assert len(entries) == 2, len(entries)
    for chunk in (EN_REMOVAL, ZH_REMOVAL):
        assert before.count(chunk) == 1, chunk[:40]

    after = before.replace(EN_REMOVAL, "", 1).replace(ZH_REMOVAL, "", 1)

    # 2 and 4: only those seven lines go, nothing else moves
    removed = [line for line in before.splitlines() if line not in after.splitlines()]
    added = [line for line in after.splitlines() if line not in before.splitlines()]
    assert len(removed) == 7 and not added, (len(removed), added)
    assert after.count(KEY_LINE) == 0, "an entry survived the removal"

    # 3: the words survive elsewhere, byte for byte -- this is a move, not a reword
    table_text = (ROOT / TABLE).read_text(encoding="utf-8")
    zh_pair, en_pair = table_pair(table_text)
    deleted = {entry_value(line) for line in entries}
    assert {zh_pair, en_pair} == deleted, (zh_pair, en_pair, sorted(deleted))

    # 5: the call site already reads the table, so no window is left without a sentence
    panel_text = (ROOT / PANEL).read_text(encoding="utf-8")
    assert '{poiImportCopy(locale, "channelLocal")}' in panel_text
    assert 't("poiImport.channelLocal")' not in panel_text

    new_bytes = after.encode("utf-8")
    assert b"\r" not in new_bytes, "the removal introduced a CR into an LF file"
    path.write_bytes(new_bytes)
    written = path.read_bytes()
    assert blob_of(written) == blob_of(new_bytes)

    print(
        "tip_blob=" + tip_blob(TIP, DIC) + "\n"
        "r1_base_blob=" + R1_BASE_BLOB + " (different, which is why r1 was refused)\n"
        "bytes_before=%d bytes_after=%d\n"
        "lines_removed=%d lines_added=%d entries_left=%d\n"
        "deleted_values=%s\n"
        "table_pair_values=%s moved_not_reworded=true\n"
        "cr_introduced=0 edited_foreign_lines=0"
        % (
            len(original), len(written), len(removed), len(added), after.count(KEY_LINE),
            sorted(deleted), [zh_pair, en_pair],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
