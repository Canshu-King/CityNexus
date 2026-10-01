"""ORD-0512 map-gate family runner r1 -- the same eighteen specs on two generations of one tree.

The accepted map gates belong to other orders (`qoder-map-ord0390/0403/0410/0412`, `qoder-ord0394/0415/
0417`, `qoder-map-ord0453`, the footprint and toggle-reach gates, and the surfaces that read the panel's
text). Painting a chip beside every pin touches their subject, so "my gate is green" is not the
denominator -- the denominator is the red set of that family before this order's bytes and after them,
read with one instrument, on one machine, in one generation.

`--revert` swaps the three product files this order changes back to the tip's bytes for the duration of
the run (and only for that duration; the restore is verified by sha256), which is what makes the two
readings comparable rather than one of them a wish.

usage: python ord0512_family_r1.py <run-id-suffix> [--revert]
"""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

TREE = pathlib.Path(os.environ.get("ORD0512_TREE") or r"D:/moodle/_qoder_b_ord0417_20260928/ord0512cut_5a4cbcd2")
RUN = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run")
GATE_DIR = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/gate")
REPORT = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/family")
TIP = os.environ.get("ORD0512_TIP") or "5a4cdbd26d4a58d6ed6b277480e766ac08b15ded"
PRODUCT_FILES = [
    "frontend/src/components/v8/MapPanel.tsx",
    "frontend/src/features/shared/SharedJourneyPanel.tsx",
]
# the e2e family: every accepted spec whose subject is the map panel, a pin in it, or text painted on it
FAMILY = [
    "e2e/qoder-map-ord0390-selection-both-ways.spec.ts",
    "e2e/qoder-ord0394-map-coordinates.spec.ts",
    "e2e/qoder-map-ord0403-named-control-and-labels.spec.ts",
    "e2e/qoder-ord0406-attention-band-hit.spec.ts",
    "e2e/qoder-map-ord0410-recenter-acts-on-the-journey-view.spec.ts",
    "e2e/qoder-map-ord0412-label-scope.spec.ts",
    "e2e/qoder-ord0415-label-string-origin.spec.ts",
    "e2e/qoder-ord0417-tap-names-the-stop.spec.ts",
    "e2e/qoder-ord0417-hub-tap-names-the-stop.spec.ts",
    "e2e/qoder-ord0407-empty-state-actions.spec.ts",
    "e2e/qoder-map-ord0453-list-third-state.spec.ts",
    "e2e/qoder-bac10f40-ord0497-footprints-on-map.spec.ts",
    "e2e/qoder-bac10f40-ord0537-map-toggle-reach.spec.ts",
    "e2e/qoder-failure-has-an-exit.spec.ts",
    "e2e/qoder-live-structure.spec.ts",
    "e2e/qoder-ack-rendered.spec.ts",
    "e2e/qoder-map-interaction.spec.ts",
    "e2e/real-world-trip-operations-v9.spec.ts",
]


def tip_bytes(rel: str) -> bytes:
    return subprocess.run(
        ["git", "-C", r"D:/moodle/CityNexus", "show", f"{TIP}:{rel}"],
        capture_output=True, check=True,
    ).stdout


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    suffix = sys.argv[1]
    revert = "--revert" in sys.argv[2:]
    REPORT.mkdir(parents=True, exist_ok=True)
    run_id = f"ord0512fam_{suffix}"
    log = GATE_DIR / f"{run_id}.log"
    originals: dict[str, bytes] = {}
    if revert:
        for rel in PRODUCT_FILES:
            path = TREE / rel
            originals[rel] = path.read_bytes()
            path.write_bytes(tip_bytes(rel))
    env_ports = os.environ.get("ORD0512_PORTS") or "5154,5155"
    try:
        proc = subprocess.run(
            [sys.executable, str(RUN / "ord0512_run_gate_r1.py"), run_id, *FAMILY, "--reporter=line"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "ORD0512_TREE": str(TREE), "ORD0512_PORTS": env_ports},
        )
        rc = proc.returncode
    finally:
        restored = {}
        for rel, data in originals.items():
            (TREE / rel).write_bytes(data)
            restored[rel] = hashlib.sha256(data).hexdigest() == hashlib.sha256((TREE / rel).read_bytes()).hexdigest()
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    red = sorted({
        line.strip().split("›")[1].split("—")[0].strip()
        for line in text.splitlines()
        if line.strip().startswith("[chromium]") and "›" in line
    })
    totals = re.findall(r"^\s*(\d+) (passed|failed|flaky|skipped)", text, re.M)
    report = {
        "run_id": run_id,
        "gate_rc": rc,
        "reverted_files": list(originals),
        "restored_ok": restored,
        "spec_files": FAMILY,
        "summary_lines": [f"{n} {w}" for n, w in totals],
        "red_tests": red,
        "log": str(log),
    }
    out = REPORT / f"{run_id}.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"RC={rc} RUN={run_id} SUMMARY={report['summary_lines']} RED={len(red)} RESTORED={restored}")
    print(f"REPORT={out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
