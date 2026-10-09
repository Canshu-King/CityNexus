import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TREE = Path(r"D:/moodle/_qoder_shuangshugong_0558")
FRONT = TREE / "frontend"
READOUTS = TREE / "review/shuangshugong/ord0558_readouts"
CONFIG = "playwright.shuangshugong-0558.config.ts"

SPECS = [
    ("this_lane", "qoder-shuangshugong-0558-live-dedup-plural-r1"),
    ("ack_rendered", "qoder-ack-rendered"),
    ("live_structure", "qoder-live-structure"),
]

rows = []
for label, spec in SPECS:
    evidence = READOUTS / ("run_" + label)
    evidence.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["CITYNEXUS_SPEC"] = spec
    env["CITYNEXUS_EVIDENCE_DIR"] = str(evidence).replace("\\", "/")
    command = "npx playwright test --config " + CONFIG
    proc = subprocess.run(command, cwd=str(FRONT), shell=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env)
    text = (proc.stdout or "") + (proc.stderr or "")
    (evidence / ("playwright_" + label + ".txt")).write_text(text, encoding="utf-8", newline="\n")
    lines = [line.strip() for line in text.splitlines()]
    green = [line for line in lines if line.startswith("ok ")]
    red = [line for line in lines if line.startswith("x ") or line.startswith("failed")]
    summary = [line for line in lines if "passed" in line or "failed" in line or "No tests found" in line]
    rows.append((label, spec, proc.returncode, len(green), len(red),
                 summary[-1] if summary else "(no summary line)",
                 [r.split(">")[-1].strip() for r in red if ">" in r]))
    print("spec={0} rc={1} green={2} red={3} summary={4}".format(
        label, proc.returncode, len(green), len(red), summary[-1] if summary else ""))

with (READOUTS / "sibling_specs_r1.txt").open("w", encoding="utf-8", newline="\n") as fh:
    fh.write("# ORD-0558 shuangshugong: the Live screen's own specs, re-run on this worktree's bytes\n")
    fh.write("# harness: " + CONFIG + " (vite only, /api proxy pointed at a port nothing listens on)\n")
    fh.write("# env CITYNEXUS_SPEC selects which spec the harness discovers\n")
    for label, spec, rc, ng, nr, last, red_names in rows:
        fh.write("spec_label={0} pattern={1} exit_code={2} green={3} red={4}\n".format(label, spec, rc, ng, nr))
        fh.write("  last_line: {0}\n".format(last))
        for name in red_names:
            fh.write("  red_arm: {0}\n".format(name))
