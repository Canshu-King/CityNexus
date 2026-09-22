"""ORD-0226: lift the three arms' red blocks out of the Playwright logs named in the receipt.

Nothing here re-runs a gate -- it reads logs an earlier run already wrote, so the text an auditor
sees is the text the run produced.
"""

import json
import pathlib

ROOT = pathlib.Path("D:/moodle/_qoder_integration_20260919")
receipt = json.loads((ROOT / "review/evidence/ui-overnight/ord0226-arms.json").read_text(encoding="utf-8"))
out = ROOT / "review/evidence/ord0226/arm-red-messages.txt"
out.parent.mkdir(parents=True, exist_ok=True)

lines = [
    f"ORD-0226 arm red messages -- lane e345b9d6, run {receipt.get('runTag', 'constant-pass-1')} at {receipt['at']}",
    f"node under test : {receipt['node']}",
    f"run shape       : {receipt['runShape']}  (the 'real-seed' setup project counts as one extra pass)",
    f"product sha256  : {receipt['productFileBeforeSha256']} (restored to this after every arm)",
    "",
]
for arm in receipt["arms"]:
    log = pathlib.Path(arm["mutated"]["log"])
    body = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.exists() else []
    block = []
    for index, line in enumerate(body):
        if line.strip().startswith("Error:") and receipt["node"] in line:
            block = [item.rstrip() for item in body[index : index + 4]]
            break
    lines += [
        "=" * 100,
        f"{arm['name']}  [{arm['verdict']}]",
        f"  why            : {arm['why']}",
        f"  guard          : anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} "
        f"restored_exact={arm['restored_exact']}",
        f"  baseline before: exit={arm['baseline']['exitCode']} run_id={arm['baseline']['runId']} "
        f"({arm['baseline']['summary']})",
        f"  mutated arm    : exit={arm['mutated']['exitCode']} run_id={arm['mutated']['runId']} "
        f"({arm['mutated']['summary']})",
        f"  mutated sha256 : {arm['mutated_sha256']}",
        f"  log            : {arm['mutated']['log']}",
        "  red            :",
        *[f"    {item[:230]}" for item in block],
        "",
    ]
out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {out} ({out.stat().st_size} B)")
