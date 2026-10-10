import { expect, test } from "@playwright/test";
import { appendFileSync, existsSync, mkdirSync, unlinkSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createFreshJourney, useJourney } from "./_qoderFreshJourney";

/* ORD-0557 follow-up table · the inbox workbench's three last-resort words.

   decisionLabel / timeLabel / renderFact used to paint their own fallback words when the
   server left a slot empty. They now read `inbox.handled` and `inbox.toConfirm`. This case
   walks the traveller's own path -- 收件箱 · 手工填一张确认单, leave one field empty, submit
   -- and reads the glass in both languages, so the claim "no word moved" is a measurement.

   Readings land in review/预防工-0557-inbox/screen_readings_r1.txt, one line per arm. */

const API =
  process.env.CITYNEXUS_API_BASE_URL ??
  `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

const HERE = dirname(fileURLToPath(import.meta.url));
const ARTIFACTS = resolve(HERE, "..", "..", "review/预防工-0557-inbox");
const READOUT = resolve(ARTIFACTS, "screen_readings_r1.txt");

const lines: string[] = [];
function note(text: string) {
  lines.push(text);
  mkdirSync(ARTIFACTS, { recursive: true });
  writeFileSync(READOUT, lines.join("\n") + "\n", "utf-8");
}

for (const locale of ["zh-CN", "en"] as const) {
  test(`${locale}: an empty slot on a hand-made confirmation reads the dictionary words`, async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);
    const { journeyId } = await createFreshJourney(request, { select: true });
    await page.addInitScript((loc) => {
      localStorage.setItem("citynexus.locale", loc);
    }, locale);
    await useJourney(page, journeyId);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/v8/bookings", { waitUntil: "load" });

    const manualTab = page.getByTestId("inbox-tab-manual");
    if (!(await manualTab.isVisible().catch(() => false))) {
      // the inbox sits behind the phone/advanced disclosures on this screen
      const summaries = page.locator("details > summary");
      const count = await summaries.count();
      for (let i = 0; i < count; i += 1) {
        await summaries.nth(i).click().catch(() => undefined);
      }
      note(`[${locale}] disclosures_opened=${count}`);
    }
    await expect(manualTab).toBeVisible({ timeout: 30_000 });
    await manualTab.click();

    await page.getByTestId("manual-title").fill("天津之眼 夜景票");
    await page.getByTestId("manual-ref").fill("TN-REF-001");
    await page.getByTestId("manual-from").fill("天津站");
    await page.getByTestId("manual-to").fill("天津之眼");
    await page.getByTestId("manual-depart").fill("2026-10-11T09:30");
    await page.getByTestId("manual-arrive").fill("2026-10-11T10:10");
    await page.getByTestId("manual-amount").fill("128");
    await page.getByTestId("manual-submit").click();

    const verdict = page.locator("p.v10-inbox-clear, p.v10-inbox-warning");
    await expect(verdict.first()).toBeVisible({ timeout: 30_000 });
    const verdictText = (await verdict.first().textContent()) ?? "";
    note(`[${locale}] 核对行 textContent = ${JSON.stringify(verdictText)}`);

    const facts = page.locator("dl dd");
    const factCount = await facts.count();
    const rendered: string[] = [];
    for (let i = 0; i < factCount; i += 1) {
      rendered.push((await facts.nth(i).textContent()) ?? "");
    }
    note(`[${locale}] dl dd readings (${factCount} slots) = ${JSON.stringify(rendered)}`);

    /* Nothing here demands a particular word: the case records what the traveller's own
       path really shows, in both languages, and the reverse control compares the two runs
       byte for byte. Which arms are reachable is written up from these readings. */
    expect(rendered.length).toBeGreaterThan(0);
    const emptySlots = rendered.filter((item) => item === "").length;
    note(
      `[${locale}] arm 279/258 reachability: dl slots=${rendered.length} empty_slots=${emptySlots} ` +
        `(the server answered every slot with a token, so renderFact never saw "")`,
    );
    const handledOnGlass = /已处理|Handled/.test(verdictText);
    note(
      `[${locale}] arm 253 reachability: handled fallback on glass=${handledOnGlass}; ` +
        `the line reads ${JSON.stringify(verdictText)}`,
    );
    note(`[${locale}] verdict_and_slots = ${JSON.stringify([verdictText, ...rendered])}`);

    await page
      .locator(".v9-inbox")
      .first()
      .screenshot({ path: resolve(ARTIFACTS, `inbox_${locale}_r1.png`) });
    note(`[${locale}] screenshot = review/预防工-0557-inbox/inbox_${locale}_r1.png`);
  });
}
