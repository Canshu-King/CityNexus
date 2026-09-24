"""Rewire ORD-0269 cell 1's clause-5 witness to the ORD-0278 behaviour.

The resume gate no longer opens the sheet -- it re-issues the second leg carrying the recorded
mission -- so "the sheet appeared" is the wrong contract for this node.  What cell 1 still owns is
clause 5: the marker must not be cleared ahead of a request.  That needs a real in-flight window to
sample, so the second leg is stubbed with a delayed answer and the marker is read DURING the flight.
"""

import sys

PATH = "D:/moodle/_qoder_d_lane_20260923/frontend/e2e/qoder-continuation-owner.spec.ts"

OLD = '''  // Clause 5 teeth: opening the sheet (the MANUAL_RESUME path) must not clear the marker before any
  // request goes out -- sample the storage right after the click.
  await gate.click();
  await expect(page.getByTestId("plan-ai-sheet")).toBeVisible({ timeout: 15_000 });
  const markerAfterClick = await page.evaluate(
    (jid) => localStorage.getItem(`citynexus.v8.continuation.${jid}`),
    journeyId,
  );
  expect(
    markerAfterClick,
    node("ord0269-cell1", "the marker was cleared on click -- clause 5 forbids clearing before a request"),
  ).not.toBeNull();

  writeFileSync(
    evidencePath("ord0269-cell1-reading.json"),
    JSON.stringify(
      { generatedBy: "e345b9d6", node: "ord0269-cell1", journeyId, marker, feedRequests, heading },
      null,
      1,
    ),
  );
'''

NEW = '''  /* Clause 5, measured against what the press does NOW.  ORD-0278 turned this gate into "re-issue
     the second leg carrying the recorded mission", so asserting that the sheet opens is no longer
     the contract -- and the clause this node owns cannot be judged by a click that sends nothing.
     The stub answers after a delay, which gives a real in-flight window; what must hold inside it
     is that the marker is still there.  The outcome sentence and the after-acceptance clearing are
     judged by ORD-0278's own gate, not duplicated here. */
  let leg2Started = 0;
  await page.route("**/api/v1/journeys/*/plans/generate", async (route) => {
    leg2Started += 1;
    await new Promise((resolve) => setTimeout(resolve, 6_000));
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify([]) });
  });
  await gate.click();
  await expect
    .poll(() => leg2Started, {
      timeout: 20_000,
      message: node("ord0269-cell1", "pressing the resume gate sent no second-leg request at all"),
    })
    .toBeGreaterThan(0);
  const markerDuringFlight = await page.evaluate(
    (jid) => localStorage.getItem(`citynexus.v8.continuation.${jid}`),
    journeyId,
  );
  expect(
    markerDuringFlight,
    node(
      "ord0269-cell1",
      "the marker was gone while the second leg was still in flight -- clause 5 forbids clearing ahead of a visible outcome",
    ),
  ).not.toBeNull();

  writeFileSync(
    evidencePath("ord0269-cell1-reading.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        node: "ord0269-cell1",
        journeyId,
        marker,
        feedRequests,
        heading,
        leg2StartedDuringFlight: leg2Started,
        markerBytesDuringFlight: String(markerDuringFlight ?? "").length,
      },
      null,
      1,
    ),
  );
'''


def main() -> int:
    src = open(PATH, encoding="utf-8", newline="").read()
    if src.count(OLD) != 1:
        print(f"ABORT: the clause-5 block is not unique (hits={src.count(OLD)})")
        return 2
    updated = src.replace(OLD, NEW)
    if OLD in updated:
        print("ABORT: the old clause-5 block survived the rewrite")
        return 3
    if updated.count(NEW) != 1:
        print(f"ABORT: the new clause-5 block appears {updated.count(NEW)} times, expected 1")
        return 3
    for marker in ("leg2Started", "markerDuringFlight"):
        if marker not in updated:
            print(f"ABORT: {marker} missing from the rewritten node")
            return 4

    open(PATH, "w", encoding="utf-8", newline="").write(updated)
    print(f"rewrote cell 1: {len(src)} -> {len(updated)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
