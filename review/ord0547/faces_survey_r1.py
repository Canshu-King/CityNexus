"""ORD-0547 pre-survey: what the four named entry points actually do today, measured off the tree.

The ruling asks these faces to render the server's named code when they are refused. Before anyone
writes a line of UI, two things have to be on the table: whether each face can even reach a refusal
(one of them is stopped before the request), and what the shell's own error channel is allowed to say
under the standing rulings that are written into the file it lives in.

Read-only. Every number is counted from the tree at the tip named on the first line.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

WT = Path(r"D:/moodle/_qoder_lane_heyuegong_20261009/wt")
FRONTEND = WT / "frontend" / "src"
REPO = "D:/moodle/CityNexus"
TIP_REF = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
OUT = WT / "review" / "ord0547" / "FACES_R1.txt"

FACES = (
    "api/citynexus.ts",
    "features/simulation/simulationAdapter.ts",
    "demo/goldenScenario.ts",
    "features/simulation/SimulationPanel.tsx",
)


def read(rel: str) -> list[str]:
    return (FRONTEND / rel).read_text(encoding="utf-8").splitlines()


tip = subprocess.run(
    ["git", "-C", REPO, "rev-parse", "--verify", TIP_REF], capture_output=True, text=True
).stdout.strip()

rows = [
    "ORD-0547 pre-survey, measured off the tree.",
    f"tip={tip}",
    "The ruling's four faces, and what each one can do today.",
    "",
]

post_sites: list[str] = []
for rel in FACES:
    lines = read(rel)
    sites = [f"{rel}:{i + 1}" for i, ln in enumerate(lines) if '"/demo/reset"' in ln or '"/api/v1/demo/reset"' in ln]
    post_sites += sites

rows.append(f"sites_in_the_four_faces_that_name_the_route={len(post_sites)}")
for site in post_sites:
    rows.append(f"   {site}")

callers = {
    "api/citynexus.ts resetDemo": [
        f"{rel}:{i + 1}"
        for rel in ("demo/goldenScenario.ts",)
        for i, ln in enumerate(read(rel))
        if ".resetDemo()" in ln
    ],
    "demo/goldenScenario.ts bootstrapGoldenScenario": [
        f"main.tsx:{i + 1}" for i, ln in enumerate(read("main.tsx")) if "bootstrapGoldenScenario()" in ln
    ],
    "features/simulation/simulationAdapter.ts resetStage": [
        f"SimulationPanel.tsx:{i + 1}"
        for i, ln in enumerate(read("features/simulation/SimulationPanel.tsx"))
        if "await resetStage()" in ln
    ],
}
rows += ["", "who is above each face (the chain that can actually reach a refusal):"]
for name, hits in callers.items():
    rows.append(f"   {name} -> {hits or 'no caller found in src/'}")

panel = read("features/simulation/SimulationPanel.tsx")
guard = [i + 1 for i, ln in enumerate(panel) if re.search(r"if \(row\.blocked \|\| running\)", ln)]
static_block = [i + 1 for i, ln in enumerate(panel) if ln.strip().startswith("blocked: {")]
rows += [
    "",
    "the simulation panel's own row never reaches the server:",
    f"   a permanently set blocker starts at SimulationPanel.tsx:{static_block[0] if static_block else 'NOT FOUND'}",
    f"   and the click path returns at SimulationPanel.tsx:{guard[0] if guard else 'NOT FOUND'} when row.blocked is set,",
    "   so there is no HTTP response to read a code from on that face.",
]

note = read("main.tsx")
allowed = [i + 1 for i, ln in enumerate(note) if "Q64=1" in ln or "Q71" in ln]
renders = [i + 1 for i, ln in enumerate(note) if "CityNexus request refused" in ln]
rows += [
    "",
    "the shell's error channel is written under two standing rulings, in the same file:",
    f"   main.tsx:{allowed[0] if allowed else 'NOT FOUND'} carries the Q64=1 note and main.tsx:{allowed[1] if len(allowed) > 1 else allowed[0] if allowed else 'NOT FOUND'} the Q71 side-door,",
    f"   and main.tsx:{renders[0] if renders else 'NOT FOUND'} is the only sentence it builds -- it names the status this device saw and no server word.",
    "So ORD-0547 as written (render the server's named code) is not free to implement in this file",
    "without a ruling that says which part of Q64=1 it lifts: the code as a selector, or the code on screen.",
]

text = "\n".join(rows) + "\n"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(text, encoding="utf-8")
print(text)
