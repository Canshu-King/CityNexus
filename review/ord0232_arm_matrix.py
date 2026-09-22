"""ORD-0232: derive the arm matrix from the receipt that measured it.

Nothing here re-runs a gate; every line is read out of `ord0232-arms-six-arms.json` and the Playwright
logs it names, so the matrix cannot drift from the run.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("D:/moodle/_qoder_integration_20260919")
SOURCE = sys.argv[1] if len(sys.argv) > 1 else "ord0232-arms-six-arms.json"
receipt = json.loads((ROOT / "review/evidence/ui-overnight" / SOURCE).read_text(encoding="utf-8"))
out = ROOT / "review/evidence/ord0232/arm-matrix.txt"
out.parent.mkdir(parents=True, exist_ok=True)

SHORT = {key.split("-", 1)[0]: key.split("-", 1)[0] for key in receipt["everyNodeKilled"]}
lines = [
    f"ORD-0232 mutation matrix -- lane e345b9d6, receipt {SOURCE}, run {receipt['runTag']} at {receipt['at']}",
    f"spec       : {receipt['spec']}",
    f"run shape  : {receipt['runShape']}",
    f"guard      : {receipt['guard']}",
    "nodes      : " + ", ".join(f"{key.split('-')[1]}={value}" for key, value in receipt["everyNodeKilled"].items()),
    "",
]
for arm in receipt["arms"]:
    reds = ",".join(item.split("-")[1] for item in arm["redSet"]) or "-"
    lines += [
        "=" * 96,
        f"{arm['name']}  [{arm['verdict']}]  owner={arm['ownerNode'].split('-')[1]}  red=[{reds}]"
        f"  exclusive_to_owner={arm['exclusiveToOwner']}",
        f"  what it models : {arm['why']}",
        f"  file           : {pathlib.Path(arm['file']).name}",
        f"  guard          : anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} "
        f"restored_exact={arm['restored_exact']}",
        f"  baseline       : exit={arm['baseline']['exitCode']} run_id={arm['baseline']['runId']} "
        f"({arm['baseline']['summary']})",
        f"  mutated        : exit={arm['attempt']['exitCode']} run_id={arm['attempt']['runId']} "
        f"({arm['attempt']['summary']})",
        f"  node verdicts  : " + "  ".join(
            f"{key.split('-')[1]}:{value}" for key, value in arm["attempt"]["nodes"].items()
        ),
        f"  log            : {arm['attempt']['log']}",
        "",
    ]
lines += [
    "per-node killers (every arm that reddened the node):",
    *[
        f"  {key.split('-')[1]} <- " + (", ".join(sorted(value)) if value else "NONE")
        for key, value in receipt["everyNodeKilled"].items()
    ],
    "",
    "exclusive killers (red set == the owner alone):",
    *[
        f"  {key.split('-')[1]} <- " + (", ".join(sorted(value)) if value else "NONE")
        for key, value in receipt["exclusiveKiller"].items()
    ],
    "",
    f"allArmsKilled={receipt['allArmsKilled']} everyNodeHasKiller={all(receipt['everyNodeKilled'].values())} "
    f"invalidStackArms={receipt['invalidStackArms']} treeUnchanged={receipt['treeUnchangedByThisRun']}",
    "END-TO-END ARM: `review/ord0232_e2e_replay.py` -> exit 7 BLOCKED_ON_MERGE(a96fabf) while that commit",
    "  (branch agent/canary-ord198-20260922) is not an ancestor of the integration tip.  No green is",
    "  claimed for it, and the positive direction above is measured against B's real envelope replayed",
    "  through a route stub, which proves the rendering path rather than the whole pipeline.",
    "",
]
out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {out} ({out.stat().st_size} B)")
