/**
 * The drawer's group-heading rule must not reach the desktop rail.
 *
 * Why this exists: the drawer and the rail share the class name `v8-nav-group`, but the rail paints
 * it on a plain heading span (`V8Experience.tsx`) while the drawer uses it as a collapsible toggle
 * button. When the drawer's grouping rule was written unscoped, the rail's heading inherited
 * `display:flex`, `cursor:pointer` and `width:100%` -- measured at 1280x800 against the
 * authoritative sha as display block / cursor auto / width 195 inside a 219 rail, and the same rule
 * turned it into flex / pointer / 219. A traveller reading the rail is not clicking a disclosure
 * control, so the rail's heading must stay a label.
 *
 * The assertions read rendered shape (computed style + painted box), and they carry their own
 * positive control: the rail and its heading must exist before any shape is judged.
 */
import { expect, test } from "@playwright/test";

test("RAIL HEADING stays a label, not the drawer's toggle control", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/", { waitUntil: "networkidle", timeout: 90000 });
  for (const re of [/sealed demo/i, /使用封存的演示行程/]) {
    const c = page.getByText(re).first();
    if (await c.count()) { await c.click().catch(() => {}); await page.waitForTimeout(4000); break; }
  }

  const shape = await page.evaluate(() => {
    const rail = document.querySelector("nav.v8-nav");
    const head = rail && rail.querySelector(".v8-nav-group");
    if (!head || !rail) return null;
    const cs = getComputedStyle(head as HTMLElement);
    return {
      tag: head.tagName.toLowerCase(),
      display: cs.display,
      cursor: cs.cursor,
      width: Math.round((head as HTMLElement).getBoundingClientRect().width),
      railWidth: Math.round(rail.getBoundingClientRect().width),
      headings: Array.from(rail.querySelectorAll(".v8-nav-group")).length,
    };
  });

  expect(shape, "the rail and its group headings have to be on screen before any shape is judged").not.toBeNull();
  const g = shape as NonNullable<typeof shape>;
  console.log("RAIL_HEADING_SHAPE " + JSON.stringify(g));
  expect(g.headings, "the rail heads the same four groups the drawer does").toBe(4);
  expect(g.tag, "the rail heading is still a span, not the drawer's button").toBe("span");
  expect(g.display, "the rail heading may not inherit the drawer's flex toggle row").toBe("block");
  expect(g.cursor, "a heading the traveller cannot click must not advertise itself as clickable").toBe("auto");
  // Strictly less, not less-or-equal: the leaked shape measured exactly the rail's width (219 in a
  // 219 rail), so `<=` would have passed the defect it is meant to catch.
  expect(g.width, "the heading must stay its own width inside the rail, not stretch to fill it")
    .toBeLessThan(g.railWidth);
});
