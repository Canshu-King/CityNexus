"""ORD-0512 -- does the ORD-0403 `reach` red belong to this order? r1

The family run of the re-cut came back 15 failed on the tip's bytes and 17 on this candidate's, and the two
extra names are `reach ... @320` and `reach ... @414`, both failing with "must not sit under the tile
notice". That sentence is about the basemap notice, which appears when tiles do not load -- so the first
question is not "what did my chip do" but "does this red even come back". A red that does not reproduce on
a re-run is not attributable (this lane has been fooled by that before), so each side is run twice,
alternating, with the product files reverted and restored by sha256 around the tip rounds.

usage: python ord0403_flank_r1.py
"""
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys

TREE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/ord0512cut_bf4f776b")
RUN = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run")
GATE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/gate")
OUT = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/family")
TIP = os.environ.get("ORD0512_TIP") or "bf4f776b0ba943b88817dfcc0cb3442d75fd9e21"
SPEC = "e2e/qoder-map-ord0403-named-control-and-labels.spec.ts"
PRODUCT_FILES = [
    "frontend/src/components/v8/MapPanel.tsx",
    "frontend/src/features/shared/SharedJourneyPanel.tsx",
    "frontend/src/lib/mapStopLabels.ts",
    "frontend/src/map-stop-labels.css",
]
BLOCK = re.compile(r"^\s{4}\[([a-z-]+)\] › (\S+) › (\S.*)$", re.M)


def tip_bytes(rel):
    return subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "show", f"{TIP}:{rel}"],
                          capture_output=True, check=True).stdout


def one_round(side, index, ports):
    originals = {}
    try:
        if side == "tip":
            for rel in PRODUCT_FILES:
                path = TREE / rel
                originals[rel] = path.read_bytes()
                path.write_bytes(tip_bytes(rel))
        run_id = f"ord0403flank_{side}_{index}"
        log = GATE / f"{run_id}.log"
        if log.exists():
            log.unlink()
        proc = subprocess.run(
            [sys.executable, str(RUN / "ord0512_run_gate_r1.py"), run_id, SPEC, "--reporter=line"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "ORD0512_TREE": str(TREE), "ORD0512_PORTS": ports},
        )
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    finally:
        restored = {}
        for rel, data in originals.items():
            (TREE / rel).write_bytes(data)
            restored[rel] = hashlib.sha256(data).hexdigest() == hashlib.sha256((TREE / rel).read_bytes()).hexdigest()
    reds = sorted({f"{loc.replace(chr(92), '/')} :: {title.strip()}" for _p, loc, title in BLOCK.findall(text)})
    totals = re.findall(r"^\s*(\d+) (failed|passed)", text, re.M)
    return {"side": side, "index": index, "runner_rc": proc.returncode,
            "totals": [f"{n} {w}" for n, w in totals], "red_tests": reds,
            "restored_ok": restored, "log": str(log)}


def main() -> int:
    rounds = []
    for index, side in enumerate(["cand", "tip", "cand", "tip"], start=1):
        ports = "5220,5221" if side == "cand" else "5222,5223"
        reading = one_round(side, index, ports)
        rounds.append(reading)
        print(f"ROUND {index} side={side} totals={reading['totals']} "
              f"restored={all(reading['restored_ok'].values()) if reading['restored_ok'] else 'n/a'}")
        for r in reading["red_tests"]:
            print("   RED", r[:120].encode("ascii", "backslashreplace").decode())
    cand = [set(r["red_tests"]) for r in rounds if r["side"] == "cand"]
    tip = [set(r["red_tests"]) for r in rounds if r["side"] == "tip"]
    summary = {
        "tip": TIP, "spec": SPEC, "rounds": rounds,
        "red_in_every_candidate_round": sorted(set.intersection(*cand)) if cand else [],
        "red_in_any_tip_round": sorted(set.union(*tip)) if tip else [],
        "candidate_only_reproducible": sorted(
            (set.intersection(*cand) - set.union(*tip)) if cand and tip else set()),
    }
    dest = OUT / "ord0403_flank_r1.json"
    io.open(dest, "w", encoding="utf-8", newline="\n").write(json.dumps(summary, indent=1, ensure_ascii=False))
    print("CANDIDATE_ONLY_REPRODUCIBLE=", json.dumps(summary["candidate_only_reproducible"]).encode("ascii", "backslashreplace").decode())
    print("WROTE=", dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
