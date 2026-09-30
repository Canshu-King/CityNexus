/**
 * ORD-0485 — the import screen's evidence pill must speak a word, not a dictionary key.
 *
 * Measured on this lane's own served production bundle at 390x844: `/v8/import` printed
 * `poiImport.channelLocal` as the pill text, because `t(key)` answers with the key itself when
 * neither word table holds it (`i18n/LocaleContext.tsx` — `dictionaries[locale][key] ?? key`,
 * falling back through `en`).  The instrument `tools/i18n_key_gap_r1.py` counted the whole
 * family at that generation: 698 referenced keys, exactly two missing from BOTH tables --
 * `poiImport.channelLocal` (proved on screen) and `exec.state.notStarted` (no phone screen
 * reached it).  Both keys are the fix; this file is the carrier that reddens if either one
 * drifts back out of the dictionary.
 *
 * The frozen wording is held HERE, not imported from the product (ORD-0251's precedent): a gate
 * that reads its own expected string out of the code under test cannot notice a rename.
 *
 * Non-vacuity: the same spec run against the pre-fix generation on this lane's first face is
 * RED -- `poiImport.channelLocal` is in the painted text and 本地通道 is not.  Both readings
 * ship with the delivery.
 */
import { expect, test } from "@playwright/test";
import { scanScreenText } from "./_qoderTextScan";

const FILE = "e2e/qoder-ord0485-phone-words.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

const FROZEN_PILL_ZH = "本地通道";
const LEAKED_PILL_KEY = "poiImport.channelLocal";
const LEAKED_STATE_KEY = "exec.state.notStarted";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

async function seedJourney(page: import("@playwright/test").Page) {
  const seeded = (await (await page.request.get("/api/v1/demo/scene")).json()) as {
    journey_id?: string;
  };
  const journeyId = String(seeded.journey_id ?? "");
  expect(journeyId.length, node("seed", "/api/v1/demo/scene returned no journey_id")).toBeGreaterThan(8);
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id as string);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  return journeyId;
}

test("ord0485-1-the-import-pill-says-a-word-not-a-key — 导入屏的证据牌不得回吐字典键", async ({
  page,
}) => {
  test.setTimeout(180_000);
  await seedJourney(page);
  await page.goto("/v8/import", { waitUntil: "load" });

  const panel = page.getByTestId("poi-import");
  await expect(panel, node("ord0485-1", "the import panel never mounted")).toBeVisible({
    timeout: 20_000,
  });

  const scan = await scanScreenText(page);
  /* The scan has to have had something to look at: a zero-leaf read is not "no leak". */
  expect(scan.visualLeaves, node("ord0485-1", "the painted-text scan read no leaves at all")).toBeGreaterThan(
    10,
  );
  expect(
    scan.visual.includes(LEAKED_PILL_KEY),
    node("ord0485-1", `the pill fell back to the dictionary key: ${LEAKED_PILL_KEY}`),
  ).toBe(false);
  expect(
    scan.accessible.includes(LEAKED_PILL_KEY),
    node("ord0485-1", `the key is not painted but an announcer can still speak it: ${LEAKED_PILL_KEY}`),
  ).toBe(false);
  expect(
    scan.visual.includes(FROZEN_PILL_ZH),
    node("ord0485-1", `the pill does not read the frozen wording either (${FROZEN_PILL_ZH})`),
  ).toBe(true);
});

test("ord0485-2-no-execution-state-key-reaches-any-phone-screen — 执行状态词表不许把键名放上屏", async ({
  page,
}) => {
  test.setTimeout(180_000);
  await seedJourney(page);
  /* The state words ride the recovery/executive surfaces; /v8/authoritative is the phone screen
     that mounts the plan-version history and the V12 panel, so it is where a missing entry would
     show up first. */
  await page.goto("/v8/authoritative", { waitUntil: "load" });
  const page0 = page.getByTestId("v12-authoritative-page");
  await expect(page0, node("ord0485-2", "the recovery screen never mounted")).toBeVisible({
    timeout: 20_000,
  });
  /* The activity rows arrive with the plan read, one round-trip after the shell mounts.  Waiting
     for the list to paint is a precondition, not a threshold: the wait itself is reported, so a
     reader can tell "settled and clean" from "looked too early". */
  const FROZEN_DONE_ZH = "已完成";
  let scan = await scanScreenText(page);
  let waitedMs = 0;
  while (waitedMs < 30_000 && !scan.visual.includes(FROZEN_DONE_ZH)) {
    await page.waitForTimeout(1_000);
    waitedMs += 1_000;
    scan = await scanScreenText(page);
  }
  expect(
    waitedMs < 30_000,
    node(
      "ord0485-2",
      `the plan read never painted its activity states (waited ${String(waitedMs)} ms), ` +
        `so the absence below would describe the instrument, not the screen`,
    ),
  ).toBe(true);
  expect(scan.visualLeaves, node("ord0485-2", "empty scan, so the absence below proves nothing")).toBeGreaterThan(
    10,
  );
  expect(
    scan.visual.includes(LEAKED_STATE_KEY),
    node("ord0485-2", `a missing exec.state entry reached the painted text: ${LEAKED_STATE_KEY}`),
  ).toBe(false);
  /* And the sibling vocabulary the panel actually prints stays intact -- the fix must not have
     renamed a state a traveller already reads. */
  for (const word of [FROZEN_DONE_ZH, "活跃", "计划中"]) {
    expect(scan.visual.includes(word), node("ord0485-2", `state word missing from the screen: ${word}`)).toBe(
      true,
    );
  }
  // eslint-disable-next-line no-console
  console.log(node("ord0485-2", `settled after ${String(waitedMs)} ms of waiting for the plan read`));
});
