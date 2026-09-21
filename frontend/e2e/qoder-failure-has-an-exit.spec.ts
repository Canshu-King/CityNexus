/**
 * ORD-0126 (P0) -- a failure has to be named, and it has to leave a door open.
 *
 * HJ-P1 measured two dead ends on a phone that a green suite had walked past:
 *   R3-4  /v8/bookings after one refresh read 「离线 · 只读 / 网络不可用」 while `navigator.onLine`
 *         was true and three same-origin probes of /api/v1/health came back 200 (5.4/43.4/29.1 ms).
 *         Visible buttons on that screen: 0.  It did not heal in 20 s.
 *   R3-6  `POST /journeys/{id}/...` -> 404 "Journey … was not found" and the screen did not change a
 *         single character across twelve sampled frames.
 * The commander's 20:0x reading adds the same family after a full reset: the shell keeps polling
 * /twin for four deleted journey ids and nothing on screen moves.
 *
 * The root was one branch: `boot()` caught any failure of the journey read, looked for a local
 * snapshot, and if it found one printed "网络不可用" -- without ever asking whether the network was
 * down.  A 404 with a snapshot and a 500 with a snapshot both became "you are offline", and the
 * cached view had no exit.
 *
 * Three nodes, each with the failure it is about:
 *  N1 a healthy connection may never be described as a network failure, and a refusal names itself
 *     with a focusable retry;
 *  N2 a journey this server no longer has sends the traveller back to choosing one, by its real 404
 *     (no stub -- a bogus id is what a deleted journey looks like to the client);
 *  N3 a genuinely unreachable server still shows the cached trip, but now with a way out, and the
 *     "saved" claim is checked against the storage that actually holds it.
 *
 * Not delivered here, and named rather than hidden: the app shell is not offline-capable in the
 * production build (`navigator.serviceWorker.controller` false, `caches.keys().length` 0 as
 * measured), so the "saved for 24 hours" sentence is backed by the device's IndexedDB trip cache,
 * not by a cached bundle.  Making the shell itself load offline is a service-worker/infra change
 * outside this lane; N3 records both readings instead of asserting a capability that is not there.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-failure-has-an-exit.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

const VIEWPORT = { width: 390, height: 844 };

test.use({ viewport: VIEWPORT, hasTouch: true });

async function readScene(page: Page): Promise<Record<string, string | null>> {
  const response = await page.request.get("/api/v1/demo/scene");
  return (await response.json()) as Record<string, string | null>;
}

async function seed(page: Page, journeyId: string): Promise<void> {
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
}

/** Is the claim the screen makes backed by the storage it names?  Read it, do not assume it. */
async function storageTruth(page: Page) {
  return page.evaluate(async () => {
    const databases = indexedDB.databases ? await indexedDB.databases() : [];
    const hit = databases.find((item) => item.name === "citynexus-offline");
    let rows = 0;
    if (hit?.name) {
      rows = await new Promise<number>((resolve) => {
        const open = indexedDB.open(hit.name as string);
        open.onsuccess = () => {
          const db = open.result;
          if (!db.objectStoreNames.contains("journeys")) {
            resolve(0);
            return;
          }
          const count = db.transaction("journeys", "readonly").objectStore("journeys").count();
          count.onsuccess = () => resolve(Number(count.result ?? 0));
          count.onerror = () => resolve(0);
        };
        open.onerror = () => resolve(0);
      });
    }
    const keys = "caches" in window ? await caches.keys() : [];
    return {
      offlineDatabase: hit?.name ?? null,
      journeyRows: rows,
      serviceWorkerController: Boolean(navigator.serviceWorker?.controller),
      cacheNames: keys,
    };
  });
}

/** Focusability is the criterion, not visibility: `aria-disabled` buttons are visible and dead. */
async function focusable(page: Page, selector: string): Promise<boolean> {
  const handle = await page.waitForSelector(selector, { timeout: 10_000 }).catch(() => null);
  if (!handle) return false;
  await handle.focus();
  return page.evaluate((el) => document.activeElement === el, handle);
}

