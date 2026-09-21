"""Rename the floating widget's surface, because `sim-window` was already taken.

My new window used `data-testid="sim-window"`; the panel has used that id since ORD-0059 for the
scene's date range (`SimulationPanel.tsx:695`). Playwright's strict mode caught it -- the helper
resolved 2 elements -- but a name that means two things on one surface is the bug, not the symptom,
so the widget becomes `sim-pop` / `.cn-sim-pop*` and the date row keeps the name it has always had.
"""

import sys

ROOT = "D:/moodle/_qoder_integration_20260919/"

SITES = {
    "frontend/src/features/simulation/SimulationPanel.tsx": [
        ('          id="cn-sim-window"\n', '          id="cn-sim-pop"\n'),
        ('          className="cn-sim-window"\n          data-testid="sim-window"\n',
         '          className="cn-sim-pop"\n          data-testid="sim-pop"\n'),
        ('          <p className="cn-sim-window-decl" data-testid="sim-entry-decl">',
         '          <p className="cn-sim-pop-decl" data-testid="sim-entry-decl">'),
        ('          <div className="cn-sim-window-body" data-testid="sim-window-body">',
         '          <div className="cn-sim-pop-body" data-testid="sim-pop-body">'),
        ('        aria-controls="cn-sim-window"', '        aria-controls="cn-sim-pop"'),
    ],
    "frontend/src/features/simulation/SimulationPanel.css": [
        (".cn-sim-window {", ".cn-sim-pop {"),
        (".cn-sim-window-decl {", ".cn-sim-pop-decl {"),
        (".cn-sim-window-body {", ".cn-sim-pop-body {"),
        ("  .cn-sim-window {\n    width: calc(100vw - 24px);\n  }",
         "  .cn-sim-pop {\n    width: calc(100vw - 24px);\n  }"),
        ("its rows scroll inside `.cn-sim-window-body`", "its rows scroll inside `.cn-sim-pop-body`"),
    ],
    "frontend/e2e/_qoderStageEntry.ts": [
        ('page.getByTestId("sim-window")', 'page.getByTestId("sim-pop")'),
        ("if (await page.getByTestId(\"sim-window\").count()) return;",
         "if (await page.getByTestId(\"sim-pop\").count()) return;"),
    ],
    "frontend/e2e/qoder-today-follows-the-stage.spec.ts": [
        ('page.getByTestId("sim-window")', 'page.getByTestId("sim-pop")'),
        ('document.querySelector(\'[data-testid="sim-window"]\')',
         'document.querySelector(\'[data-testid="sim-pop"]\')'),
    ],
    "frontend/e2e/qoder-reset-from-wizard.spec.ts": [
        ('page.getByTestId("sim-window")', 'page.getByTestId("sim-pop")'),
    ],
    "frontend/e2e/qoder-wallet-commitments.spec.ts": [
        ('page.getByTestId("sim-window")', 'page.getByTestId("sim-pop")'),
    ],
}

for name, edits in SITES.items():
    path = f"{ROOT}{name}"
    body = open(path, encoding="utf-8", newline="").read()
    for old, new in edits:
        hits = body.count(old)
        if hits == 0:
            print(f"skip (already renamed or absent) {name}: {old[:48]!r}")
            continue
        body = body.replace(old, new)
        print(f"{name}: replaced {hits} x {old[:48]!r}")
    open(path, "w", encoding="utf-8", newline="").write(body)

# The date row must survive untouched -- it is a different surface with the old name.
panel = open(f"{ROOT}frontend/src/features/simulation/SimulationPanel.tsx", encoding="utf-8").read()
if panel.count('data-testid="sim-window"') != 1:
    print(f"FATAL: expected exactly one legacy sim-window (the date row), found {panel.count('data-testid=\"sim-window\"')}")
    sys.exit(2)
print("legacy sim-window intact:", panel.count('data-testid="sim-window"'))
