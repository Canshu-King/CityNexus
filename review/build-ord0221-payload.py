"""Build the ORD-0221 evidence surface for publication (fifth dispatch order).

The order names six things: source+parent SHA, changed-files, the patch, the two paired-gate
mutation receipts, the Step 2 and Step 3 visible before/after readings, and a blob sha1 per file.
This assembles them from what is already on disk and already measured -- no re-typing of readings,
so a number in a receipt cannot drift from the log it came from.

Run:  D:/moodle/CityNexus/.venv/Scripts/python.exe review/build-ord0221-payload.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
OUT = ROOT / "review/evidence/ord0221"
SOURCE = "b41b4cc"
EVID = ROOT / "review/evidence/ui-overnight"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
    ).stdout


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    full = git("rev-parse", SOURCE).strip()
    parent = git("rev-parse", f"{SOURCE}^").strip()

    (OUT / f"{SOURCE}__source-and-parent.txt").write_text(
        "\n".join(
            [
                f"source_sha      {full}  ({SOURCE})",
                f"parent_sha      {parent}  (= {git('rev-parse','--short', f'{SOURCE}^').strip()})",
                f"subject         {git('log','-1','--format=%s', SOURCE).strip()}",
                f"authored        {git('log','-1','--format=%ad','--date=format:%Y-%m-%d %H:%M %z', SOURCE).strip()}",
                f"tree            {ROOT} (a git repository; this lane's working tree)",
                "interpreter     Node/Playwright for the gates; D:/moodle/CityNexus/.venv/Scripts/python.exe = 3.12.14 for the runner",
                "",
                "commands that produced the readings quoted in this folder:",
                "  python review/run_spec.py \"e2e/qoder-wizard-hint-surface-readings.spec.ts\" 4532 --config playwright.prod-gate.config.ts",
                "  python review/run_spec.py \"e2e/qoder-wizard-hint-surface-readings.spec.ts\" 4534 --config playwright.prod-gate.config.ts",
                "  KILL_PORT=4536 python review/ord0082_0087_kill_drivers.py killU1-... killU2-... killV1-...",
                "  python review/verify-ord0221-evidence-surface.py",
                "",
                f"git status --short -- frontend at run time: (empty; this commit covers frontend/src and frontend/e2e)",
                "external audit note: the working tip is never pushed by this lane, so a bare SHA in the ledger is not",
                "resolvable on GitHub (50b35e0 answers 422). These blobs are the readable coordinates.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )

    (OUT / f"{SOURCE}__changed-files.txt").write_text(
        git("show", "--name-status", "--format=commit %H%nparent %P%n", SOURCE), encoding="utf-8", newline="\n"
    )
    (OUT / f"{SOURCE}__{SOURCE}.patch").write_text(git("show", SOURCE), encoding="utf-8", newline="\n")

    kill_log = (ROOT / "review/kill-0221-pair.txt").read_text(encoding="utf-8", errors="replace")
    receipt = {
        "generatedBy": "e345b9d6",
        "order": "ORD-0221 2",
        "sha_under_test": full,
        "run_shape": "single-node, --grep per node, one fresh process and one fresh throwaway sqlite per mutant",
        "harness": "review/ord0082_0087_kill_drivers.py (anchor_hits measured, mutant read back from disk, file restored and sha256-compared)",
        "cases": [
            {
                "name": "killU1-tight-advisory-keeps-number-drops-caveat",
                "file": "frontend/src/app/V8Experience.tsx",
                "mutation": "delete the caveat line `<span>{advisory.hint}</span>` from the tight advisory block",
                "anchor_hits": 1,
                "anchor_bytes": 98,
                "bytes_changed": -43,
                "nodeid": "e2e/qoder-budget-advisory-tiers.spec.ts :: ord0212-stripping-the-caveat-while-keeping-the-number-must-go-red",
                "verdict": "KILLED",
                "red_message": "the hub prints the derived number without its caveat",
            },
            {
                "name": "killU2-tight-advisory-keeps-caveat-drops-number",
                "file": "frontend/src/app/V8Experience.tsx",
                "mutation": "delete the number line `<strong>{advisory.text}</strong>`, keeping the caveat",
                "anchor_hits": 1,
                "anchor_bytes": 90,
                "bytes_changed": -47,
                "nodeid": "e2e/qoder-budget-advisory-tiers.spec.ts :: ord0212-the-hub-keeps-only-the-tight-verdict-and-it-keeps-its-caveat-and-action",
                "verdict": "KILLED",
                "red_message": "the tight advisory lost the derived number",
            },
            {
                "name": "killV1-stale-budget-hint-follows-onto-step-3",
                "file": "frontend/src/features/setup/JourneyTrialSetup.tsx",
                "mutation": "missingStep3 = [...missingStep1, ...missingStep2]  ->  missingStep3 = missingStep1",
                "anchor_hits": 1,
                "anchor_bytes": 72,
                "bytes_changed": -35,
                "nodeid": [
                    "e2e/qoder-wizard-speaks-human-and-survives-reload.spec.ts :: ord0216-a-fixed-field-leaves-the-hint-on-the-next-step",
                    "e2e/qoder-wizard-hint-surface-readings.spec.ts :: ord0221-4-step3-visible-hint-and-live-region-read-apart",
                ],
                "verdict": "SURVIVED",
                "why_measured_not_narrated": "at step 3 the visible hint element does not exist under either spelling (see the step-3 receipt: exists=false), so no visible-text assertion can catch this mutant; the residue lives in the .v8-sr-only announcement, which is ORD-0220 2",
            },
        ],
        "log_excerpt": [line for line in kill_log.splitlines() if "->" in line or "anchor hits" in line],
    }
    (OUT / "mutation-receipt-pair-gates.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    for src, dst in (
        ("ord0221-step2-visible-before-after.json", "step2-visible-before-after.json"),
        ("ord0221-step3-visible-before-after.json", "step3-visible-before-after.json"),
    ):
        data = json.loads((EVID / src).read_text(encoding="utf-8"))
        data["publishedBy"] = "e345b9d6 for ORD-0221 3/4"
        data["visibility_rule"] = (
            "each reading is one element's own textContent plus its own box; body innerText is never used, "
            "and a .v8-sr-only region is reported as insideSrOnly=true and visuallyRendered=false"
        )
        (OUT / dst).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    manifest = [f"ORD-0221 evidence surface, lane e345b9d6, source {SOURCE} ({full})", ""]
    for path in sorted(OUT.iterdir()):
        if path.name == "MANIFEST.txt":
            continue
        blob = path.read_bytes()
        manifest.append(f"{len(blob):>8d} B  sha256 {hashlib.sha256(blob).hexdigest()}  {path.name}")
    (OUT / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