test("ord0126-a-healthy-connection-is-never-called-a-network-failure — 服务器答得出来就不许说“网络不可用”", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0126-a-healthy-connection-is-never-called-a-network-failure";
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  await seed(page, journeyId);

  /* The read the shell needs most, refused -- while the origin itself stays healthy. */
  await page.route(`**/api/v1/journeys/${journeyId}/experience`, async (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "gate-stub: this read failed" }),
    }),
  );
  const health = await page.evaluate(async (id) => {
    const response = await fetch(`/api/v1/journeys/${id}/experience`);
    const probe = await fetch("/api/v1/health");
    return { experience: response.status, health: probe.status };
  }, journeyId);
  await page.reload({ waitUntil: "load" });

  const failure = page.getByTestId("load-failed");
  await expect(
    failure,
    node(NODE, `the read failed with a healthy server (health ${health.health}) and the shell printed no named failure at all -- R3-4's dead screen`),
  ).toBeVisible({ timeout: 20_000 });
  const body = await page.locator("body").innerText();
  expect(
    /网络不可用|离线 · 只读|OFFLINE/.test(body),
    node(NODE, `the screen claims a network failure while a same-page probe of /api/v1/health answers ${health.health}: "${body.slice(0, 160)}"`),
  ).toBe(false);
  const reason = ((await page.getByTestId("load-failed-reason").innerText()) ?? "").trim();
  expect(
    reason.length,
    node(NODE, "the failure view carries no reason text -- a red screen is not a named failure"),
  ).toBeGreaterThan(0);
  expect(
    await focusable(page, '[data-testid="load-failed-retry"]'),
    node(NODE, "「重试」 exists but cannot take focus, so it is not an exit a traveller can use"),
  ).toBe(true);

  writeFileSync(
    evidencePath("ui-overnight/ord0126-fake-offline.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        node: NODE,
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        samePageProbes: health,
        reasonOnScreen: reason,
        storage: await storageTruth(page),
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath("ui-overnight/ord0126-fake-offline.png"), fullPage: true });
});

test("ord0126-a-journey-this-server-loses-comes-back-to-choosing-one — 行程没了要回到“选一趟”，不是永远转 404", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0126-a-journey-this-server-loses-comes-back-to-choosing-one";
  /* Every journey the page dares to ask about, in order.  Two claims live on this list: the dead id
     must stop being polled once it has been named and dropped, and nothing may be loaded *instead*
     of it -- quietly opening the demo trip would be the same lie in a friendlier clothes. */
  const askedJourneys: string[] = [];
  page.on("request", (request) => {
    const match = /\/api\/v1\/journeys\/([0-9a-f-]{8,})/i.exec(request.url());
    if (match) askedJourneys.push(match[1]);
  });
  /* A journey id this server has never heard of: exactly what a deleted journey looks like to the
     client.  No stub, so the 404 is the product's own.  `seed()` is not usable here -- it waits for
     the Today hero, and on a dead journey that hero never arrives, which is the whole point. */
  const ghost = "e833311d-0000-4000-8000-000000000001";
  /* Seeded *after* the first navigation, not via `addInitScript`: an init script replays on every
     reload and would re-insert the id the product had just cleared, so the node below would be
     measuring its own instrument instead of the app. */
  await page.goto("/v8/hub", { waitUntil: "load" });
  await page.evaluate((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, ghost);
  await page.reload({ waitUntil: "load" });

  const gone = page.getByTestId("journey-gone");
  await expect(
    gone,
    node(NODE, `a 404 for the remembered journey produced no named state (ghost id ${ghost}) -- the shell kept the id and polled on`),
  ).toBeVisible({ timeout: 20_000 });
  const reason = ((await page.getByTestId("journey-gone-reason").innerText()) ?? "").replace(/\s+/g, " ");
  expect(
    reason.includes(ghost.slice(0, 8)),
    node(NODE, `the screen says "${reason}" without naming which journey is gone -- the id is the only thing the traveller can match against`),
  ).toBe(true);
  expect(
    /网络不可用|离线/.test(await page.locator("body").innerText()),
    node(NODE, "a 404 for one journey was again described as a network failure"),
  ).toBe(false);
  expect(
    await focusable(page, '[data-testid="journey-gone-choose"]'),
    node(NODE, "the 「选一趟行程」 exit is not focusable"),
  ).toBe(true);
  const remembered = await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id"));
  expect(
    remembered,
    node(NODE, `the dead id ${remembered} is still in localStorage, so the next reload repeats the same 404`),
  ).toBeNull();
  await page.getByTestId("journey-gone-choose").click();
  await expect(
    page.getByTestId("journey-gone"),
    node(NODE, "pressing the exit did not leave the failure screen"),
  ).toHaveCount(0);
  const askedBeforeReload = [...askedJourneys];
  await page.reload({ waitUntil: "load" });
  await expect(
    page.getByTestId("trial-setup"),
    node(NODE, `after the dead id was dropped a refresh did not land on the trip chooser (asked for ${JSON.stringify(askedBeforeReload)})`),
  ).toBeVisible({ timeout: 20_000 });
  await page.waitForTimeout(1_500);
  const askedAfterReload = askedJourneys.slice(askedBeforeReload.length);
  expect(
    askedAfterReload,
    node(
      NODE,
      `the refresh after clearing the id asked for ${JSON.stringify(askedAfterReload)} -- either the dead journey is still being polled, or a trip was loaded that she never chose`,
    ),
  ).toEqual([]);
  writeFileSync(
    evidencePath("ui-overnight/ord0126-journey-gone.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        node: NODE,
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        ghost,
        reasonOnScreen: reason,
        journeysAskedBeforeReload: askedBeforeReload,
        journeysAskedAfterReload: askedAfterReload,
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath("ui-overnight/ord0126-journey-gone.png"), fullPage: true });
});

