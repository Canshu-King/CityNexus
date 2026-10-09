import { createRequire } from "module";
import { execFileSync } from "child_process";
import { readFileSync, writeFileSync, mkdirSync } from "fs";
const require = createRequire("D:/moodle/CityNexus/frontend/package.json");
const { chromium } = require("@playwright/test");

const REPO = "D:/moodle/CityNexus";
const REL = "frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx";
const TIP = "7f08160743b3b46e600c2c05e6863eaabd722f54";
const JOURNEY = "d13611bd-8c60-4c76-b1ef-200e2e2aff23";
const BASE = "http://localhost:5199";
const OUT = "D:/moodle/_liangchigong_0553r2_screen";
mkdirSync(OUT, { recursive: true });

const sha = (p) => execFileSync("git", ["-C", REPO, "hash-object", p], { encoding: "utf8" }).trim();
const after = readFileSync(`${REPO}/${REL}`, "utf8");
const before = execFileSync("git", ["-C", REPO, "show", `${TIP}:${REL}`], { encoding: "utf8", maxBuffer: 1 << 24 });
if (after === before) throw new Error("ABORT_SAME_SOURCE: working copy equals tip");
const afterSha = sha(`${REPO}/${REL}`);

const b = await chromium.launch();
const rows = [];
const emit = (o) => process.stdout.write(JSON.stringify(o) + "\n");
try {
  for (const [variant, src] of [["before", before], ["after", after]]) {
    writeFileSync(`${REPO}/${REL}`, src);
    await new Promise((r) => setTimeout(r, 5000));
    const sourceSha = sha(`${REPO}/${REL}`);
    for (const [localeKey, deviceZone] of [["en", "America/New_York"], ["zh-CN", "America/New_York"], ["en", "Asia/Shanghai"]]) {
      const ctx = await b.newContext({ locale: localeKey === "en" ? "en-US" : "zh-CN", timezoneId: deviceZone, viewport: { width: 1120, height: 340 } });
      const page = await ctx.newPage();
      const errs = [];
      page.on("pageerror", (e) => errs.push(String(e.message).slice(0, 120)));
      await page.addInitScript(([id, loc]) => {
        localStorage.setItem("citynexus.v8.journey_id", id);
        localStorage.setItem("citynexus.locale", loc);
      }, [JOURNEY, localeKey]);
      await page.goto(`${BASE}/v8/authoritative`, { waitUntil: "networkidle", timeout: 60000 });
      const panel = page.getByTestId("v12-authoritative-panel");
      await panel.waitFor({ state: "visible", timeout: 30000 });
      const nextCell = page.locator(".v12-state-card.next small").first();
      const nextText = (await nextCell.count()) ? (await nextCell.innerText()).replace(/\s+/g, " ").trim() : "NO_CELL";
      const kicker = (await page.locator(".v12-state-card.next .v12-state-kicker").first().innerText()).replace(/\s+/g, " ").trim();
      const title = (await page.locator(".v12-state-card.next strong").first().innerText()).replace(/\s+/g, " ").trim();
      const shot = `0553r2v2_${variant}_${localeKey}_${deviceZone.replace(/[^A-Za-z]/g, "")}.png`;
      await panel.screenshot({ path: `${OUT}/${shot}` });
      const row = { variant, sourceSha, localeKey, deviceZone, kicker, nextTitle: title, nextCellText: nextText, shot, errs: errs.slice(0, 2) };
      rows.push(row);
      emit(row);
      await ctx.close();
    }
  }
} finally {
  writeFileSync(`${REPO}/${REL}`, after);
  await b.close();
}

const restored = sha(`${REPO}/${REL}`);
const beforeTexts = new Set(rows.filter((r) => r.variant === "before").map((r) => `${r.localeKey}|${r.nextCellText}`));
const afterTexts = new Set(rows.filter((r) => r.variant === "after").map((r) => `${r.localeKey}|${r.nextCellText}`));
emit({
  verdict: "restored_ok",
  restoredSha: restored,
  expectedAfterSha: afterSha,
  restore_matches: restored === afterSha,
  before_readings: [...beforeTexts],
  after_readings: [...afterTexts],
  screens_differ: beforeTexts.size > 0 && afterTexts.size > 0 && [...afterTexts].some((t) => !beforeTexts.has(t)),
});
