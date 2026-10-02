"""ORD-0512 counter-example harness r1 -- does each arm of the glass gate actually bite?

Every arm here could be satisfied by a product that paints nothing (the tip's behaviour), so the gate's
green means nothing until a mutant proves it reddens. Each case:

  1. reads the bytes of every file it is about to touch and keeps them, with their sha256;
  2. replaces one exact anchor -- and refuses if that anchor does not occur exactly once, because an
     anchor that silently stopped matching is how ORD-0477's `screen_stops_asking` mutant spent a round
     printing "No matches found" while the suite stayed green;
  3. runs the gate on this order's own ports with a fresh run-id database;
  4. writes the kept bytes back and re-hashes, so "reverted" is a fact about the file rather than a
     claim about intent.

M0 is the control that matters most for this order: the tip's own render path with my spec added. It is
what turns "the arm is green" into "the arm was red before this change and green after it", which is the
only reading that says the change is what made the difference.

usage: python ord0512_mutant_r1.py <case> [case...]
env:   ORD0512_TREE, ORD0512_PORTS (front,back)
"""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

TREE = pathlib.Path(os.environ.get("ORD0512_TREE") or r"D:/moodle/_qoder_b_ord0417_20260928/ord0512cut_1c785a2d")
RUN = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run")
GATE_DIR = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/gate")
EVIDENCE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/mutant")
SPEC = "e2e/qoder-0512-stop-names-on-the-glass.spec.ts"
MAP_PANEL = "frontend/src/components/v8/MapPanel.tsx"
SHARED_PANEL = "frontend/src/features/shared/SharedJourneyPanel.tsx"
LABELS_LIB = "frontend/src/lib/mapStopLabels.ts"
LABELS_CSS = "frontend/src/map-stop-labels.css"
TIP = os.environ.get("ORD0512_TIP") or "5a4cdbd26d4a58d6ed6b277480e766ac08b15ded"
PAIR = (os.environ.get("ORD0512_PORTS") or "5152,5153").split(",")
# which generation's bytes are being bitten; keeps a re-run from overwriting the reading it is compared
# against (the r1 logs are the before-picture for the two-sided placement rule)
GEN = os.environ.get("ORD0512_MUT_GEN") or "r1"

REVERT = "__REVERT_TO_TIP__"

