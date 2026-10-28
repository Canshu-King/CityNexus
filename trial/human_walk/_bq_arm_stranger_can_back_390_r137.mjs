import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// The follow-up question bp136 left open.  A reopened traveller was shown an honest line -- 「这台设备上还留着
// 「北京」这趟行程，这次打开没有登录到它，所以读不到进度。」 -- with no way back, and the receipt proved why:
// the bearer and session-id live in sessionStorage (gone on reopen) while only the journey pointer survives
// in localStorage.  Before anyone decides that #332 needs persistent signing, one thing has to be measured:
// can a NEW identity, minted by the same product on the same device, still read that OLD journey?
//
//   yes -> "come back" is reachable today; the missing piece is only an on-screen door, not an auth change;
//   no  -> a button would lie, and #332 really needs the signing decision.
//
// Everything below is a real press in real Chrome at 390x844 on the isolated canary stack (vite :14464 /
// backend :60364, E:/_cmdr_tip_113 at dea0328e0b, zero dirty, nothing carried forward).  No seeded
// storage, no direct API call, no DOM injection.  Only key names and uuid shapes are printed -- never a
// token value; the old journey id is read out of the app's own localStorage pointer.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/bq137-stranger-can-back-390.txt`;
const PROFILE = "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bp136b";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

const box = await chromium.launchPersistentContext(PROFILE, {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
note(`PROFILE_USED ${PROFILE.split("/").pop()} t=${elapsed()}`);
const page = box.pages()[0] ?? await box.newPage();
box.on("response", async (resp) => {
  const url = resp.url(); const method = resp.request().method();
  if (!url.includes("/api/v1/")) return;
  if (method !== "POST" && resp.status() < 400) return;
  if (!/journeys|travelers|goal-tasks/.test(url)) return;
  note(`HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`);
});
box.on("pageerror", (e) => note("PAGEERROR " + String(e).replace(/\s+/g, " ").slice(0, 160)));

await page.goto("http://127.0.0.1:14464/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(8000);
const pointer = await page.evaluate(() => {
  const raw = window.localStorage.getItem("citynexus.revolution.firstlook.journey") || "";
  const found = raw.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
  return { keys: Object.keys(JSON.parse(raw || "{}")), id: found ? found[0] : "" };
}).catch((e) => ({ keys: [], id: "", err: String(e).slice(0, 80) }));
note(`A_LOCAL_POINTER keys=${JSON.stringify(pointer.keys)} old_id_shape=${pointer.id ? "uuid" : "none"}`);
note(`A_SESSION_NOW ${JSON.stringify(await page.evaluate(() => { const o = []; for (let i = 0; i < window.sessionStorage.length; i += 1) o.push(window.sessionStorage.key(i)); return o; }))}`);
if (!pointer.id) { note("ABORT no old journey id in the app's own pointer"); await box.close(); process.exit(3); }

// Mint a fresh identity the only way a traveller can: press the door the screen offers.
await page.getByRole("button", { name: /开始探索/ }).first().click().catch(() => note("EXPLORE_MISS"));
await page.waitForTimeout(2500);
const box2 = page.getByRole("textbox", { name: /想怎么玩/ }).first();
if (await box2.count()) {
  await box2.fill("2026 年 12 月 5 日到 6 日在上海玩两天，一个人");
  await page.waitForTimeout(500);
  await page.getByRole("button", { name: /继续规划/ }).first().click().catch(() => note("CONTINUE_MISS"));
  await page.waitForTimeout(3500);
}
const newId = lines.filter((l) => l.includes("POST 201 /api/v1/journeys")).map((l) => (l.match(UUID) || [""])[0]).pop() || "";
note(`B_NEW_JOURNEY new_id_shape=${newId ? "uuid" : "not_seen"} t=${elapsed()}`);
await page.screenshot({ path: `${DIR}/390-bq137-fresh-identity.png` }).catch(() => {});

// The measurement: same browser, same fresh traveller, the OLD journey's own address.
await page.goto("http://127.0.0.1:14464/journeys/" + pointer.id, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(7000);
const seen = await page.evaluate(() => {
  const body = (document.body.innerText || "").replace(/\s+/g, " ");
  return { head: body.slice(0, 200), refuses: /无权|没有登录|读不到|找不到|不可访问|不属于/.test(body),
    showsShanghai: body.includes("上海"), showsBeijing: body.includes("北京"),
    cards: Array.from(document.querySelectorAll("article")).length };
});
note(`C_OLD_ADDRESS ${JSON.stringify(seen)} t=${elapsed()}`);
await page.screenshot({ path: `${DIR}/390-bq137-old-journey-address.png` }).catch(() => {});
let verdict = "UNKNOWN";
if (seen.refuses) verdict = "STRANGER_REFUSED_needs_persistent_identity";
else if (seen.showsBeijing || seen.cards > 0) verdict = "STRANGER_CAN_READ_old_journey";
note(`VERDICT ${verdict} old_id_shape=${pointer.id ? "uuid" : "none"} t=${elapsed()}`);
note("DONE t=" + elapsed());
await box.close();
