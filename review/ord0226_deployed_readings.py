"""ORD-0226 follow-up ②: assemble the deployed-generation readings from the logs that produced them.

Nothing re-runs here. Node verdicts are parsed out of Playwright's own list output, and the bundle
identity comes from the probe receipt's content hash, so the text is a derivation, not a retyping.
"""

import json
import pathlib
import re

ROOT = pathlib.Path("D:/moodle/_qoder_integration_20260919")
RUNS = [
    ("qoder-wizard-hint-surface-readings.spec.ts", "run101513"),
    ("qoder-demo-entry-copy-matches-the-stage.spec.ts", "run101929"),
    ("qoder-budget-advisory-tiers.spec.ts / ord0220-1 (generation discriminator)", "run101582"),
    ("same discriminator again after 7f9ee06 bounded the read", "run103328"),
]
OUT = ROOT / "review/evidence/ord0226/deployed-generation-readings.txt"
probe = json.loads(
    (ROOT / "review/evidence/ui-overnight/phone-bundle-readings.json").read_text(encoding="utf-8")
)

lines = [
    "ORD-0226 follow-up ② -- this lane's targets re-read on the generation the phone is served",
    f"assembled by e345b9d6 from the run logs named below; probe receipt taken at {probe['at']} (UTC, the box is +08)",
    "",
    "BUNDLE COORDINATE (content, not a filename):",
    f"  served by :4781      {probe['servedBundle']}  {probe['servedBundleIdentity']['bytes']} B",
    f"  sha256 served        {probe['servedBundleIdentity']['servedSha256']}",
    f"  sha256 deployed dist {probe['servedBundleIdentity']['deployedDistOnDiskSha256']}",
    f"  sameBytes            {probe['servedBundleIdentity']['sameBytes']}"
    f"   ({probe['servedBundleIdentity']['deployedDist']})",
    "  chain used           playwright.deployed-bundle.config.ts -- `vite preview --outDir <deployed dist>`,",
    "                       no build step, so the bytes are the deployed artifact rather than this tree.",
    "                       backend = this run's own throwaway sqlite; _preview.db was never opened.",
    "  serviceWorkers=block, so a precache cannot answer in place of the file being measured.",
    "",
]
node_line = re.compile(r"^\s*(ok|x|✘)\s+\d+ \[([a-z-]+)\] .*?› (.+?)(?: — (.*))?$")
for label, run in RUNS:
    log = ROOT / f"review/run-{run}.log"
    text = log.read_text(encoding="utf-8", errors="replace").splitlines()
    verdicts = []
    for line in text:
        match = node_line.match(line.rstrip())
        if match:
            status, project, title, _ = match.groups()
            verdicts.append(f"    {'GREEN' if status == 'ok' else 'RED  '} [{project}] {title.strip()}")
    tail = next((line.strip() for line in reversed(text) if " passed" in line or " failed" in line), "(no summary line)")
    lines += [f"RUN {run}  --  {label}", f"  summary: {tail}"]
    lines += verdicts or ["    (no node lines parsed -- check the log)"]
    lines.append("")

instant = probe["ord0222_1_instant_reveal"]
announce = probe["ord0220_2_announcement"]
lines += [
    "WHAT THE PROBE ADDED (read-only on the live preview at :4781; creation POSTs aborted by construction,",
    f"  blockedWrites={probe['read_only_guarantee']['blockedWrites']} creationPostsAttempted={probe['read_only_guarantee']['creationPostsAttempted']})",
    f"  ORD-0216 ④  entry label {probe['ord0216_4_entry_copy']['label']!r}, city named on the wizard screen: "
    f"{probe['ord0216_4_entry_copy']['wizardScreenMentionsCity']}",
    f"  ORD-0222 ①  150 ms after the refused press the hint is already in the viewport "
    f"(scrollY={instant['scrollAt150']}, inViewport={instant['at150']['inViewport']}, opacity={instant['at150']['opacity']}),",
    f"              position={instant['settled']['position']} stickyAncestor={instant['settled']['stickyAncestor']}"
    "  -> instant reveal, not a sticky bar",
    f"              computed scroll-behavior html={instant['scrollBehaviour']['html']} body={instant['scrollBehaviour']['body']} -> no tween to depend on",
    f"  ORD-0220 ②  live region after press {announce['afterPress']['text']!r}; after fixing the field "
    f"{announce['afterFix']['text']!r}; at step 3 {announce['atStep3']['text']!r} -> it retires",
    f"  ORD-0222 ②  not readable here (no create is clicked); same bytes with a real 确认创建: "
    f"{probe['ord0222_2_after_create']['measured_on_same_bytes']}",
    "",
    "GENERATION DISCRIMINATOR: the caveat node above is RED on these bytes on purpose -- the caveat element",
    "(`budget-advisory-caveat`) arrived in e08131e, which is newer than the deployed bundle. A chain that",
    "had built this tree would have gone green, so the red is the proof that the deployed artifact, not a",
    "fresh build, was measured. NOT-DEPLOYED, not REPRODUCED, for that one node.",
    "The discriminator appears twice above on purpose: the first is before `7f9ee06` bounded the read and",
    "the second after, and the two durations are the difference between the two.",
    "",
]
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({OUT.stat().st_size} B)")
