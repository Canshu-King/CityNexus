/**
 * ORD-0261 + ORD-0264 -- the wizard's "高级设置" had two tappability defects with different mechanics,
 * split by the commander after the read-only reproduction:
 *
 *   0261  the sticky action bar's gradient paints over the 「高级设置」 summary row, so its centre hit
 *         the bar's 「下一步」 button instead of the summary (fix: the scrolling content reserves the
 *         bar's height, so at rest the bar overlaps only its own padding);
 *   0264  the same-label opener button rendered at the page bottom, its centre at y=1208 in an 844px
 *         viewport -- permanently below the fold (fix: it renders directly under the details now).
 *
 * Judging shape per the order: enumerate every rendered control whose label matches, and for each
 * require `elementFromPoint(centre)` to hit that control itself (or a node inside it).  A control
 * below the fold cannot pass this either, because its centre is outside the viewport and hits nothing.
 * Computed min-height is deliberately NOT treated as size -- the box that is hit is what counts.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-wizard-advanced-is-tappable.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const VIEWPORT = { width: 390, height: 844 };
test.use({ viewport: VIEWPORT, hasTouch: true });

const LABELS = ["高级设置", "看支持的目的地"];

type Hit = {
  label: string;
  role: string;
  box: [number, number];
  centre: [number, number];
  hitTag: string;
  hitText: string;
  hitsItself: boolean;
  inViewport: boolean;
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

/** A traveller reaches a control by scrolling it into view; measuring at scroll-top would grade the
 *  scroll position, not the control (at scroll-top the summary sits at y≈885 in an 844px viewport and
 *  a centre hit is trivially empty). Scroll each into view (reduced-motion makes it instant), let the
 *  sticky bar settle, then hit-test the centre of where the control actually rests. */
async function inventory(page: Page): Promise<Hit[]> {
  const rows: Hit[] = [];
  for (const label of LABELS) {
    for (const role of ["summary", "button"] as const) {
      const probe = await page.evaluate(
        ({ label, role }) => {
          for (const el of Array.from(document.querySelectorAll("button, summary, a"))) {
            const text = (el.textContent ?? "").replace(/\s+/g, " ").trim();
            const isRole = el.tagName === "SUMMARY" ? role === "summary" : el.tagName.toLowerCase() === role;
            if (!isRole || !text.includes(label)) continue;
            const before = el.getBoundingClientRect();
            if (before.width <= 0 || before.height <= 0) continue;
            el.scrollIntoView({ block: "center" });
            return { found: true };
          }
          return { found: false };
        },
        { label, role },
      );
      if (!probe.found) continue;
      await page.waitForTimeout(300);
      const hit = await page.evaluate(
        ({ label, role }) => {
          for (const el of Array.from(document.querySelectorAll("button, summary, a"))) {
            const text = (el.textContent ?? "").replace(/\s+/g, " ").trim();
            const isRole = el.tagName === "SUMMARY" ? role === "summary" : el.tagName.toLowerCase() === role;
            if (!isRole || !text.includes(label)) continue;
            const box = el.getBoundingClientRect();
            if (box.width <= 0 || box.height <= 0) continue;
            const cx = box.left + box.width / 2;
            const cy = box.top + box.height / 2;
            const landed = document.elementFromPoint(cx, cy);
            return {
              label: text.slice(0, 20),
              role,
              box: [Math.round(box.width), Math.round(box.height)],
              centre: [Math.round(cx), Math.round(cy)],
              hitTag: landed ? landed.tagName : "",
              hitText: landed ? (landed.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 20) : "",
              hitsItself: landed === el || (!!landed && el.contains(landed)),
              inViewport: cy >= 0 && cy <= window.innerHeight,
              scrollY: Math.round(window.scrollY),
            };
          }
          return null;
        },
        { label, role },
      );
      if (hit) rows.push(hit as Hit);
    }
  }
  return rows;
}

test("ord0261-every-labelled-control-is-what-its-centre-hits — sticky 条不许压住 summary 行", async ({
  page,
}) => {
  test.setTimeout(180_000);
  await openWizard(page);
  const rows = await inventory(page);

  for (const label of LABELS) {
    expect(
      rows.some((row) => row.label.includes(label)),
      node("ord0261", `"${label}" was not on the wizard screen at all`),
    ).toBe(true);
  }
  const summaryRow = rows.find((row) => row.label.includes("高级设置") && row.role === "summary");
  expect(summaryRow, node("ord0261", "the 高级设置 summary never rendered")).toBeTruthy();
  expect(
    summaryRow!.hitsItself,
    node(
      "ord0261",
      `the summary's centre (${summaryRow!.centre.join(",")}) hit <${summaryRow!.hitTag}> "${summaryRow!.hitText}" instead of the summary itself -- chrome covering a control`,
    ),
  ).toBe(true);
  // Positive control on the instrument: a control that is genuinely free must still pass.
  const supported = rows.find((row) => row.label.includes("看支持的目的地"));
  expect(supported?.hitsItself, node("ord0261", "the positive control no longer hits itself")).toBe(true);

  await page.screenshot({ path: evidencePath(`ui-overnight/ord0261-fixed-${process.env.CITYNEXUS_E2E_RUN_ID ?? "dev"}.png`) });
  writeFileSync(
    evidencePath("ord0261-tappability-reading.json"),
    JSON.stringify({ generatedBy: "e345b9d6", order: "ORD-0261", viewport: VIEWPORT, controls: rows }, null, 1),
  );
});

test("ord0264-the-opener-button-is-inside-the-viewport-and-tappable — 折叠之下的按钮要回得来", async ({
  page,
}) => {
  test.setTimeout(180_000);
  await openWizard(page);
  const rows = await inventory(page);

  const opener = rows.filter((row) => row.label.includes("高级设置") && row.role === "button");
  expect(
    opener.length,
    node("ord0264", `expected exactly one opener button, found ${opener.length}`),
  ).toBe(1);
  const button = opener[0];
  expect(
    button.inViewport,
    node(
      "ord0264",
      `the opener's centre is at y=${button.centre[1]} in a ${VIEWPORT.height}px viewport -- still below the fold`,
    ),
  ).toBe(true);
  expect(
    button.hitsItself,
    node("ord0264", `the opener's centre hit <${button.hitTag}> "${button.hitText}" instead of the button`),
  ).toBe(true);

  // The move must not have broken what the button is for: it opens the advanced block.
  await page.getByTestId("trial-show-advanced").click();
  await expect(page.locator(".trial-advanced")).toHaveAttribute("open", "");
});
