/**
 * ORD-0362 -- what the shipped preparation panel's words actually depend on, measured on the payload.
 *
 * The pair this covers is the one that exists on real phones today: a shell of this generation reads
 * a server whose capability answer has grown keys before (the ORD-0245 jump) and has grown further
 * since (measured at this tip: 29 top-level keys, 27 on the HYDRATABLE answer and 29 on the
 * UNAVAILABLE ones).  A half-missing answer and an answer carrying fields this shell has never seen
 * must both leave the traveller's screen saying the same thing -- a payload the shell cannot fully
 * recognise is not a failure of the traveller's, and must not be rendered as one.
 *
 * One test, two readings of the same destination:
 *   A -- the server's own answer, untouched;
 *   B -- the same answer with every key the panel provably does not read removed, plus three field
 *        names no version of the server has ever sent.
 * The claim is that A and B are the same screen: same verdict, same visible copy, same set of
 * pressable actions, and no error surfaced by B that A does not also have.
 *
 * The key split is not a guess.  READ_KEYS below are the fields the shipped component takes off the
 * capability object (each appears as `capability?.<name>` in DestinationPreparationPanel.tsx);
 * everything else the server sends is dropped by B, which is why B removes 20 of the 29 keys -- well
 * past "half missing".  `CITYNEXUS_ORD0362_EXTRA_DROP` exists so the arm that must fail can be run
 * without editing this file: naming a key from READ_KEYS there makes B a different screen, and the
 * gate goes red on purpose, which is what proves the gate is looking at the payload at all.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-ord0362-old-shell-payload-compat.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

/** The fields the shipped panel reads off the capability answer, named in the order the component
 *  reaches them (DestinationPreparationPanel.tsx:146-149, :299, :363 and the verdict block). */
const READ_KEYS = [
  "capability",
  "reason_code",
  "recommended_action",
  "missing_categories",
  "coverage",
  "candidates",
  "retryable",
  "pending_destination_label",
  "query",
];

/** Field names this server has never sent, in any vintage. */
const UNKNOWN_KEYS: Record<string, unknown> = {
  n1_field_no_shell_has_seen: "unknown",
  n1_next_generation_object: { nested: { deeper: 1 } },
  n1_next_generation_list: [{ also: "unknown" }],
};

const EXTRA_DROP = (process.env.CITYNEXUS_ORD0362_EXTRA_DROP ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

/* `DROP_ONE` changes the shape of B without changing anything else about it: every key the server
   sent is kept except the named one, so two runs that differ only in that name differ only in the
   key removed.  That is the pair the order asks for -- an unread key removed must leave the gate
   green, a key the panel reads must redden it.  Unset, B is the broad claim in the header: every
   unread key absent. */
const DROP_ONE = (process.env.CITYNEXUS_ORD0362_DROP_ONE ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const VIEWPORT = { width: 390, height: 844 };
test.use({ viewport: VIEWPORT, hasTouch: true });

async function openDiscover(page: Page): Promise<void> {
  const seeded = (await (await page.request.get("/api/v1/demo/scene")).json()) as {
    journey_id?: string;
  };
  const journeyId = String(seeded.journey_id ?? "");
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
  await page.goto("/v8/discover", { waitUntil: "load" });
  await expect(page.getByTestId("prep-panel"), node("prep-panel", "no panel on the discover surface")).toBeVisible({
    timeout: 30_000,
  });
}

/** Everything a traveller could tell apart about the screen, as data. */
async function readScreen(page: Page) {
  const verdict = page.getByTestId("prep-verdict");
  const panel = page.getByTestId("prep-panel");
  return {
    verdict_present: await verdict.count().then((n) => n > 0),
    capability: (await verdict.getAttribute("data-capability")) ?? null,
    panel_text: (await panel.innerText()).replace(/\s+/g, " ").trim(),
    actions: await page.evaluate(() =>
      Array.from(document.querySelectorAll<HTMLElement>("[data-testid^='prep-']"))
        .filter((el) => el.tagName === "BUTTON" && !el.hasAttribute("disabled") && el.offsetParent !== null)
        .map((el) => el.dataset.testid as string)
        .sort(),
    ),
    error_text: await page.evaluate(() => {
      const el = document.querySelector("[data-testid='prep-error'], .prep-error");
      return el ? (el.textContent ?? "").replace(/\s+/g, " ").trim() : null;
    }),
  };
}

/**
 * One run of the destination check with the capability answer passed through `transform`.
 * The server answers for real; only the keys change, which is the whole point of a payload-only gate.
 */
async function checkWith(page: Page, transform: (body: Record<string, unknown>) => Record<string, unknown>) {
  const seen: Array<{ keys: string[]; dropped: string[]; added: string[] }> = [];
  await page.route("**/api/v1/destinations/capability*", async (route) => {
    const real = await route.fetch();
    const body = (await real.json()) as Record<string, unknown>;
    const before = Object.keys(body).sort();
    const out = transform(body);
    seen.push({
      keys: before,
      dropped: before.filter((k) => !(k in out)),
      added: Object.keys(out).filter((k) => !before.includes(k)),
    });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(out) });
  });
  await page.getByTestId("prep-query").fill("厦门");
  await page.getByTestId("prep-check").click();
  await expect(page.getByTestId("prep-verdict")).toBeVisible({ timeout: 20_000 });
  const screen = await readScreen(page);
  return { screen, seen };
}

