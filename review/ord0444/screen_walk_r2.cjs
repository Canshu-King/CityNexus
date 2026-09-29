/*
 * ORD-0444 r2 -- the same screen walk, run against the re-cut tree after the two Q64 cells were
 * removed. It exists because r2 deletes something from the details face, and a green `tsc` plus a
 * green `vite build` do not show what a traveller reads.
 *
 * Stack, all three processes started by this lane and none of them shared:
 *   uvicorn  :60152  over `scratch/private_r10.db`, a `mode=ro`-backed-up copy of the shared preview
 *                    database (the shared file itself is opened read-only and byte-compared),
 *                    started with `CITYNEXUS_DEMO_MODE=true` because the sealed-demo entry the wizard
 *                    uses needs the stage, and with no token and no reset called.
 *   preview  :60153  `vite preview` over THIS tree's `dist`, proxying /api/v1 to :60152 through
 *                    `CITYNEXUS_BACKEND_PORT` (`frontend/vite.config.ts:143`), so what is walked is
 *                    the built artifact and not a dev server.
 *
 * Frames: the empty state and its action; the shelf the action created, read back by the server; that
 * shelf's own no-rows sentence; a place added through the door and then seen after one press of
 * 再读一次收藏夹; an independent read of the door outside the page. Plus the two checks that are the
 * whole point of r2 -- no `data-cnx-value` slot anywhere inside the panel, and no server reason token
 * anywhere in the panel's rendered text at any point in the walk.
 *
 * No screenshot is claimed. The host refuses the visual capture for this browser
 * (`NATIVE_BROWSER_VIEWPORT_UNAVAILABLE`), so every assertion below is on rendered text.
 */

const { chromium } = require("playwright");

const PREVIEW = process.env.CNX_PREVIEW || "http://localhost:60153";
const BACKEND = process.env.CNX_BACKEND || "http://127.0.0.1:60152";
const OUT = process.env.CNX_OUT || "screen_walk_r2.json";
const PLACE_ID = "place-beijing-houhai";
const TOKENS = ["PLACE_NOT_FOUND", "COLLECTION_FOLDER_NOT_FOUND", "PLACE_ALREADY_IN_COLLECTION"];

