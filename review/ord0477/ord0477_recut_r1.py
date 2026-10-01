"""ORD-0477: re-cut the candidate onto the current authority tip, anchor by anchor.

Why a script and not hand edits: the authority line moved twice while this order was in flight
(`dcb90ccc` -> `d7a5ecee` -> the tip named by the commander), and every re-cut has to leave the same
four things true -- the door's bytes replaced from a uniquely anchored span, the tier vocabulary in one
place, the contract block re-applied, and the generated client carrying *only* this order's hunks.
Doing that by hand a third time is how a coordinate gets lost.

It refuses rather than guesses: every anchor must occur exactly once in the tip's own file, the
ORD-0402 byte pin must still find the segment r2 recorded, and the client sync gate (r3) must agree to
write.  A moved anchor means upstream changed this door -- a finding for the block, not something to
patch around.

usage: python ord0477_recut_r1.py <tip40>
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
SRC = LANE / "ord0477rb"  # the verified candidate this script carries forward
REPO = pathlib.Path(r"D:/moodle/CityNexus")
NODE = "node"
OATS = r"D:/moodle/CityNexus/frontend/node_modules/openapi-typescript/bin/cli.js"
NL = chr(10)

PRE_TIER_MARKER = '@app.get("/api/v1/journeys", response_model=list[JourneySchema])'
END_MARKER = '@app.delete("/api/v1/journeys/{journey_id}", status_code=204)'
REFUSAL_COMMENT = "#: ORD-0477: the name `GET /api/v1/journeys` answers when `sort` is neither absent nor a tier."
SCHEMA_ANCHOR = "class RecycleBinJourney(Journey):"
IMPORT_ANCHOR = "from app.schemas import (" + NL + "    Journey as JourneySchema," + NL + ")"
CONTRACT_GET_START = "  /journeys:" + NL + "    get:" + NL + "      operationId: listJourneys"
# `createJourney` is a prefix of another operation on this tree (`createJourneyCheckin`), so the end
# anchor carries its own line break -- without it the needle matches twice and the cut is ambiguous.
CONTRACT_GET_END = "    post:" + NL + "      operationId: createJourney" + NL

COPY_VERBATIM = [
    "backend/tests/test_qoder_ord0477_journey_sort.py",
    "backend/tests/test_qoder_ord0402_recycle_bin.py",
    "frontend/src/features/access/accessDoors.ts",
    "frontend/src/features/access/accessVocabulary.ts",
    "frontend/src/features/access/accessCopy.ts",
    "frontend/src/features/access/AccessPanel.tsx",
    "frontend/src/features/access/access.css",
    "frontend/e2e/qoder-ord0477-journey-list-sort.spec.ts",
    "review/ord0402-readouts/make_list_door_baseline_artifact_r2.py",
]
SHIPPED = [
    "backend/app/main.py",
    "backend/app/schemas.py",
    "backend/tests/test_qoder_ord0477_journey_sort.py",
    "backend/tests/test_qoder_ord0402_recycle_bin.py",
    "contracts/openapi.yaml",
    "frontend/src/generated/api.ts",
    "frontend/src/features/access/accessDoors.ts",
    "frontend/src/features/access/accessVocabulary.ts",
    "frontend/src/features/access/accessCopy.ts",
    "frontend/src/features/access/AccessPanel.tsx",
    "frontend/src/features/access/access.css",
    "frontend/e2e/qoder-ord0477-journey-list-sort.spec.ts",
    "review/ord0402-readouts/LIST_DOOR_BASELINE_r3.json",
    "review/ord0402-readouts/make_list_door_baseline_artifact_r2.py",
]


def show(tip: str, relative: str) -> str:
    done = subprocess.run(["git", "show", f"{tip}:{relative}"], capture_output=True, cwd=str(REPO))
    if done.returncode != 0:
        raise SystemExit("REFUSE: git show %s:%s -> %s" % (tip, relative, done.stderr[:300]))
    return done.stdout.decode("utf-8").replace("\r\n", "\n")


def require_once(text: str, needle: str, label: str) -> int:
    hits = text.count(needle)
    if hits != 1:
        raise SystemExit("REFUSE: the %s anchor occurs %d times, not once" % (label, hits))
    return text.index(needle)


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"[0-9a-f]{40}", sys.argv[1]):
        print(__doc__)
        return 2
    tip = sys.argv[1]
    dst = LANE / ("ord0477cut_" + tip[:8])
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", tip], capture_output=True, cwd=str(REPO))
    if archive.returncode != 0:
        raise SystemExit("REFUSE: git archive failed: %s" % archive.stderr[:300])
    untar = subprocess.run(["tar", "-x", "-C", str(dst)], input=archive.stdout)
    if untar.returncode != 0:
        raise SystemExit("REFUSE: export of %s did not land" % tip)
    notes = ["tip=%s" % tip, "export=%s bytes=%d" % (dst.name, len(archive.stdout))]

    for relative in COPY_VERBATIM:
        target = dst / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((SRC / relative).read_bytes())
    notes.append("copied verbatim: %d files" % len(COPY_VERBATIM))

    # ---------------------------------------------------------------- the door itself
    tip_main = show(tip, "backend/app/main.py")
    src_main = (SRC / "backend/app/main.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    r2 = json.loads((SRC / "review/ord0402-readouts/LIST_DOOR_BASELINE_r2.json").read_text(encoding="utf-8"))
    start = require_once(tip_main, PRE_TIER_MARKER, "pre-tier decorator")
    end = require_once(tip_main, END_MARKER, "delete decorator")
    if tip_main[start:end] != r2["segment_lf"]:
        raise SystemExit("REFUSE: the tip's list_journeys span is not what ORD-0402's r2 recorded")
    src_start = require_once(src_main, REFUSAL_COMMENT, "refusal comment")
    src_end = require_once(src_main, END_MARKER, "delete decorator (candidate)")
    patched = tip_main[:start] + src_main[src_start:src_end] + tip_main[end:]
    require_once(patched, IMPORT_ANCHOR, "schemas import block")
    patched = patched.replace(
        IMPORT_ANCHOR,
        "from app.schemas import (" + NL + "    JOURNEY_SORT_TIERS," + NL + ")" + NL + IMPORT_ANCHOR,
        1,
    )
    # `backend/app/main.py` is stored with CRLF on this line while every other file here is LF.  A
    # reader that normalises and writes back LF re-ships all 13 362 lines of it, which turns a 126-line
    # change into a whole-file rewrite in the diff -- so the tip's own convention is put back.
    tip_bytes = subprocess.run(
        ["git", "show", f"{tip}:backend/app/main.py"], capture_output=True, cwd=str(REPO)
    ).stdout
    crlf = tip_bytes.count(b"\r\n") > tip_bytes.count(b"\n") // 2
    payload = patched.replace(NL, "\r\n").encode("utf-8") if crlf else patched.encode("utf-8")
    (dst / "backend/app/main.py").write_bytes(payload)
    notes.append(
        "main.py: door span %d -> %d chars, helpers and refusal name carried with it; import added; "
        "line endings written back as %s" % (end - start, src_end - src_start, "CRLF" if crlf else "LF")
    )

    # ---------------------------------------------------------------- the tier vocabulary
    tip_schemas = show(tip, "backend/app/schemas.py")
    src_schemas = (SRC / "backend/app/schemas.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    if "JOURNEY_SORT_TIERS" in tip_schemas:
        raise SystemExit("REFUSE: the tip already carries JOURNEY_SORT_TIERS -- this order landed elsewhere")
    at_tip = require_once(tip_schemas, SCHEMA_ANCHOR, "RecycleBinJourney")
    block_start = require_once(src_schemas, "#: ORD-0477: the orders", "tier vocabulary block")
    block_end = require_once(src_schemas, SCHEMA_ANCHOR, "RecycleBinJourney (candidate)")
    (dst / "backend/app/schemas.py").write_text(
        tip_schemas[:at_tip] + src_schemas[block_start:block_end] + tip_schemas[at_tip:],
        encoding="utf-8",
        newline=NL,
    )
    notes.append("schemas.py: %d chars of tier vocabulary inserted" % (block_end - block_start))

    # ---------------------------------------------------------------- the hand contract
    tip_contract = show(tip, "contracts/openapi.yaml")
    src_contract = (SRC / "contracts/openapi.yaml").read_text(encoding="utf-8").replace("\r\n", "\n")
    if "RECENT_UPDATE" in tip_contract:
        raise SystemExit("REFUSE: the tip's contract already advertises the tiers")
    c_start = require_once(tip_contract, CONTRACT_GET_START, "contract listJourneys")
    c_end = require_once(tip_contract, CONTRACT_GET_END, "contract createJourney")
    s_start = require_once(src_contract, CONTRACT_GET_START, "contract listJourneys (candidate)")
    s_end = require_once(src_contract, CONTRACT_GET_END, "contract createJourney (candidate)")
    (dst / "contracts/openapi.yaml").write_text(
        tip_contract[:c_start] + src_contract[s_start:s_end] + tip_contract[c_end:], encoding="utf-8", newline=NL
    )
    notes.append("contracts/openapi.yaml: listJourneys block replaced (%d chars)" % (s_end - s_start))

    # ---------------------------------------------------------------- the generated client
    base_spec = LANE / ("run/ord0477_contract_%s_base.yaml" % tip[:8])
    base_spec.write_bytes(subprocess.run(
        ["git", "show", f"{tip}:contracts/openapi.yaml"], capture_output=True, cwd=str(REPO)
    ).stdout)
    gen_base = LANE / ("run/ord0477_api_%s_base.ts" % tip[:8])
    gen_mine = LANE / ("run/ord0477_api_%s_mine.ts" % tip[:8])
    for spec, out in ((base_spec, gen_base), (dst / "contracts/openapi.yaml", gen_mine)):
        done = subprocess.run([NODE, OATS, str(spec), "-o", str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if done.returncode != 0 or not out.exists():
            raise SystemExit("REFUSE: openapi-typescript failed on %s: %s" % (spec.name, done.stderr[:300]))
    sync = pathlib.Path(__file__).with_name("ord0477_api_sync_r3.py")
    checked = dst / "frontend/src/generated/api.ts"
    done = subprocess.run(
        [sys.executable, str(sync), str(gen_base), str(gen_mine), str(checked)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    notes.append("client sync: %s" % (done.stdout.strip().splitlines() or ["no output"])[-1])
    if done.returncode != 0:
        raise SystemExit("REFUSE: the client sync gate refused -- %s" % (done.stdout or done.stderr)[-700:])
    base_spec.unlink(missing_ok=True)

    # ---------------------------------------------------------------- the ORD-0402 byte pin
    gen_path = dst / "review/ord0402-readouts/make_list_door_baseline_artifact_r2.py"
    gen_path.write_text(
        re.sub(r'TIER_TIP = "[0-9a-f]{40}"', 'TIER_TIP = "%s"' % tip, gen_path.read_text(encoding="utf-8")),
        encoding="utf-8",
        newline=NL,
    )
    arm_path = dst / "backend/tests/test_qoder_ord0402_recycle_bin.py"
    arm_path.write_text(
        re.sub(r'BASELINE_TIP = "[0-9a-f]{40}"', 'BASELINE_TIP = "%s"' % tip, arm_path.read_text(encoding="utf-8")),
        encoding="utf-8",
        newline=NL,
    )
    done = subprocess.run([sys.executable, str(gen_path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("REFUSE: the pin re-record refused: %s" % (done.stdout or done.stderr)[-700:])
    record = json.loads((dst / "review/ord0402-readouts/LIST_DOOR_BASELINE_r3.json").read_text(encoding="utf-8"))
    notes.append(
        "pin re-recorded against %s: segment_sha256=%s pre_tier=%s"
        % (tip[:8], record["segment_sha256"][:16], record["pre_tier_segment_sha256"][:16])
    )

    # ---------------------------------------------------------------- the shipped bytes, read back
    manifest = []
    for relative in SHIPPED:
        path = dst / relative
        blob = subprocess.run(
            ["git", "hash-object", "-w", "--no-filters", str(path)], capture_output=True, text=True, cwd=str(REPO)
        ).stdout.strip()
        if len(blob) != 40:
            raise SystemExit("REFUSE: no blob id for %s" % relative)
        manifest.append({"path": relative, "blob": blob, "bytes": path.stat().st_size})
    out = dst / "review/ord0477/RECUT_MANIFEST_r1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"tip": tip, "files": manifest}, ensure_ascii=False, indent=2) + NL, encoding="utf-8", newline=NL)
    notes.append("manifest: %d shipped files with blob ids" % len(manifest))
    (LANE / "run/ord0477_recut_r1.txt").write_text(NL.join(notes) + NL, encoding="utf-8", newline=NL)
    print("RECUT OK", tip[:8], "->", dst.name)
    print(NL.join(notes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
