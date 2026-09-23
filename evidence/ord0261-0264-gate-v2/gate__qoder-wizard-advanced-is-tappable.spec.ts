/**
 * ORD-0261 + ORD-0264 -- wizard "高级设置" tappability, under the arbiter's 17:19 contract.
 *
 *   ORD-0264 contract = SCROLL_REACHABLE_AND_TAPPABLE (NOT "visible at scrollTop"): the opener is a
 *   secondary/advanced entry, so it must stay in step 1, be reachable by ordinary scrolling, be free
 *   of chrome at rest, hit-test to itself, and really open the details — with the draft intact.
 *
 * The five cells the ruling names:
 *   1 locality    — the opener belongs to the step-1 region it opens, asserted by DOM containment
 *                   inside the rendered step-1 card (NOT class-name geometry), so "move it back to
 *                   the page tail" is a meaningful reverse mutation;
 *   2 human path  — scrollIntoView is a geometric diagnostic only; the evidence of reachability is a
 *                   real mouse wheel roll with a recorded scrollY delta, then the centre hit-test;
 *   3 semantics   — the seven required behaviours asserted one by one, including "draft survives
 *                   scrolling and expanding";
 *   4 arms        — K261_REMOVE_STICKY_RESERVE and K264_MOVE_OPENER_BACK_TO_PAGE_TAIL (overlap reds
 *                   under K264 are collateral, not independent evidence — that is what locality buys);
 *   5 control     — 「看支持的目的地」 stays as the positive control so the gate cannot drift into
 *                   "every summary must be big and centred".
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-wizard-advanced-is-tappable.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const VIEWPORT = { width: 390, height: 844 };
test.use({ viewport: VIEWPORT, hasTouch: true });

const LABELS = ["高级设置", "看支持的目的地"];
/** A typed word that must survive scrolling and expanding (ruling cell 3). */
const DRAFT_WORD = "外滩";

type Hit = {
  label: string;
  role: string;
  box: [number, number];
  centre: [number, number];
  hitTag: string;
  hitText: string;
  hitsItself: boolean;
  inViewport: boolean;
  scrollY: number;
};

async function openWizard(page: Page) {
  const seeded = (await (await page.request.get("/api/v1/demo/scene")).json()) as {
    journey_id?: string;
  };
  const journeyId = String(seeded.journey_id ?? "");
  expect(journeyId.length, node("seed", "/api/v1/demo/scene returned no journey_id")).toBeGreaterThan(8);
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", "zh-CN");
    localStorage.removeItem("citynexus.v8.journey_id");
  }, journeyId);
  await page.goto("/v8", { waitUntil: "load" });
  await page.waitForTimeout(1_000);
}

async function typeDraft(page: Page) {
  const city = page.getByTestId("trial-city");
  await expect(city).toBeVisible({ timeout: 15_000 });
  await city.fill(DRAFT_WORD);
  expect(await city.inputValue(), node("draft", "the fixture word did not land in the field")).toBe(DRAFT_WORD);
}

/**
 * Human-path witness: roll the mouse wheel until the element intersects the viewport, recording the
 * scrollY delta. `scrollIntoView` teleports and proves nothing about a traveller's reach.
 */
async function wheelToControl(page: Page, selector: string) {
  const before = await page.evaluate(() => Math.round(window.scrollY));
  for (let roll = 0; roll < 30; roll += 1) {
    const visible = await page.evaluate((sel) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      const box = el.getBoundingClientRect();
      return box.top >= 0 && box.bottom <= window.innerHeight && box.height > 0;
    }, selector);
    if (visible) break;
    await page.mouse.wheel(0, 240);
    await page.waitForTimeout(120);
  }
  const after = await page.evaluate(() => Math.round(window.scrollY));
  return { before, after, scrolled: after - before };
}

async function centreProbe(page: Page, selector: string) {
  return await page.$eval(
    selector,
    (el) => {
      const box = el.getBoundingClientRect();
      const cx = box.left + box.width / 2;
      const cy = box.top + box.height / 2;
      const landed = document.elementFromPoint(cx, cy);
      return {
        box: [Math.round(box.width), Math.round(box.height)] as [number, number],
        centre: [Math.round(cx), Math.round(cy)] as [number, number],
        hitTag: landed ? landed.tagName : "",
        hitText: landed ? (landed.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 20) : "",
        hitsItself: landed === el || (!!landed && el.contains(landed)),
        inViewport: cy >= 0 && cy <= window.innerHeight,
        scrollY: Math.round(window.scrollY),
      };
    },
  );
}

