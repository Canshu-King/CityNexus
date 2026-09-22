"""Build a publishable evidence folder for one of this lane's deliveries.

The fifth dispatch order names what an external auditor must be able to read: source and parent
SHA, changed files, the patch, the mutation receipts with node id and verdict, and the runtime
readings.  Everything here is assembled from bytes already on disk (git output, the kill harness
log, the gate's own evidence JSON), so no reading is re-typed and none can drift.

Run:  D:/moodle/CityNexus/.venv/Scripts/python.exe review/build-evidence-payload.py ord0220
      D:/moodle/CityNexus/.venv/Scripts/python.exe review/build-evidence-payload.py ord0222
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
EVID = ROOT / "review/evidence/ui-overnight"

# name -> (commits newest-first, mutation log, extra evidence files, order label)
PLAN = {
    "ord0220": (
        ["c4a4001", "dfdc5d5"],
        [ROOT / "review/ord0220-1-arm.txt", ROOT / "review/ord0220-2-run.txt", ROOT / "review/ord0220-3-run.txt", ROOT / "review/ord0220-instant.txt"],
        [
            ("ord0220-caveat-meaning.json", "caveat-meaning.json"),
            ("ord0220-announcement-retired.json", "announcement-retired.json"),
            ("ord0220-reason-on-screen.json", "reason-on-screen-before-after.json"),
            ("ord0220-budget-conflict-probe.json", "budget-conflict-blackbox-probe.json"),
        ],
        "ORD-0220",
    ),
    "ord0126d": (
        ["9544628"],
        [ROOT / "review/ord0126-kill.txt"],
        [
            ("ord0126d-403.json", "refusal-403-visible-text.json"),
            ("ord0126d-id-source.json", "shown-versus-submitted-journey.json"),
        ],
        "ORD-0126 补项",
    ),
    "ord0222": (
        ["f7ce8ff"],
        [ROOT / "review/ord0222-run.txt", ROOT / "review/kill-0221-pair.txt"],
        [
            ("ord0222-visual-scan.json", "visual-text-scan.json"),
            ("ord0222-accessible-scan.json", "accessible-text-scan.json"),
            ("ord0222-unknown-value.json", "unknown-value-fail-closed.json"),
            ("ord0222-days-side-by-side.json", "days-payload-versus-visible-card.json"),
            ("ord0222-dark-scan.json", "dark-scheme-scan.json"),
        ],
        "ORD-0222",
    ),
    # ORD-0226 ran its arms through `live_checks/mutation_anchor_guard.py`, whose receipt *is* the
    # machine-readable artifact -- parsing the old driver's log for it would print an empty case list.
    # Its console capture is deliberately not published: that file predates the driver's utf-8 stdout
    # fix and is mojibake on every Chinese line; `arm-red-messages.txt` carries the same ordering.
    "ord0226": (
        [],
        [],
        [
            ("ord0226-en-reachability.json", "english-caveat-reachability.json"),
            ("phone-bundle-readings.json", "deployed-generation-readings.json"),
        ],
        "ORD-0226",
        "ord0226-arms-six-arms.json",
    ),
}


def _plan(value: tuple) -> tuple:
    """Legacy entries carry four fields; a guard-driven delivery carries a fifth (its receipt file)."""
    return value if len(value) == 5 else value + ("",)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
    ).stdout


def main() -> int:
    key = sys.argv[1]
    commits, kill_log_paths, extras, label, guard_receipt = _plan(PLAN[key])
    commits = commits or sys.argv[2:]
    out = ROOT / "review/evidence" / key
    out.mkdir(parents=True, exist_ok=True)

    for sha in commits:
        full = git("rev-parse", sha).strip()
        parent = git("rev-parse", f"{sha}^").strip()
        (out / f"{sha}__source-and-parent.txt").write_text(
            "\n".join(
                [
                    f"order           {label}",
                    f"source_sha      {full}  ({sha})",
                    f"parent_sha      {parent}",
                    f"subject         {git('log','-1','--format=%s', sha).strip()}",
                    f"authored        {git('log','-1','--format=%ad','--date=format:%Y-%m-%d %H:%M %z', sha).strip()}",
                    f"lane            e345b9d6 (frontend/UI), tree {ROOT}",
                    "interpreter     Node/Playwright for the gates; D:/moodle/CityNexus/.venv/Scripts/python.exe = 3.12.14 for the runner",
                    "note            the working tip is not pushed by this lane, so a bare SHA answers 422 on GitHub;",
                    "                these blobs are the readable coordinates for it.",
                    "",
                ]
            ),
            encoding="utf-8",
            newline="\n",
        )
        (out / f"{sha}__changed-files.txt").write_text(
            git("show", "--name-status", "--format=commit %H%nparent %P%n", sha), encoding="utf-8", newline="\n"
        )
        (out / f"{sha}__{sha}.patch").write_text(git("show", sha), encoding="utf-8", newline="\n")

    log = "".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in kill_log_paths
        if path.exists()
    )
    cases = []
    for line in log.splitlines():
        if "anchor hits=" in line:
            parts = line.strip().split()
            cases.append(
                {
                    "case": parts[0],
                    "file": parts[1],
                    "anchor_hits": int(parts[3].split("=", 1)[1]),
                    "on_disk": parts[4].split("=", 1)[1],
                    "anchor_bytes": parts[5].split("=", 1)[1],
                    "bytes_changed": parts[6].split("=", 1)[1],
                }
            )
        elif "->" in line and ("KILLED" in line or "SURVIVED" in line):
            if cases:
                cases[-1]["verdict_line"] = line.strip()
        elif line.strip().startswith("red message:"):
            if cases:
                cases[-1]["red_message"] = line.strip()[len("red message:") :][:400]
    receipt = (
        json.loads((EVID / guard_receipt).read_text(encoding="utf-8"))
        if guard_receipt
        else {
            "generatedBy": "e345b9d6",
            "order": label,
            "harness": "review/ord0082_0087_kill_drivers.py",
            "run_shape": "single node per target via --grep, one fresh process and one fresh throwaway sqlite per mutant; the product file is restored and sha256-compared after every case",
            "cases": cases,
        }
    )
    if guard_receipt:
        receipt["publishedBy"] = f"e345b9d6 for {label}"
        receipt["guardPath"] = "live_checks/mutation_anchor_guard.py :: temporary_guarded_replace"
    (out / "mutation-receipts.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    for path in kill_log_paths:
        if path.exists():
            (out / path.name).write_text(
                path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8", newline="\n"
            )

    for src, dst in extras:
        source = EVID / src
        if not source.exists():
            print(f"  skip (absent): {src}")
            continue
        data = json.loads(source.read_text(encoding="utf-8"))
        data["publishedBy"] = f"e345b9d6 for {label}"
        (out / dst).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    manifest = [f"{label} evidence surface, lane e345b9d6, commits {' + '.join(commits)}", ""]
    for path in sorted(out.iterdir()):
        if path.name == "MANIFEST.txt":
            continue
        blob = path.read_bytes()
        manifest.append(f"{len(blob):>8d} B  sha256 {hashlib.sha256(blob).hexdigest()}  {path.name}")
    (out / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