CASES = {
    # M0, the control: the tip paints no stop name anywhere, so every name claim has to be red here and
    # any arm that comes back green is measuring something other than the glass.
    "base_paints_no_names": [
        (MAP_PANEL, REVERT, None),
        (SHARED_PANEL, REVERT, None),
    ],
    # M1: the chips are in the document but paint nothing -- an arm that read only attributes would
    # still be green, which is exactly why A1/A7 compare pixels.
    "labels_never_paint": [
        (LABELS_CSS, ".v8-map-panel .v8-map-stop-label {", ".v8-map-panel .v8-map-stop-label {\n  display: none;"),
    ],
    # M2: no crowding rule -- every name is placed whether or not it lands on another one.
    "no_crowding_rule": [
        (LABELS_LIB,
         "    const free = inFrame.find(({ box }) => !placed.some((entry) => overlaps(box, entry.box)));",
         "    const free = inFrame[0] as { box: LabelBox; index: number };"),
    ],
    # M3: the stop's identity token painted instead of its word.
    "name_replaced_by_id": [
        (MAP_PANEL, "        chip.textContent = label.text;", "        chip.textContent = point.id ?? label.text;"),
    ],
    # M6: the element claims a side fits when the placement rule says it does not -- the second
    # generation's own claim is that the reason is told, so a told lie has to be catchable.
    "the_reason_claims_a_side_that_fits": [
        (MAP_PANEL,
         '      node.el.setAttribute("data-fits-right", String(verdict.fits[0] === true));',
         '      node.el.setAttribute("data-fits-right", "true");'),
    ],
    # M7: the blocker is never named -- `over_a_name` with nothing standing there is the same class of
    # sentence as `off_map` while a side fits, arriving from the other direction.
    "the_blocker_is_never_named": [
        (MAP_PANEL,
         '      node.el.setAttribute("data-blocked-by", verdict.blocked_by ?? "nothing");',
         '      node.el.setAttribute("data-blocked-by", "nothing");'),
    ],
    # M5: only the right-hand side is ever considered -- r1's placement rule. The floor in
    # `crowding-hides` (5 names on the post-pick view at 390x844, where r1 reached 3) is what reddens.
    "one_sided_placement_only": [
        (LABELS_LIB,
         "    const inFrame = usable.filter(({ index }) => fits[index]);",
         "    const inFrame = usable.slice(0, 1).filter(({ box }) => !frame || inside(box, frame));"),
    ],
    # M4: the name folded into the pin -- the mistake `onlyDigitsPainted` guards, and the reason the
    # chip is its own marker.
    "name_moved_into_the_pin": [
        (MAP_PANEL, '        chip.className = "v8-map-stop-label";', '        chip.className = "v8-map-stop-label v9-map-marker";'),
    ],
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tip_bytes(rel: str) -> bytes:
    return subprocess.run(
        ["git", "-C", r"D:/moodle/CityNexus", "show", f"{TIP}:{rel}"],
        capture_output=True, check=True,
    ).stdout


def run_gate(case: str) -> dict:
    run_id = f"ord0512{GEN}m_{case}"
    log = GATE_DIR / f"{run_id}.log"
    if log.exists():
        log.unlink()
    proc = subprocess.run(
        [sys.executable, str(RUN / "ord0512_run_gate_r1.py"), run_id, SPEC, "--reporter=line"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "ORD0512_TREE": str(TREE), "ORD0512_PORTS": f"{PAIR[0]},{PAIR[1]}"},
    )
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    # only the failure-summary block names a red test: lines indented four spaces. The progress lines
    # ("[5/9] [chromium] › ...") name every test that RAN, and reading them as failures turned a 7-red
    # run into a list of nine -- a red set that includes everything hides the one that matters.
    red = sorted({
        f"{file_name}:{line} :: {title.strip()}"
        for file_name, line, title in re.findall(
            r"^\s{4}\[[a-z-]+\] › (\S+?)(?: (?:(\d+):\d+) )?› ([^\n—]+) —", text, re.M
        )
    })
    summary = [line.strip() for line in text.splitlines() if " passed" in line or " failed" in line]
    return {"runner_rc": proc.returncode, "summary": summary[-3:], "red_tests": red, "log": str(log)}


def main() -> int:
    wanted = sys.argv[1:] or list(CASES)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    report = {}
    for case in wanted:
        if case not in CASES:
            print(f"UNKNOWN_CASE={case}")
            return 2
        originals: dict[str, bytes] = {}
        applied: list[dict] = []
        try:
            for rel, anchor, replacement in CASES[case]:
                path = TREE / rel
                originals.setdefault(rel, path.read_bytes())
                if anchor == REVERT:
                    path.write_bytes(tip_bytes(rel))
                    applied.append({"path": rel, "mode": "reverted_to_tip", "sha_before": digest(path)})
                    continue
                text = originals[rel].decode("utf-8")
                occurrences = text.count(anchor)
                if occurrences != 1:
                    raise RuntimeError(f"anchor occurs {occurrences} times in {rel}: {anchor[:60]!r}")
                path.write_text(text.replace(anchor, replacement), encoding="utf-8", newline="")
                applied.append({"path": rel, "mode": "anchor", "sha_before": digest(TREE / rel)})
            reading = run_gate(case)
        finally:
            for rel, data in originals.items():
                (TREE / rel).write_bytes(data)
        for entry in applied:
            entry["sha_after_restore"] = digest(TREE / entry["path"])
            entry["sha_while_patched"] = entry.pop("sha_before")
            entry["matches_original"] = (
                entry["sha_after_restore"] == digest_of(originals[entry["path"]])
            )
        report[case] = {"applied": applied, "reading": reading}
        print(
            f"CASE={case} RC={reading['runner_rc']} SUMMARY={reading['summary']} "
            f"RESTORED={all(e['matches_original'] for e in applied)}"
        )
        print(f"RED={json.dumps(reading['red_tests'])}")
    out = EVIDENCE / f"mutant_{GEN}_report.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"REPORT={out}")
    return 0


def digest_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
