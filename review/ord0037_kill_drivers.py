"""ORD-0037 kill evidence driver.

Each named assertion node in e2e/qoder-map-interaction.spec.ts is given a mutant of its
own shape.  After every run MapPanel.tsx is restored from the pristine copy and its
sha1 is checked, so the tree cannot drift out of a mutation experiment.
"""

import hashlib
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_ui_overnight_20260920"
SRC = f"{ROOT}/frontend/src/components/v8/MapPanel.tsx"
PRISTINE = f"{ROOT}/review/MapPanel.tsx.pristine"
LOGDIR = f"{ROOT}/review"
SPEC = "e2e/qoder-map-interaction.spec.ts"

sha1 = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()


def seed_pristine_from_git() -> None:
    """The restore baseline is the committed file, never a hand-made copy that can go stale."""
    proc = subprocess.run(
        "git show HEAD:frontend/src/components/v8/MapPanel.tsx",
        cwd=f"{ROOT}/frontend",
        capture_output=True,
        shell=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"cannot read MapPanel.tsx from HEAD: {proc.stderr[:200]!r}")
    with open(PRISTINE, "wb") as fh:
        fh.write(proc.stdout)


seed_pristine_from_git()

CASES = [
    (
        "kill-a-interactive-false",
        "8191",
        [("      interactive: true,\n", "      interactive: false,\n")],
        "drag-moves-camera",
    ),
    (
        "kill-a2-scrollzoom-false",
        "8192",
        [("      maxPitch: 0,\n", "      maxPitch: 0,\n      scrollZoom: false,\n")],
        "ctrl-wheel-zooms",
    ),
    (
        "kill-e-merged-single-line",
        "8193",
        [
            (
                "      return data.active_plan.legs.map((leg, index) => tag(leg.geometry, leg.mode, index));\n",
                "      return [\n"
                "        tag(\n"
                "          { type: \"Feature\", geometry: { type: \"LineString\", coordinates: data.active_plan.legs.flatMap((leg) => leg.geometry.geometry.coordinates) } },\n"
                "          \"MERGED\",\n"
                "          0,\n"
                "        ),\n"
                "      ];\n",
            )
        ],
        "route-feature-count",
    ),
    (
        "kill-b-no-mode-property",
        "8244",
        [
            (
                "      properties: { ...(feature.properties ?? {}), mode, leg_index: index },\n",
                "      properties: { ...(feature.properties ?? {}) },\n",
            )
        ],
        "route-mode-colour-expression",
    ),
    (
        "kill-c-constant-width",
        "8195",
        [
            (
                '              "line-width": [\n'
                '                "interpolate", ["exponential", 1.3], ["zoom"],\n'
                "                8, 1.5,\n"
                "                12, 3.5,\n"
                "                16, 7,\n"
                "              ],\n",
                '              "line-width": 4,\n',
            )
        ],
        "route-width-follows-zoom",
    ),
    (
        "kill-d-no-casing-layer",
        "8196",
        [
            (
                '            id: "journey-provider-route-casing",\n',
                '            id: "journey-provider-route-casing-removed",\n',
            )
        ],
        "route-casing-layer",
    ),
    # kill-b (dropping the stamped mode) survived, and that is a measured fact: the
    # provider's geometry already carries properties.mode.  The mutant that does
    # correspond to this node is the pre-fix painting itself — one constant colour.
    (
        "kill-f-constant-colour",
        "8197",
        [
            (
                '              "line-color": lineColour as unknown as string,\n',
                '              "line-color": "#4658d9",\n',
            )
        ],
        "route-mode-colour-expression",
    ),
]

only = sys.argv[1:] or [c[0] for c in CASES]
baseline = sha1(PRISTINE)
print(f"pristine sha1 {baseline}")

for name, port, subs, expected_node in CASES:
    if name not in only:
        continue
    text = open(PRISTINE, "r", encoding="utf-8", newline="").read()
    mutated = text
    hits = []
    for old, new in subs:
        n = mutated.count(old)
        hits.append(n)
        mutated = mutated.replace(old, new, 1)
    if any(h == 0 for h in hits):
        print(f"{name}: ANCHOR NOT FOUND (counts={hits}) — mutant not applied, result invalid")
        continue
    if mutated == text:
        print(f"{name}: substitution was a no-op — result invalid")
        continue
    open(SRC, "w", encoding="utf-8", newline="").write(mutated)
    print(f"{name}: mutant applied ({len(text)} -> {len(mutated)} bytes)")

    # A fresh run id per attempt: the backend refuses to reopen an existing e2e
    # database, which is what made the first re-run of every mutant "invalid".
    run_id = f"{name.replace(chr(45), chr(0x5f))[:12]}{int(time.time()) % 100000:05d}"
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_E2E_PORT": str(int(port) + 100),
            "CITYNEXUS_BACKEND_PORT": port,
            "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{run_id}.db",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": f"{ROOT}/review/evidence",
        }
    )
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_AI_API_KEY", None)
    proc = subprocess.run(
        f"npx playwright test {SPEC} --reporter=list",
        cwd=f"{ROOT}/frontend",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    out = proc.stdout + proc.stderr
    lines = [ln for ln in out.splitlines() if "WebServer" not in ln]
    log = f"{LOGDIR}/{name}.log"
    with open(log, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines) + "\n")
    kills = [ln.strip() for ln in lines if " :: " in ln]
    print(f"  exit={proc.returncode}  log={log}")
    for k in kills[:4]:
        print(f"  red message: {k[:220]}")
    server_died = any("was not able to start" in ln for ln in lines)
    if server_died:
        print(f"  INVALID RUN: the webServer never started, so this says nothing about {expected_node}")
    else:
        named = f":: {expected_node} " in out or f":: {expected_node} —" in out
        print(f"  expected node {expected_node}: {'NAMED IN A RED' if named else 'SURVIVED'}")

    import shutil

    shutil.copyfile(PRISTINE, SRC)
    now = sha1(SRC)
    print(f"  restored sha1 {now} {'OK' if now == baseline else 'MISMATCH — STOP'}")
    if now != baseline:
        sys.exit(2)
