import { chromium } from "playwright";
import fs from "node:fs";

const BASE = "http://localhost:4581/legacy";
const OUT = process.env.OUT || "review/pinggong-0557/screen_read_r1.txt";
const TAG = process.env.TAG || "after";

const NEEDLES = [
  ["main.cityNexusRequestFailed", "CityNexus request failed"],
  ["main.cityNexusRequestRefusedHttp", "CityNexus request refused (HTTP"],
  ["main.persistedOperationUpdate", "Persisted operation update"],
  ["main.generalRecovery", "general recovery"],
  ["main.activateAStandingMissionOnce", "Activate a standing mission once; subsequent city signals"],
  ["main.noDominantFailureMode", "No dominant failure mode"],
  ["main.notEvaluated", "not evaluated"],
  ["main.validatedActivity", "validated Activity"],
  ["main.noActionableTarget", "no actionable target"],
  ["main.outcomeEvidence", "outcome evidence"],
  ["main.explicitWins", "explicit wins"],
  ["main.notReported", "not reported"],
  ["main.noUpcomingActivity", "no upcoming activity"],
  ["main.noActiveC4", "No active C4"],
  ["main.notAvailable", "not available"],
  ["main.unnamedCommitmentServerGaveNoName", "未命名承诺 · 服务器没给名字"],
  ["main.verifiedFeasible", "verified feasible"],
  ["main.notFeasible", "not feasible"],
  ["main.notPreserved", "not preserved"],
  ["main.verifiedEvidenceAttached", "verified evidence attached"],
  ["main.evidenceUnavailable", "evidence unavailable"],
];

async function readLocale(browser, locale) {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto("http://localhost:4581/", { waitUntil: "domcontentloaded" });
  await page.evaluate((l) => localStorage.setItem("citynexus.locale", l), locale);
  await page.goto(BASE, { waitUntil: "load" });
  await page.waitForTimeout(3500);
  const text = await page.evaluate(() => document.body.innerText);
  const file = `review/pinggong-0557/screen_${TAG}_${locale}.png`;
  await page.screenshot({ path: file, fullPage: true });
  await ctx.close();
  return { text, file };
}

(async () => {
  const browser = await chromium.launch();
  const en = await readLocale(browser, "en");
  const zh = await readLocale(browser, "zh-CN");
  await browser.close();

  const lines = [`# screen read TAG=${TAG} url=${BASE}`];
  let hitEn = 0, hitZh = 0;
  for (const [key, needle] of NEEDLES) {
    const a = en.text.includes(needle);
    const b = zh.text.includes(needle);
    if (a) hitEn++;
    if (b) hitZh++;
    lines.push(`key ${key} | needle ${JSON.stringify(needle)} | en=${a} zh=${b}`);
  }
  lines.push(`HITS en=${hitEn}/${NEEDLES.length} zh=${hitZh}/${NEEDLES.length}`);
  lines.push(`png_en=${en.file} bytes=${fs.statSync(en.file).size}`);
  lines.push(`png_zh=${zh.file} bytes=${fs.statSync(zh.file).size}`);
  lines.push(`body_chars en=${en.text.length} zh=${zh.text.length}`);
  fs.writeFileSync(OUT, lines.join("\n") + "\n");
  console.log(lines.slice(-4).join("\n"));
})();
