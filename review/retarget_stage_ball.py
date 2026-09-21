"""Retarget every gate that opened the stage from the old inline disclosure to the floating ball.

The widget's shape changed; what each node proves must not. So these are name swaps only -- the
counts, the tap-floor assertion, the "if there is nothing to open, that IS the finding" branches all
stay, and the script below refuses to write unless every pattern matched exactly once.
"""

import sys

ROOT = "D:/moodle/_qoder_integration_20260919/frontend/e2e/"

EDITS = [
    (
        "qoder-simulation-scene.spec.ts",
        """  await expect(page.getByTestId("sim-entry"), node("sim-entry-390-declares-stage-in-plain-words",
    "the Simulation entry is not rendered on Today at all")).toBeVisible({ timeout: 25_000 });""",
        """  await expect(page.getByTestId("sim-ball"), node("sim-entry-390-declares-stage-in-plain-words",
    "the stage ball is not rendered on Today at all")).toBeVisible({ timeout: 25_000 });""",
    ),
    (
        "qoder-simulation-scene.spec.ts",
        """  /* The entry starts collapsed on a phone (ORD-0085), and every node below reads the panel. */
  await openStageEntry(page, "the stage gate");""",
        """  /* At rest the widget is one ball, so every node below has to open the window first. */
  await openStageEntry(page, "the stage gate");""",
    ),
    (
        "qoder-simulation-scene.spec.ts",
        """      const summary = page.getByTestId("sim-entry-summary");
      const summaryBox = await summary.boundingBox();
      expect(
        summaryBox && summaryBox.height >= 44,
        node("sim-entry-390-declares-stage-in-plain-words",
          `the entry's own tap target measures ${JSON.stringify(summaryBox)} at 390px`),
      ).toBe(true);""",
        """      const ballBox = await page.getByTestId("sim-ball").boundingBox();
      expect(
        ballBox && ballBox.width >= 44 && ballBox.height >= 44,
        node("sim-entry-390-declares-stage-in-plain-words",
          `the ball's own tap target measures ${JSON.stringify(ballBox)} at 390px`),
      ).toBe(true);""",
    ),
    (
        "qoder-simulation-scene.spec.ts",
        "      readings[scheme] = { text, bannerWidth: box?.width, summaryHeight: summaryBox?.height };",
        "      readings[scheme] = { text, bannerWidth: box?.width, ball: ballBox };",
    ),
    (
        "qoder-reset-from-wizard.spec.ts",
        """  const summary = page.getByTestId("sim-entry-summary");
  const entryFound = (await summary.count()) > 0;
  if (entryFound) await summary.click();""",
        """  const ball = page.getByTestId("sim-ball");
  const entryFound = (await ball.count()) > 0;
  if (entryFound) await ball.click();""",
    ),
    (
        "qoder-reset-from-wizard.spec.ts",
        """  /* The wizard's stage entry is collapsed on purpose; opening it is the first teacher action in this
     chain, and if there is nothing to open the chain does not exist. */
  const summary = page.getByTestId("sim-entry-summary");
  await expect(
    summary,
    node("ord0081-stage-chain-from-the-wizard-reaches-execution",
      "the wizard screen has no stage entry to open, so no chain of real stage actions can start here"),
  ).toHaveCount(1);
  await summary.click();""",
        """  /* The widget is one ball at rest; pressing it is the first teacher action in this chain, and if
     there is nothing to press the chain does not exist. */
  const ball = page.getByTestId("sim-ball");
  await expect(
    ball,
    node("ord0081-stage-chain-from-the-wizard-reaches-execution",
      "the wizard screen has no stage ball, so no chain of real stage actions can start here"),
  ).toHaveCount(1);
  await ball.click();
  await expect(
    page.getByTestId("sim-window"),
    node("ord0081-stage-chain-from-the-wizard-reaches-execution",
      "the ball was pressed and no stage window appeared"),
  ).toBeVisible();""",
    ),
    (
        "qoder-wallet-commitments.spec.ts",
        """  const summary = page.getByTestId("sim-entry-summary");
  await expect(
    summary,
    node("ord0087-booked-commitment-is-on-the-wallet-screen", "the wizard has no stage entry to open"),
  ).toHaveCount(1);
  await summary.click();""",
        """  const ball = page.getByTestId("sim-ball");
  await expect(
    ball,
    node("ord0087-booked-commitment-is-on-the-wallet-screen", "the wizard has no stage ball to press"),
  ).toHaveCount(1);
  await ball.click();
  await expect(
    page.getByTestId("sim-window"),
    node("ord0087-booked-commitment-is-on-the-wallet-screen",
      "the ball was pressed and no stage window appeared on the wizard"),
  ).toBeVisible();""",
    ),
]

text = {}
for name, old, new in EDITS:
    if name not in text:
        text[name] = open(f"{ROOT}{name}", encoding="utf-8", newline="").read()
    hits = text[name].count(old)
    if hits != 1:
        print(f"ABORT {name}: pattern matched {hits} times -> {old[:70]!r}")
        sys.exit(2)
    text[name] = text[name].replace(old, new, 1)

for name, body in text.items():
    open(f"{ROOT}{name}", "w", encoding="utf-8", newline="").write(body)
    left = body.count("sim-entry-summary") + body.count('getByTestId("sim-entry")')
    print(f"{name}: written, stale references left = {left}")
