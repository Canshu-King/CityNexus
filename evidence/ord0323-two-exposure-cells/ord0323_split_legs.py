"""Make ORD-0323's eight legs independent arms, and fix two instrument faults found by the probe run.

Measured in `e2e_0323fix1907`: N1/N2/N3 passed, N4 timed out with `running_leg = T09` after three legs had
landed. Two causes, both mine:
  1. one test walking eight legs spends one timeout on eight chances -- a stuck leg hides which, and burns
     the whole budget;
  2. the paste leg filled `page.locator("textarea").first()`, and this page holds a second textarea inside
     the closed structured-JSON aside, which is not editable -> the action waits.
Plus the leg rows never carried `status_in_slot`, so the receipt could not read its own claim back.
"""
from __future__ import annotations

import pathlib
import re

P = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\e2e\qoder-ord0323-two-exposure-cells.spec.ts")
s = P.read_text(encoding="utf-8")

start = s.index('test("N4_eight_catch_sites_no_longer_carry')
NEW = '''/* One test per leg: a shared test would spend one timeout across eight chances and hide which leg stuck
 * (measured -- the loop版 died at `running_leg = T09` with three legs done). Each leg gets its own route
 * plan, its own 120 s budget, and its own evidence file named by D's cell id. */
for (const leg of LEGS) {
  test(`N4_${leg.cell}_a_refused_${leg.method}_leaves_no_reply_words_and_keeps_its_own_reading — ${leg.cell}：自己那句原话不在屏上，自己那次读数还在屏上`, async ({
    page,
  }) => {
    test.setTimeout(120_000);
    const arm = leg.cell;
    const id = await journeyId(page);
    await page.route("**/api/v1/journeys/**", async (r: Route) => {
      const path = new URL(r.request().url()).pathname;
      const method = r.request().method();
      const mine =
        leg.match === "PATCH_INBOX"
          ? method === "PATCH" && /\\/inbox\\/[A-Za-z0-9-]+$/.test(path)
          : method === leg.method && path.endsWith(leg.match);
      if (mine) {
        await r.fulfill({
          status: leg.status,
          contentType: "application/json",
          body: jsonBody({error: {message: NEEDLES[leg.cell]}, detail: NEEDLES[leg.cell]}),
        });
        return;
      }
      if (path.endsWith("/inbox") && method === "GET") {
        await r.fulfill({status: 200, contentType: "application/json", body: jsonBody({drafts: [draftRow]})});
        return;
      }
      return r.fallback();
    });
    await boot(page, id);
    await page.goto("/v8/bookings", {waitUntil: "load"});
    await expect(
      page.getByTestId("v13-2-memory"),
      node(arm, `${leg.cell}: the wallet panel never rendered, so this leg has no surface to be judged on`),
    ).toBeVisible({timeout: 30_000});
    if (leg.trigger === "paste") {
      await page.getByTestId("inbox-tab-paste").click();
      /* This page holds a second textarea inside the closed structured-JSON aside; only the visible one is
         the paste box. */
      await page.locator("textarea").filter({visible: true}).first().fill("9月26日 天津西→北京南 G8901 二等座 07:30");
      await page.getByRole("button", {name: "提取文本草稿"}).click();
    } else if (leg.trigger !== "none") {
      await drive(page, leg.trigger);
    }
    const slot =
      leg.slot === "message"
        ? page.locator(".v10-inbox-message").first()
        : leg.slot === "queue"
          ? page.getByTestId("inbox-pending-error")
          : page.getByTestId("inbox-confirm-detail");
    await expect(
      slot,
      node(arm, `${leg.cell}: the leg was refused but its own slot shows nothing -- an empty screen is not an honest screen`),
    ).toBeVisible({timeout: 30_000});
    if (leg.slot === "fold") await slot.locator("summary").click();
    const text = clean(await slot.textContent());
    const dom = await domReading(page);
    const found = Object.entries(NEEDLES)
      .filter(([, n]) => dom.root.includes(n) || dom.body.includes(n))
      .map(([c]) => c);
    const foreign = LEGS.filter((o) => o.cell !== leg.cell).map((o) => String(o.status)).filter((x) => text.includes(x));
    readings[arm] = {
      cell: leg.cell,
      route: leg.match,
      method: leg.method,
      status_asked: leg.status,
      slot_text: text,
      status_in_slot: text.includes(String(leg.status)),
      needles_found: found,
      foreign_status_found: foreign,
      internal_token_on_screen: /inbox request rejected/i.test(text),
    };
    expect(found, node(arm, `${leg.cell}: a reply's own words are on the screen (${JSON.stringify(found)}); the slot reads "${text}"`)).toEqual([]);
    expect(text.includes(String(leg.status)),
      node(arm, `${leg.cell}: the slot no longer states the status this device measured for THIS request (${text})`)).toBe(true);
    expect(foreign,
      node(arm, `${leg.cell}: the slot shows another leg's status ${JSON.stringify(foreign)} instead of its own (${text})`)).toEqual([]);
    if (leg.slot !== "message") {
      expect(text.includes("application/json"),
        node(arm, `${leg.cell}: the machine slot lost the content type this device measured (${text})`)).toBe(true);
    }
    expect(/inbox request rejected/i.test(text),
      node(arm, `${leg.cell}: the carrier's internal token reached the traveller (${text})`)).toBe(false);
  });
}
'''
s = s[:start] + NEW

# the old `drive()` no longer handles the paste leg, and the hex PNG helper stays
s = s.replace('''  if (trigger === "paste" || trigger === "vision") {
    await page.getByTestId("inbox-tab-paste").click();
    if (trigger === "paste") {
      await page.locator("textarea").first().fill("9月26日 天津西→北京南 G8901 二等座 07:30");
      await page.getByRole("button", {name: "提取文本草稿"}).click();
      return;
    }''', '''  if (trigger === "vision") {
    await page.getByTestId("inbox-tab-paste").click();''')
P.write_text(s, encoding="utf-8", newline="\n")
print("legs split into independent arms;", len(s.splitlines()), "lines")
print("arm keys:", re.findall(r"const arm = (\w+)", s)[:3], "| generated tests:", s.count("  test(`N4_"))
