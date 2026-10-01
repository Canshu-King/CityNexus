/* ORD-0507 item 1 -- the access screen's activity rows must not put a server action name in front of a
   traveller, and the name must still be reachable inside a fold.

   Everything here is read off rendered text (`innerText`), not off a `data-*` attribute, because the
   attribute is what a screen can lie about and the sentence is what a person reads.

   Three arms, and what each one would do if the guard were removed:
   * no-machine-word: a visible sentence in either shipped locale must not contain a dotted or
     snake_case token. Delete the vocabulary lookup and the row becomes `journey.updated ...`, which is
     exactly the mutant this spec was written against -- measured on a bundle built with the lookup
     bypassed, both locales read `machine_word=True`.
   * fold-carries-it: the technical fold must exist (count >= 1) and its own text must name the server's
     word, so removing the token from the sentence does not remove the fact.
   * paired-in-both-arms: every key this screen asks for exists in both the `en` and the `zh-CN` table,
     so a future third locale missing a line fails here rather than rendering a key.
*/

import { expect, test } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

const API = (path: string) => `/api/v1${path}`;
const MACHINE = /\b[a-z]+[._][a-z0-9_.]+\b/;
const NODE = "ord0507-1";

const node = (cell: string, message: string) => `${NODE} ${cell}: ${message}`;

async function seedJourneyWithAnUnmappedAction(request: any): Promise<string> {
  const start = new Date(Date.now() + 3 * 864e5).toISOString();
  const end = new Date(Date.now() + 5 * 864e5).toISOString();
  const traveller = await request.post(API("/travelers"), {
    data: { display_name: "ORD-0507 探针", locale: "zh-CN", timezone: "Asia/Shanghai" },
  });
  expect(traveller.ok(), node("setup-traveller", `the traveller door answered ${traveller.status()}`)).toBe(true);
  const journey = await request.post(API("/journeys"), {
    data: {
      traveler_id: (await traveller.json()).id,
      title: "ORD-0507 活动流",
      city_code: "CN-XIAMEN",
      timezone: "Asia/Shanghai",
      start_at: start,
      end_at: end,
      budget: { amount_minor: 120000, currency: "CNY" },
      planning_mode: "balanced",
    },
  });
  expect(journey.ok(), node("setup-journey", `the journey door answered ${journey.status()}`)).toBe(true);
  const journeyId = (await journey.json()).id as string;
  // `journey.updated` is an action this screen's vocabulary has no entry for -- that is the whole
  // point of the arm -- and it is produced here through the product's own write door.
  const rename = await request.patch(API(`/journeys/${journeyId}`), {
    data: { title: "ORD-0507 活动流（改名）" },
  });
  expect(rename.ok(), node("setup-action", `the rename door answered ${rename.status()}`)).toBe(true);
  const feed = await request.get(API(`/journeys/${journeyId}/agent-feed?limit=50`));
  expect(feed.ok(), node("setup-feed", `the feed door answered ${feed.status()}`)).toBe(true);
  const events = ((await feed.json()).events || []) as { event_type: string }[];
  expect(
    events.some((e) => !e.event_type.startsWith("journey.created")),
    node("setup-feed", "the journey needs at least one action the screen cannot name"),
  ).toBe(true);
  return journeyId;
}

for (const locale of ["zh-CN", "en"]) {
  test(`the access activity row speaks one language at a time [${locale}]`, async ({ page, request }) => {
    test.setTimeout(180_000);
    const journeyId = await seedJourneyWithAnUnmappedAction(request);
    await page.addInitScript(
      ([id, value]) => {
        localStorage.clear();
        localStorage.setItem("citynexus.v8.journey_id", id);
        localStorage.setItem("citynexus.locale", value);
      },
      [journeyId, locale],
    );
    await page.goto("/v8/access");

    const picker = page.getByTestId("access-journey-picker");
    await expect(
      picker,
      node("picker", "this screen asks for its own pick; a reading taken without it measures an empty stage"),
    ).toBeVisible({ timeout: 30_000 });
    await picker.selectOption(journeyId);

    const rows = page.locator(".cn-access-activity-row");
    await expect(
      rows.first(),
      node("rows", "no activity row was painted, so the two assertions below would pass on an empty screen"),
    ).toBeVisible({ timeout: 30_000 });
    await expect(rows.count()).resolves.toBeGreaterThan(0);

    let folded = 0;
    for (const row of await rows.all()) {
      const what = row.locator(".cn-access-what");
      const sentence = (await what.innerText()).replace(/\s+/g, " ").trim();
      expect(
        MACHINE.test(sentence),
        node("no-machine-word", `a server action name reached the sentence: "${sentence.slice(0, 120)}"`),
      ).toBe(false);

      const fold = what.locator("details[data-testid='access-activity-technical']");
      if ((await fold.count()) === 0) continue;
      folded += 1;
      await fold.locator("summary").click();
      const raw = (await what.locator('[data-testid="access-activity-raw"]').innerText())
        .replace(/\s+/g, " ")
        .trim();
      expect(
        MACHINE.test(raw),
        node("fold-carries-it", `the fold exists but no longer carries the server's own word: "${raw}"`),
      ).toBe(true);
    }
    expect(folded, node("fold-carries-it", "the unmapped row had no technical fold at all")).toBeGreaterThan(0);
  });
}

test("every access-screen key the panel asks for has a line in both shipped tables", async () => {
  /* Playwright starts in the frontend project, and this arm reads source files, so the working
     directory is the one honest root to use.  A wrong guess throws rather than passing quietly. */
  const root = process.cwd();
  if (!fs.existsSync(path.join(root, "src/features/access/accessCopy.ts"))) {
    throw new Error(`ord0507-1 pairing: "${root}" is not the frontend project root`);
  }
  const copy = fs.readFileSync(path.join(root, "src/features/access/accessCopy.ts"), "utf8");
  const panel = fs.readFileSync(path.join(root, "src/features/access/AccessPanel.tsx"), "utf8");
  const asked = new Set<string>();
  for (const m of panel.matchAll(/say\("(access\.[A-Za-z]+)"/g)) asked.add(m[1]);
  for (const m of panel.matchAll(/t\("(access\.[A-Za-z]+)"/g)) asked.add(m[1]);
  expect(asked.size, node("paired-in-both-arms", "the panel asks for no access.* key -- a false green")).toBeGreaterThan(5);
  const tables = { en: "", zh: "" };
  {
    const en = copy.indexOf('  en: {');
    const zh = copy.indexOf('  "zh-CN": {');
    const end = copy.indexOf("} as const;", zh);
    tables.en = copy.slice(en, zh);
    tables.zh = copy.slice(zh, end);
  }
  const missing = [...asked].filter(
    (key) => !tables.en.includes(`"${key}"`) || !tables.zh.includes(`"${key}"`),
  );
  expect(missing, node("paired-in-both-arms", `keys without a line in both tables: ${missing.join(", ")}`)).toEqual([]);
});
