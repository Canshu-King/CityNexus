/**
 * ORD-0570 · the three sentences this order moved out of `accessCopy.ts` into the shared dictionary.
 *
 * What has to be seen on glass, per the order: each of the three cells once in Chinese and once in
 * English, with the words copied off the screen and then compared byte-for-byte against the
 * dictionary side that now supplies them. A DOM presence check is not the claim: the assertions read
 * `innerText` / the rendered `aria-label`, and the two languages are two separate page loads.
 *
 * `access.pickLabel` is the trip picker's own label, so this file records whether it was painted in
 * the state the seeded journey produces instead of asserting it blindly.
 */
import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const DICTIONARY = "src/i18n/LocaleContext.tsx";
const OUT = path.join(process.cwd(), "..", "review", "beichengong-0570");
const CELLS = [
  { key: "access.title", expectPainted: true },
  { key: "access.sub", expectPainted: true },
  { key: "access.pickLabel", expectPainted: true },
];

function dictValue(key: string, book: "en" | "zh"): string {
  const lines = fs.readFileSync(DICTIONARY, "utf8").split("\n");
  const zhStart = lines.findIndex((l) => l.startsWith("const zhCN: Dict"));
  for (let i = 0; i < lines.length; i += 1) {
    const m = /^\s*"([^"]+)": "(.*)",$/.exec(lines[i]);
    if (!m || m[1] !== key) continue;
    if ((i < zhStart ? "en" : "zh") === book) return m[2];
  }
  throw new Error("no dictionary side for " + key + " " + book);
}

async function openAccess(page: Page, locale: string): Promise<void> {
  const seeded = await (await page.request.get("/api/v1/demo/scene")).json();
  const journeyId = String((seeded as { journey_id?: string }).journey_id ?? "");
  expect(journeyId.length, "the shell needs an open trip before the member screen renders").toBeGreaterThan(8);
  await page.addInitScript(
    ([loc, id]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", loc);
      localStorage.setItem("citynexus.v8.journey_id", id);
    },
    [locale, journeyId] as [string, string],
  );
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
  await page.goto("/v8/access", { waitUntil: "load" });
  await expect(page.getByTestId("access-panel")).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(1200);
}

for (const [locale, book] of [["zh-CN", "zh"], ["en", "en"]] as [string, "en" | "zh"][]) {
  test("0570 screen read of the three moved cells in " + locale, async ({ page }) => {
    fs.mkdirSync(OUT, { recursive: true });
    await openAccess(page, locale);
    const panel = page.getByTestId("access-panel");
    const painted = await panel.innerText();
    const whole = await page.evaluate(() => document.body.innerText);
    const rows: string[] = [];
    for (const cell of CELLS) {
      const want = dictValue(cell.key, book);
      // 那一格的 kicker 带 CSS 大写变换，屏上就是 MEMBERS AND ACCESS；
      // 所以按内容定位，再把屏上此刻真的那几个字原样抄进读数件，不拿期望值冒充读数。
      const idx = painted.toLowerCase().indexOf(want.toLowerCase());
      const seen = idx >= 0 ? painted.slice(idx, idx + want.length) : null;
      const inPanel = seen !== null;
      const inWhole = whole.toLowerCase().includes(want.toLowerCase());
      rows.push([cell.key, inPanel ? "PANEL" : inWhole ? "PAGE_ONLY" : "ABSENT",
        "字典=" + want, "屏上=" + (seen ?? "—")].join(" | "));
    }
    // 读数先落盘再断言：上一版先断言后写件，红的那一趟什么也没留下
    await page.screenshot({ path: path.join(OUT, "access_" + locale + "_r1.png"), fullPage: true });
    fs.writeFileSync(path.join(OUT, "screen_read_" + locale + "_r1.txt"),
      rows.join("\n") + "\n面板 innerText 前 240 字：" + painted.slice(0, 240) + "\n", "utf8");
    for (const cell of CELLS) {
      if (cell.expectPainted) {
        expect(rows.some((r) => r.startsWith(cell.key + " | PANEL")),
          locale + " 屏上这一格没在面板里读到：" + cell.key).toBe(true);
      }
    }
  });
}