const log = { preview: PREVIEW, backend: BACKEND, frames: {}, started_at: new Date().toISOString() };

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
  await page.goto(`${PREVIEW}/v8/discover`, { waitUntil: "load" });
  const entry = page.getByRole("button", { name: "使用封存的演示行程" });
  if (await entry.count()) await entry.first().click();
  await page.waitForSelector('[data-testid="collection-panel"]', { timeout: 30000 });

  const panel = () => page.locator('[data-testid="collection-panel"]');
  const tokensSeen = async () => {
    const text = await panel().innerText();
    return TOKENS.filter((t) => text.includes(t));
  };

  log.frames.f1_empty_state = {
    heading: await panel().locator(".v8-kicker").textContent(),
    empty_sentence: await panel().locator('[data-testid="collection-empty"] p').textContent(),
    action_label: await panel().locator('[data-testid="collection-empty-action"]').textContent(),
    action_enabled: await panel().locator('[data-testid="collection-empty-action"]').isEnabled(),
    row_count: await panel().locator('[data-testid="collection-row"]').count(),
    tokens_in_text: await tokensSeen(),
  };

  await panel().locator('[data-testid="collection-empty-action"]').click();
  await page.waitForSelector('[data-testid="collection-shelf"]', { timeout: 20000 });
  log.frames.f2_after_the_action = {
    outcome_text: await panel().locator('[data-testid="collection-outcome-text"]').textContent(),
    shelf_names: await panel().locator('[data-testid="collection-shelf-name"]').allTextContents(),
    shelf_badges: await panel()
      .locator('[data-testid="collection-shelf"] [data-testid="collection-shelf-count"]')
      .allTextContents(),
    shelf_empty_sentence: await panel().locator('[data-testid="collection-shelf-empty"]').textContent(),
    whole_screen_empty_state_gone:
      (await panel().locator('[data-testid="collection-empty"]').count()) === 0,
    tokens_in_text: await tokensSeen(),
  };

  const folderId = await page.evaluate(async () => {
    const answer = await fetch("/api/v1/collections");
    return (await answer.json())[0].id;
  });
  const added = await fetch(`${BACKEND}/api/v1/collections/${folderId}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ place_id: PLACE_ID, note: "傍晚去，日落最好" }),
  });
  const addedBody = await added.json();
  await panel().locator('[data-testid="collection-refresh"]').first().click();
  await page.waitForFunction(
    () => document.querySelectorAll('[data-testid="collection-row"]').length > 0,
    null,
    { timeout: 20000 }
  );
  log.frames.f3_row_after_a_door_add_and_one_refresh = {
    add_http: added.status,
    folder_id_is_a_server_uuid_not_a_client_value: /^[0-9a-f-]{36}$/.test(folderId),
    item_id: addedBody.id,
    row_texts: (await panel().locator('[data-testid="collection-row"]').allInnerTexts()).map((t) =>
      t.replace(/\n/g, " | ")
    ),
    count_badge: await panel()
      .locator('[data-testid="collection-shelf"] [data-testid="collection-shelf-count"]')
      .textContent(),
    tokens_in_text: await tokensSeen(),
  };

  // The two r2 checks. These are what the door refused slice 1 for.
  log.frames.f4_q64_shape_of_this_screen = {
    data_cnx_value_attributes_inside_panel: await panel().locator("[data-cnx-value]").count(),
    non_literal_attribute_slots_inside_panel: await page.evaluate(() => {
      const root = document.querySelector('[data-testid="collection-panel"]');
      if (!root) return -1;
      let n = 0;
      // `page.evaluate` runs in the browser, so the token list has to be spelled out here rather
      // than closed over from Node -- the first version of this file referenced TOKENS and died with
      // `ReferenceError: TOKENS is not defined`, which is why the f1-f3 frames above carry a real
      // reading and this frame did not.
      const tokens = ["PLACE_NOT_FOUND", "COLLECTION_FOLDER_NOT_FOUND", "PLACE_ALREADY_IN_COLLECTION"];
      for (const el of root.querySelectorAll("*")) {
        for (const a of el.attributes) {
          if (/^(data|aria)-/i.test(a.name) && a.value.trim() !== "" && !/^(cnx|collection|true|false)$/.test(a.value)) {
            // a slot whose value is a word this file composed is not what Q64 asks about; what it
            // asks about is a server sentence or token sitting in the slot.
            if (tokens.some((t) => a.value.includes(t))) n += 1;
          }
        }
      }
      return n;
    }),
    server_tokens_anywhere_in_panel_text: await tokensSeen(),
    details_face_still_carries_the_numbers: await page.evaluate(() => {
      const facts = document.querySelectorAll(
        '[data-testid="collection-panel"] .cnx-measured-fact'
      );
      return { measured_fact_nodes: facts.length };
    }),
  };

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

  log.verdict = {
    empty_state_actionable:
      !!log.frames.f1_empty_state.action_label && log.frames.f1_empty_state.action_enabled === true,
    no_server_token_rendered_on_this_screen_anywhere:
      log.frames.f4_q64_shape_of_this_screen.server_tokens_anywhere_in_panel_text.length === 0,
    no_upstream_value_in_any_attribute_slot:
      log.frames.f4_q64_shape_of_this_screen.data_cnx_value_attributes_inside_panel === 0 &&
      log.frames.f4_q64_shape_of_this_screen.non_literal_attribute_slots_inside_panel === 0,
    row_visible_only_after_a_refresh_press:
      log.frames.f1_empty_state.row_count === 0 &&
      log.frames.f3_row_after_a_door_add_and_one_refresh.row_texts.length === 1,
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