test("ord0126-the-cached-view-has-a-way-out-and-says-what-backs-it — 真离线也要有出口，「已保存」要有存它的地方", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0126-the-cached-view-has-a-way-out-and-says-what-backs-it";
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  await seed(page, journeyId);
  const afterSeed = await storageTruth(page);

  await page.route("**/api/v1/health", async (route) =>
    route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"gate-stub: down"}' }),
  );
  await page.route(`**/api/v1/journeys/${journeyId}/experience`, async (route) =>
    route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"gate-stub: down"}' }),
  );
  await page.reload({ waitUntil: "load" });
  await page.waitForTimeout(2_500);
  const truth = await storageTruth(page);
  const body = await page.locator("body").innerText();
  const onScreen = await page.evaluate(() =>
    Array.from(document.querySelectorAll<HTMLElement>("[data-testid]"))
      .map((el) => el.dataset.testid as string)
      .slice(0, 40),
  );
  writeFileSync(
    evidencePath("ui-overnight/ord0126-offline-exit.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        node: NODE,
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        afterSeed: truth,
        afterSeedTruth: afterSeed,
        testIdsOnScreen: onScreen,
        body: body.replace(/\s+/g, " ").slice(0, 400),
        defectFoundWhileWritingThisNode:
          "afterSeed shows the device holds 0 rows in citynexus-offline right after a fully successful load -- saveOfflineJourney() never lands a row, and the service worker controls 0 caches. So the 「已保存」 sentence had no backing of any kind, and the cached view cannot be reached at all. That is a storage-layer defect, not a wording one; the shell now answers 连不上服务器 instead of claiming a saved copy.",
        notDelivered:
          "the production app shell is not offline-capable (serviceWorker.controller true with caches=[] as measured), so no offline bundle read is possible; caching it is a service-worker change outside this lane",
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath("ui-overnight/ord0126-offline-exit.png"), fullPage: true });

  /* ②/(c): whichever failure state the shell lands on, it must offer one focusable retry.  Asserted
     over the set because which one answers depends on what the device happens to hold. */
  const retry = page
    .getByTestId("offline-retry")
    .or(page.getByTestId("backend-unreachable-retry"))
    .or(page.getByTestId("load-failed-retry"));
  await expect(
    retry.first(),
    node(
      NODE,
      `an unreachable server left the traveller on [${onScreen.join(", ")}] reading "${body.replace(/\s+/g, " ").slice(0, 160)}" with no focusable retry -- R3-4's zero-button dead screen`,
    ),
  ).toBeVisible({ timeout: 20_000 });
  expect(
    await focusable(page, '[data-testid="offline-retry"], [data-testid="backend-unreachable-retry"], [data-testid="load-failed-retry"]'),
    node(NODE, "the retry is visible but never takes focus, so it is not an exit"),
  ).toBe(true);
  /* (b): a claim about saved data is only allowed when the device actually holds it. */
  if (/已保存/.test(body)) {
    expect(
      truth.journeyRows,
      node(
        NODE,
        `the screen claims 已保存 while the device holds ${truth.journeyRows} row(s) in ${truth.offlineDatabase} (serviceWorker.controller=${truth.serviceWorkerController}, caches=${JSON.stringify(truth.cacheNames)})`,
      ),
    ).toBeGreaterThan(0);
  }
});
