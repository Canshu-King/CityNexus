/**
 * ORD-0531 -- the recycle bin, read as rendered text from two seats.
 *
 * The order asks for both directions on the screen and not from data attributes, so every assertion
 * below reads `innerText`.  The world is seeded through the product's own doors on this lane's stack
 * (see `seed_r1.py` beside the lane receipts), and the ids and titles come from that seed file rather
 * than being hardcoded here: a stale uuid in a spec reads as a pass against a row that no longer exists.
 *
 *  - V1 the traveller's own binned trip: named as theirs, and the 找回 action is there.
 *  - V2 a trip that belongs to somebody else where this traveller only holds an ADMIN seat: named as
 *    another's, the role sentence is rendered, and there is no action on that row.
 *  - V3 a trip belonging to a third traveller with no seat at all: its title does not appear.
 *  - V4 the two directions in one read: two rows, one action.
 *  - V5 the same screen from the owner's seat: both of their rows carry an action.
 *  - V6 no identifier in what the traveller is shown.
 *  - V7 what the screen does when it has no traveller to ask about.
 */

import { expect, test, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";

const SEED = JSON.parse(
  readFileSync("D:/moodle/_qoder_6a_ord0531_20261001/seed_r1.json", "utf8"),
) as {
  trips: Record<string, string>;
  titles: Record<string, string>;
  viewer_journey_for_B: string;
  viewer_journey_for_A: string;
};

const EVIDENCE = "D:/moodle/_qoder_6a_ord0531_20261001/e2e";
const UUID = /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/;
const readings: Record<string, unknown> = {};

test.setTimeout(180_000);

function note(name: string, body: unknown) {
  readings[name] = body;
  console.log(`O531 ${name} ${JSON.stringify(body)}`);
}

async function openBinAs(page: Page, viewerJourneyId: string | null) {
  await page.addInitScript((id) => {
    if (id) localStorage.setItem("citynexus.v8.journey_id", id);
    else localStorage.removeItem("citynexus.v8.journey_id");
  }, viewerJourneyId);
  await page.goto("/v8/trash", { waitUntil: "load" });
  await expect(page.getByTestId("journey-trash-panel").first()).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(1_200);
  return page.getByTestId("journey-trash-panel").first();
}

/** The rendered rows, each with the text of its own title, owner line and any action. */
async function rowTexts(panel: import("@playwright/test").Locator) {
  const out: Array<{ title: string; all: string }> = [];
  for (const row of await panel.getByTestId("trash-row").all()) {
    out.push({
      title: (await row.getByTestId("trash-row-title").innerText()).trim(),
      all: (await row.innerText()).replace(/\s+/g, " ").trim(),
    });
  }
  return out;
}

test.describe.serial("ORD-0531 the bin from a seat", () => {
  test("V1..V4 both directions on B's screen", async ({ page }) => {
    const panel = await openBinAs(page, SEED.viewer_journey_for_B);
    const rows = await rowTexts(panel);
    const mine = rows.find((row) => row.title === SEED.titles.mine_B);
    const readOnly = rows.find((row) => row.title === SEED.titles.read_only_B);
    const hidden = rows.find((row) => row.title === SEED.titles.hidden_B);
    const buttons = await panel.getByTestId("trash-bring-back").count();
    const reasons = await panel.getByTestId("trash-row-readonly-reason").count();
    const panelText = (await panel.innerText()).replace(/\s+/g, " ");

    note("V1_V4_as_B", {
      row_titles: rows.map((row) => row.title),
      own_row_text: mine?.all ?? null,
      read_only_row_text: readOnly?.all ?? null,
      third_party_row_present: hidden !== undefined,
      action_buttons_on_screen: buttons,
      role_reason_sentences_on_screen: reasons,
      uuid_in_rendered_text: UUID.test(panelText),
      panel_text_head: panelText.slice(0, 200),
    });

    expect(mine, "B's own binned trip should be on B's screen").toBeTruthy();
    expect(mine!.all).toContain("在这台服务器上属于你");
    expect(mine!.all).toContain("找回");
    expect(readOnly, "the trip B holds an ADMIN seat on should be visible").toBeTruthy();
    expect(readOnly!.all).toContain("由这台服务器上的另一位旅客保管");
    expect(readOnly!.all).toContain("你那个角色不能把它找回来");
    expect(readOnly!.all).not.toContain("在这台服务器上属于你");
    expect(hidden, "a third traveller's discarded trip must not reach this bin").toBeFalsy();
    expect(reasons).toBe(1);
    expect(buttons).toBe(1);
    expect(UUID.test(panelText)).toBe(false);
    await page.screenshot({ path: `${EVIDENCE}/V1_V4_as_B.png`, fullPage: true });
  });

  test("V5 the same screen from the owner's seat", async ({ page }) => {
    const panel = await openBinAs(page, SEED.viewer_journey_for_A);
    const rows = await rowTexts(panel);
    const buttons = await panel.getByTestId("trash-bring-back").count();
    note("V5_as_A", {
      row_titles: rows.map((row) => row.title),
      action_buttons_on_screen: buttons,
      third_party_row_present: rows.some((row) => row.title === SEED.titles.hidden_B),
    });
    expect(rows.some((row) => row.title === SEED.titles.mine_A)).toBe(true);
    expect(buttons).toBe(2);
    await page.screenshot({ path: `${EVIDENCE}/V5_as_A.png`, fullPage: true });
  });

  test("V7 what answers when the shell has no traveller", async ({ page }) => {
    await page.addInitScript(() => localStorage.removeItem("citynexus.v8.journey_id"), null);
    await page.goto("/v8/trash", { waitUntil: "load" });
    await page.waitForTimeout(2_500);
    const panel = page.getByTestId("journey-trash-panel");
    const panelPresent = await panel.count();
    const noViewerPresent = panelPresent
      ? await panel.getByTestId("trash-no-viewer").count()
      : 0;
    const rowsAnywhere = await page.getByTestId("trash-row").count();
    const body = (await page.locator("body").innerText()).replace(/\s+/g, " ");
    const whichSurface: Record<string, boolean> = {};
    for (const id of ["trial-setup", "v8-hub", "today-strip", "v8-trips", "v8-live"]) {
      whichSurface[id] = (await page.getByTestId(id).count()) > 0;
    }
    note("V7_no_viewer", {
      panel_rendered: panelPresent,
      named_no_viewer_state_rendered: noViewerPresent,
      bin_rows_rendered_anywhere: rowsAnywhere,
      surfaces_present: whichSurface,
      body_head: body.slice(0, 160),
    });
    /* The claim this arm holds is the leak, not the route: with no seat to ask about, no discarded
       trip of anybody's may be on the screen. Whether the shell reaches the panel at all is recorded
       above rather than asserted, because that is the shell's navigation rule, not this order's. */
    expect(rowsAnywhere).toBe(0);
    await page.screenshot({ path: `${EVIDENCE}/V7_no_viewer.png`, fullPage: true });
  });

  test("V8 write the readings file", async () => {
    writeFileSync(`${EVIDENCE}/readings.json`, JSON.stringify(readings, null, 1), "utf8");
  });
});
