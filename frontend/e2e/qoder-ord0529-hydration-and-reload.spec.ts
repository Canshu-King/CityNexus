/**
 * ORD-0529 (second half) — the empty trip cell asks the server to prepare the city, and it asks again.
 *
 * Two cells the commander cut at 17:16: name the hydration dead-end on this screen instead of sending
 * the traveller to another one, and stop the place count from being a memory.  Nothing here is stubbed:
 * the job is started through `POST /api/v1/catalog-hydrations` by a tap, polled through its own
 * `GET /api/v1/catalog-hydrations/{id}`, and the count comes back from `GET /api/v1/places?city_code=`.
 * Requests are counted from the browser's own network log, so "it re-read" is a number, not an intent.
 *
 *   H1 opening the cell writes nothing -- asking is a tap
 *   H2 the ask appears exactly where the catalogue is empty, and not where it is not
 *   H3 tapping it starts a real job and the screen follows it by polling
 *   H4 the dead end is said as a fact about the place, not as a fault, with no machine token painted
 *   H5 再读一次 actually re-asks the door
 *   H6 coming back to the tab re-asks it too (synthetic event, named as such)
 *   H7 the outcome vocabulary exists in exactly one file
 *   H8 a job that cannot prepare the city does not turn the empty catalogue into a full one
 */
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { evidencePath } from "./_qoderEvidence";
import { hydrationOutcomeCopy } from "../src/features/discovery/catalogHydrationCopy";

const ZERO_PLACE_JOURNEY = "1b849dc1-4488-4136-858d-7445dac19f63"; // CN-XIAMEN: no places, no source
const READY_CITY_JOURNEY = "011a2238-0a45-4840-9405-c28c098662e8"; // CNX-DEMO: 8 places
const MACHINE_WORD = /[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+/;

function write(name: string, body: unknown) {
  const p = evidencePath("qoder-ord0529b", name + ".json");
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(body, null, 1), "utf8");
  console.log("O529BGATE " + name + " " + JSON.stringify(body));
}

/** Counts the doors this screen actually knocked on, per method and path prefix. */
function tally(page: Page) {
  const hits: { method: string; path: string }[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/v1/")) hits.push({ method: request.method(), path: url.pathname });
  });
  return {
    hits,
    count: (method: string, prefix: string) =>
      hits.filter((h) => h.method === method && h.path.startsWith(prefix)).length,
  };
}

async function openTrip(page: Page, journeyId: string) {
  await page.addInitScript((id) => localStorage.setItem("citynexus.v8.journey_id", id), journeyId);
  await page.goto("/v8/trips", { waitUntil: "load" });
  await expect(page.getByTestId("trip-itinerary-empty")).toBeVisible({ timeout: 25_000 });
  await page.waitForTimeout(1_500);
}

test("H1 进这一格不写任何东西：问服务器是一枚点击，不是屏自己的主张", async ({ page }) => {
  const door = tally(page);
  await openTrip(page, ZERO_PLACE_JOURNEY);
  const writes = door.count("POST", "/api/v1/catalog-hydrations");
  expect(writes).toBe(0);
  write("H1_no_write_on_open", { post_hydration_on_open: writes, places_reads: door.count("GET", "/api/v1/places") });
});

test("H2 那枚动作只出现在目录真的空着的那格", async ({ page }) => {
  await openTrip(page, ZERO_PLACE_JOURNEY);
  await expect(page.getByTestId("trip-itinerary-empty-hydrate")).toBeVisible();
  await openTrip(page, READY_CITY_JOURNEY);
  await expect(page.getByTestId("trip-itinerary-empty-hydrate")).toHaveCount(0);
  write("H2_conditional_ask", { zero_city: true, ready_city: false });
});

test("H3 点下去是一桩真的任务，屏跟着它的记录走", async ({ page }) => {
  const door = tally(page);
  await openTrip(page, ZERO_PLACE_JOURNEY);
  await page.getByTestId("trip-itinerary-empty-hydrate").click();
  const cell = page.getByTestId("trip-itinerary-empty-hydration");
  await expect(cell).toBeVisible({ timeout: 15_000 });
  /* A single GET is only the first reading of the job the tap just created -- a screen that asks once
     and never again would pass that.  So the arm waits for the server's own ending to reach the
     screen, which requires the screen to have asked at least twice. */
  await expect(async () => {
    expect(await cell.innerText()).toContain("不是网络或服务器故障");
  }).toPass({ timeout: 30_000 });
  const started = door.count("POST", "/api/v1/catalog-hydrations");
  const polled = door.count("GET", "/api/v1/catalog-hydrations/");
  expect(started).toBe(1);
  expect(polled).toBeGreaterThanOrEqual(2);
  const sentence = await cell.innerText();
  write("H3_real_job_polled", { started, polled, sentence });
});

