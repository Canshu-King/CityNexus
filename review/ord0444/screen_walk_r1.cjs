/*
 * ORD-0444 -- the collection screen, walked in a real browser against this lane's own private stack.
 *
 * Standalone on purpose: this is not added to `frontend/e2e/`, because that suite starts its own
 * servers, runs serially on one shared database, and belongs to the e2e owner.  Here the stack is
 * three processes this lane started and will stop: a uvicorn on `:60148` over a private copy of the
 * preview database, and `vite preview` on `:60149` serving the `dist` this tree built, proxying
 * `/api/v1` to `:60148`.  Port ownership is printed from the HTTP answers and from the database file
 * the same script writes, not assumed from a port being open.
 *
 * Five frames, each read as rendered text (`innerText` / `textContent`), never as a `data-*`
 * attribute, because the claim being evidenced is what a traveller sees:
 *   1  an empty store -- the empty state, and the action button beside it;
 *   2  the action pressed -- the shelf the server created, read back through `GET /collections`;
 *   3  a shelf with nothing on it -- its own empty sentence, not the whole-screen one;
 *   4  a place added through the door (not through this screen -- the picker is another order),
 *      then the screen re-read: the row, with its name, category, city code, coordinate + CRS and note;
 *   5  the same shelf from a second, unrelated read of the door, so frame 4 cannot be client state.
 *
 * A screenshot was attempted and is NOT part of this evidence: the host returns
 * `NATIVE_BROWSER_VIEWPORT_UNAVAILABLE` for the in-app browser, so no PNG is claimed here.
 */

const { chromium } = require("playwright");

const PREVIEW = process.env.CNX_PREVIEW || "http://localhost:60149";
const BACKEND = process.env.CNX_BACKEND || "http://127.0.0.1:60148";
const OUT = process.env.CNX_OUT || "screen_walk_r1.json";
const PLACE_ID = "place-beijing-houhai";

const log = { preview: PREVIEW, backend: BACKEND, frames: {}, started_at: new Date().toISOString() };

function text(page, selector) {
  return page.locator(selector).first().textContent();
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });

  await page.goto(`${PREVIEW}/v8/discover`, { waitUntil: "load" });

  // The sealed-demo entry: this screen lives inside the experience, so the store needs a journey.
  const entry = page.getByRole("button", { name: "使用封存的演示行程" });
  if (await entry.count()) {
    await entry.first().click();
  }
  await page.waitForSelector('[data-testid="collection-panel"]', { timeout: 30000 });

  // frame 1 -- the empty state, with its action
  log.frames.f1_empty_state = {
    panel_heading: await text(page, '[data-testid="collection-panel"] .v8-kicker'),
    empty_sentence: await text(page, '[data-testid="collection-empty"] p'),
    action_label: await text(page, '[data-testid="collection-empty-action"]'),
    action_enabled: (await page.locator('[data-testid="collection-empty-action"]').isEnabled()),
    empty_state_present: (await page.locator('[data-testid="collection-empty"]').count()) === 1,
    shelf_rows: await page.locator('[data-testid="collection-row"]').count(),
    panel_inner_text: await page.locator('[data-testid="collection-panel"]').innerText(),
  };

  // frame 2 -- press it: the create door runs, and the shelf comes back from the server
  await page.locator('[data-testid="collection-empty-action"]').click();
  await page.waitForSelector('[data-testid="collection-shelf"]', { timeout: 20000 });
  log.frames.f2_after_the_action = {
    outcome_text: await text(page, '[data-testid="collection-outcome-text"]'),
    shelf_count_line: await text(page, '[data-testid="collection-shelf-count"]'),
    shelf_names: await page.locator('[data-testid="collection-shelf-name"]').allTextContents(),
    shelf_badges: await page
      .locator('[data-testid="collection-shelf"] [data-testid="collection-shelf-count"]')
      .allTextContents(),
    empty_state_gone: (await page.locator('[data-testid="collection-empty"]').count()) === 0,
  };

  // frame 3 -- a shelf that holds nothing says so in its own sentence
  log.frames.f3_shelf_with_no_rows = {
    shelf_empty_sentence: await text(page, '[data-testid="collection-shelf-empty"]'),
  };

  // frame 4 -- a place goes in through the door, then the screen re-reads.
  const folderId = await page.evaluate(async () => {
    const answer = await fetch("/api/v1/collections");
    const shelves = await answer.json();
    return shelves[0].id;
  });
  const added = await fetch(`${BACKEND}/api/v1/collections/${folderId}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ place_id: PLACE_ID, note: "傍晚去，日落最好" }),
  });
  const addedBody = await added.json();
  log.frames.f4_door_add_then_screen_reread = {
    add_http: added.status,
    folder_id: folderId,
    item_id: addedBody.id,
    row_texts: (await page.locator('[data-testid="collection-row"]').allInnerTexts()).map((t) =>
      t.replace(/\n/g, " | ")
    ),
    note_lines: await page.locator('[data-testid="collection-row-note"]').allTextContents(),
    row_count_before_refresh: (await page.locator('[data-testid="collection-row"]').count()),
  };
  await page.locator('[data-testid="collection-refresh"]').first().click();
  await page.waitForFunction(
    () => document.querySelectorAll('[data-testid="collection-row"]').length > 0,
    null,
    { timeout: 20000 }
  );
  log.frames.f4_door_add_then_screen_reread.row_texts_after_refresh = (
    await page.locator('[data-testid="collection-row"]').allInnerTexts()
  ).map((t) => t.replace(/\n/g, " | "));
  log.frames.f4_door_add_then_screen_reread.count_badge_after_refresh = await text(
    page,
    '[data-testid="collection-shelf"] [data-testid="collection-shelf-count"]'
  );

  // frame 5 -- an independent read of the door, outside the page
  const outside = await fetch(`${BACKEND}/api/v1/collections`);
  const outsideBody = await outside.json();
  const shelf = outsideBody.find((s) => s.id === folderId) || {};
  log.frames.f5_independent_door_read = {
    http: outside.status,
    shelf_count: outsideBody.length,
    item_count: shelf.item_count,
    items_len: (shelf.items || []).length,
    row_place_ids: (shelf.items || []).map((r) => r.place_id),
    row_notes: (shelf.items || []).map((r) => r.note),
  };

  // The nav strip must not have grown a raw dictionary key.
  log.frames.f6_sidebar_honesty = {
    nav_shows_raw_key: (await page.locator("nav.v8-nav").innerText()).includes("nav.collections"),
    discover_nav_label: (await page.locator("nav.v8-nav").innerText()).includes("城市探索"),
  };

  log.finished_at = new Date().toISOString();
  await browser.close();
  require("fs").writeFileSync(OUT, JSON.stringify(log, null, 1), "utf-8");
  console.log(JSON.stringify(log, null, 1));
}

main().catch((error) => {
  log.error = String(error && error.message ? error.message : error);
  require("fs").writeFileSync(OUT, JSON.stringify(log, null, 1), "utf-8");
  console.error(log.error);
  process.exit(1);
});