test("ord0261-sticky-bar-must-not-cover-the-summary-row — sticky 条不许压住 summary 行", async ({ page }) => {
  test.setTimeout(180_000);
  await openWizard(page);
  await typeDraft(page);

  // Human-path witness for the summary too: the row starts below the fold at 390x844.
  const roll = await wheelToControl(page, ".trial-advanced > summary");
  const probe = await centreProbe(page, ".trial-advanced > summary");
  expect(
    probe.hitsItself,
    node(
      "ord0261",
      `after a real wheel roll of ${roll.scrolled}px the summary's centre (${probe.centre.join(",")}) hit <${probe.hitTag}> "${probe.hitText}" instead of the summary itself`,
    ),
  ).toBe(true);
  expect(roll.scrolled, node("ord0261", "the wheel produced no scroll, so nothing was reached")).toBeGreaterThan(0);

  // Positive control: a genuinely free control must still pass, so the gate cannot become
  // "every disclosure must be big and centred".
  await wheelToControl(page, ".trial-supported > summary");
  const control = await centreProbe(page, ".trial-supported > summary");
  expect(control.hitsItself, node("ord0261", "the positive control no longer hits itself")).toBe(true);

  writeFileSync(
    evidencePath("ord0261-tappability-reading.json"),
    JSON.stringify(
      { generatedBy: "e345b9d6", order: "ORD-0261", viewport: VIEWPORT, wheel: roll, summaryProbe: probe, controlProbe: control },
      null,
      1,
    ),
  );
});

test("ord0264-opener-is-scroll-reachable-and-tappable — 高级入口要滚得到、点得动、不伤草稿", async ({ page }) => {
  test.setTimeout(240_000);
  await openWizard(page);
  await typeDraft(page);

  // Cell 1, locality: the opener must live inside the rendered step-1 card -- the DOM region it
  // opens. Asserted by containment, not by class names or geometry.
  const locality = await page.evaluate(() => {
    const opener = document.querySelector('[data-testid="trial-show-advanced"]');
    const stepCard = document.querySelector('[data-testid="trial-step1-body"], .trial-advanced')?.closest(
      '[data-testid="trial-step1-body"]',
    );
    const details = document.querySelector(".trial-advanced");
    return {
      openerPresent: !!opener,
      insideStep1Card: !!opener && !!stepCard && stepCard.contains(opener),
      adjacentToItsDetails: !!opener && !!details && (details.contains(opener) || details.nextElementSibling === opener || opener.nextElementSibling === details || details.parentElement === opener.parentElement),
    };
  });
  expect(locality.openerPresent, node("ord0264", "the opener button is not rendered at all")).toBe(true);
  expect(
    locality.insideStep1Card,
    node(
      "ord0264",
      `the opener is not inside the step-1 card it belongs to (locality ${JSON.stringify(locality)}) -- moved back to the page tail?`,
    ),
  ).toBe(true);
  expect(
    locality.adjacentToItsDetails,
    node("ord0264", `the opener is not adjacent to the details it opens: ${JSON.stringify(locality)}`),
  ).toBe(true);

  // Cell 2, human path: an ordinary wheel roll must bring it into the viewport. Recorded delta is
  // the proof the scroll really happened; scrollIntoView is not used here at all.
  const roll = await wheelToControl(page, '[data-testid="trial-show-advanced"]');
  expect(
    roll.scrolled,
    node("ord0264", `the wheel rolled 0px -- the opener is not scroll-reachable (${JSON.stringify(roll)})`),
  ).toBeGreaterThan(0);

  const probe = await centreProbe(page, '[data-testid="trial-show-advanced"]');
  expect(
    probe.inViewport,
    node("ord0264", `after scrolling ${roll.scrolled}px the opener's centre is at y=${probe.centre[1]} -- still out of reach`),
  ).toBe(true);
  expect(
    probe.hitsItself,
    node(
      "ord0264",
      `the opener's centre hit <${probe.hitTag}> "${probe.hitText}" instead of the button -- chrome covering it at rest`,
    ),
  ).toBe(true);

  // Draft survival across the scroll (cell 3): what the traveller typed must still be there.
  expect(
    await page.getByTestId("trial-city").inputValue(),
    node("ord0264", "the typed draft did not survive the scroll"),
  ).toBe(DRAFT_WORD);

  // Cell 3 continued: a real click opens the advanced block, and the draft survives that too.
  await page.getByTestId("trial-show-advanced").click();
  await expect(page.locator(".trial-advanced")).toHaveAttribute("open", "");
  expect(
    await page.getByTestId("trial-city").inputValue(),
    node("ord0264", "the typed draft did not survive opening the advanced block"),
  ).toBe(DRAFT_WORD);

  writeFileSync(
    evidencePath("ord0264-scroll-reachable-reading.json"),
    JSON.stringify(
      { generatedBy: "e345b9d6", order: "ORD-0264", viewport: VIEWPORT, locality, wheel: roll, probe, draftWord: DRAFT_WORD },
      null,
      1,
    ),
  );
  await page.screenshot({ path: evidencePath(`ui-overnight/ord0264-reachable-${process.env.CITYNEXUS_E2E_RUN_ID ?? "dev"}.png`) });
});