test("H4 补不出的那格说的是关于这个地方的事实，不是故障，也不印机词", async ({ page }) => {
  await openTrip(page, ZERO_PLACE_JOURNEY);
  await page.getByTestId("trip-itinerary-empty-hydrate").click();
  const cell = page.getByTestId("trip-itinerary-empty-hydration");
  await expect(async () => {
    expect(await cell.innerText()).toContain("不是网络或服务器故障");
  }).toPass({ timeout: 30_000 });
  const whole = await page.getByTestId("trip-itinerary-empty").innerText();
  expect(whole).not.toContain("NO_REGISTERED_SOURCE");
  expect(MACHINE_WORD.test(whole)).toBe(false);
  write("H4_dead_end_in_words", { sentence: await cell.innerText(), machine_tokens: 0 });
});

test("H5 再读一次是再去问门，不是把上一句重排一遍", async ({ page }) => {
  await openTrip(page, ZERO_PLACE_JOURNEY);
  const door = tally(page);
  const before = door.count("GET", "/api/v1/places");
  await page.getByTestId("trip-itinerary-empty-reread").click();
  await page.waitForTimeout(1_500);
  const after = door.count("GET", "/api/v1/places");
  expect(after).toBeGreaterThanOrEqual(before + 1);
  expect(await page.getByTestId("trip-itinerary-empty-catalogue").innerText()).toContain("一个地点都还没有");
  write("H5_reread_asks_again", { places_reads_before: before, places_reads_after: after });
});

test("H6 回到这一页会自动再问一次（事件是合成发出的，这里具名）", async ({ page }) => {
  await openTrip(page, ZERO_PLACE_JOURNEY);
  const door = tally(page);
  const before = door.count("GET", "/api/v1/places");
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    document.dispatchEvent(new Event("visibilitychange"));
    window.dispatchEvent(new Event("focus"));
  });
  await page.waitForTimeout(1_500);
  const after = door.count("GET", "/api/v1/places");
  expect(after).toBeGreaterThanOrEqual(before + 1);
  write("H6_return_to_tab_rereads", {
    synthetic_event: true,
    places_reads_before: before,
    places_reads_after: after,
  });
});

test("H7 结局词表只有一份：探索屏与这格读的是同一个文件", async () => {
  const panel = readFileSync("src/features/discovery/DestinationPreparationPanel.tsx", "utf8");
  const table = readFileSync("src/features/discovery/catalogHydrationCopy.ts", "utf8");
  const sentence = hydrationOutcomeCopy("NO_REGISTERED_SOURCE", "UNAVAILABLE", true).body;
  expect(table).toContain(sentence);
  expect(panel).not.toContain(sentence);
  expect(panel).toContain("hydrationOutcomeCopy(");
  write("H7_one_table", { in_module: true, in_panel: false, panel_delegates: true });
});

test("H9 那句关于目的地的实话是词表给的，不依赖屏也不依赖浏览器", async () => {
  /* Same fact as H4, taken straight from the table: a browser that cannot start on this box must not
     be able to hide whether the dead end is named honestly. */
  const zh = hydrationOutcomeCopy("NO_REGISTERED_SOURCE", "UNAVAILABLE", true);
  const en = hydrationOutcomeCopy("NO_REGISTERED_SOURCE", "UNAVAILABLE", false);
  expect(zh.body).toContain("不是网络或服务器故障");
  expect(zh.body).not.toContain("网络不可用");
  expect(en.body).toContain("not a network or server fault");
  expect(MACHINE_WORD.test(zh.title + zh.body)).toBe(false);
  write("H9_table_says_it_honestly", { zh_title: zh.title, zh_body: zh.body });
});

test("H8 补不出来的那格不把空目录说成有地点，也不假装已排", async ({ page }) => {
  await openTrip(page, ZERO_PLACE_JOURNEY);
  await page.getByTestId("trip-itinerary-empty-hydrate").click();
  const cell = page.getByTestId("trip-itinerary-empty-hydration");
  await expect(async () => {
    expect(await cell.innerText()).toContain("不是网络或服务器故障");
  }).toPass({ timeout: 30_000 });
  const catalogue = await page.getByTestId("trip-itinerary-empty-catalogue").innerText();
  expect(catalogue).toContain("一个地点都还没有");
  expect(catalogue).not.toMatch(/有 \d+ 个地点/);
  await expect(page.getByTestId("trip-itinerary")).toHaveCount(0);
  write("H8_no_invented_success", { catalogue, day_surface: 0 });
});