test("ord0362-a-screen-half-of-whose-keys-are-gone-says-the-same-thing — 少一半键、多未知字段，屏幕不得改口", async ({ page }) => {
  test.setTimeout(300_000);
  const NODE = "ord0362-a-screen-half-of-whose-keys-are-gone-says-the-same-thing";

  await openDiscover(page);
  const untouched = await checkWith(page, (b) => b);
  await page.unroute("**/api/v1/destinations/capability*");

  await openDiscover(page);
  const shaped = await checkWith(page, (b) => {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(b)) {
      const absent = DROP_ONE.length
        ? DROP_ONE.includes(k)
        : !READ_KEYS.includes(k) || EXTRA_DROP.includes(k);
      if (absent) continue;
      out[k] = v;
    }
    return { ...out, ...UNKNOWN_KEYS };
  });
  await page.unroute("**/api/v1/destinations/capability*");

  const observed = untouched.seen[0]?.keys ?? [];
  const droppedByDesign = observed.filter((k) => !READ_KEYS.includes(k));
  writeFileSync(
    evidencePath("ord0362-payload-compat.json"),
    JSON.stringify(
      {
        node: NODE,
        run_id: process.env.CITYNEXUS_E2E_RUN_ID ?? "dev",
        viewport: VIEWPORT,
        shape: DROP_ONE.length ? "drop-one" : "drop-all-unread",
        drop_one: DROP_ONE,
        extra_drop: EXTRA_DROP,
        read_keys_named_here: READ_KEYS,
        unread_keys_observed: droppedByDesign,
        unread_key_count: droppedByDesign.length,
        observed_top_level_keys: observed,
        observed_top_level_count: observed.length,
        dropped_absent_from_B: shaped.seen[0]?.dropped ?? [],
        dropped_count: (shaped.seen[0]?.dropped ?? []).length,
        unknown_fields_injected: Object.keys(UNKNOWN_KEYS),
        keys_kept_in_B: observed.filter((k) => !(shaped.seen[0]?.dropped ?? []).includes(k)),
        screen_A: untouched.screen,
        screen_B: shaped.screen,
        same_verdict: untouched.screen.capability === shaped.screen.capability,
        same_text: untouched.screen.panel_text === shaped.screen.panel_text,
        same_actions: JSON.stringify(untouched.screen.actions) === JSON.stringify(shaped.screen.actions),
      },
      null,
      1,
    ),
  );

  expect(untouched.screen.capability, node(NODE, "the untouched answer produced no verdict to compare against")).not.toBeNull();
  /* The "must not shatter" half: B has to be a screen with the same verdict and the same actions. */
  const actuallyDropped = shaped.seen[0]?.dropped ?? [];
  expect(shaped.screen.capability, node(NODE, `the verdict was lost when B removed ${actuallyDropped.length} key(s) named ${JSON.stringify(actuallyDropped)} (${untouched.screen.capability} -> ${shaped.screen.capability})`)).toBe(untouched.screen.capability);
  expect(shaped.screen.actions, node(NODE, `the pressable actions changed under shape=${DROP_ONE.length ? "drop-one" : "drop-all-unread"}: A=${JSON.stringify(untouched.screen.actions)} B=${JSON.stringify(shaped.screen.actions)}`)).toEqual(untouched.screen.actions);
  expect(shaped.screen.panel_text, node(NODE, `the sentence the traveller reads changed under shape=${DROP_ONE.length ? "drop-one" : "drop-all-unread"} (dropped ${JSON.stringify(shaped.seen[0]?.dropped ?? [])})`)).toBe(untouched.screen.panel_text);
  /* The "unknown fields are not an error" half: B carries three field names no server ever sent, and
     must not answer with an error A does not already have. */
  expect(shaped.screen.error_text, node(NODE, `unknown fields surfaced as an error: ${shaped.screen.error_text}`)).toBe(untouched.screen.error_text);
});
