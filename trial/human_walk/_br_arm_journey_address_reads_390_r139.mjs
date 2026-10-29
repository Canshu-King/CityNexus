import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// Fixing two instrument faults I recorded in the session-recovery note, then re-measuring with them gone.
//
//   fault 1 -- both earlier arms looked for the journey id inside the URL of `POST 201 /api/v1/journeys`,
//             and that URL carries no id, so the receipts printed not_seen_in_receipt.  The right reader
//             is the product's own local pointer, which is what this arm uses for BOTH ids.
//   fault 2 -- the verdict predicate only knew "a refusal word appeared", "the old city name is on
//             screen" and "there is an article".  The real fourth shape -- bounced to the create wizard
//             -- fell through to UNKNOWN.  This arm covers three shapes and proves the middle one fires:
//
//     positive control  visit the journey THIS identity just created  -> expect READ_CONTENT
//     negative shape    visit the older journey owned by another id    -> expect REDIRECTED_TO_CREATE
//     refusal shape     kept in the predicate for when the server says so out loud
//
// Without the positive control a predicate that always answered "redirected" would look identical, so
// the arm is only worth running because it can also read the other side.
//
// Real Chrome at 390x844 on the isolated canary stack (vite :14464 / backend :60364, E:/_cmdr_tip_113 at
// dea0328e0b, zero dirty, nothing carried forward).  No seeded storage, no direct API call, no DOM
// injection; only key names, id shapes and on-screen sentences are printed -- never a credential value.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/br139-journey-address-reads-390.txt`;
// The collision ruler bit this arm the moment it was added: it reused _chrome_gozero_bp136b, which
// belongs to r137 (PROFILE_CLASH ... COLLISIONS 1).  The profile is now its own, which also means this
// arm can no longer be re-run for the same reading -- a fresh profile holds no older journey to
// compare against.  Its receipt is kept as the run that found the bare /journeys/:id route bounces
// EVERYONE to the create wizard, own journeys included; the discriminating reading is r140.
const PROFILE = "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_br139";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const ctx = await chromium.launchPersistentContext(PROFILE, {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
note(`PROFILE_USED ${PROFILE.split("/").pop()} t=${elapsed()}`);
const page = ctx.pages()[0] ?? await ctx.newPage();
ctx.on("pageerror", (e) => note("PAGEERROR " + String(e).replace(/\s+/g, " ").slice(0, 160)));
ctx.on("response", (resp) => {
  const url = resp.url(); const method = resp.request().method();
  if (!url.includes("/api/v1/travelers") && !url.includes("/api/v1/journeys")) return;
  if (method !== "POST" && resp.status() < 400) return;
  note(`HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`);
});

// The one reader that works: the app writes its own pointer, so ask it.
const pointerId = () => page.evaluate(() => {
  const raw = window.localStorage.getItem("citynexus.revolution.firstlook.journey") || "";
  try {
    const box = JSON.parse(raw || "{}");
    const id = typeof box.id === "string" ? box.id : "";
    return { id, owner: typeof box.ownerTravelerId === "string" ? box.ownerTravelerId : "",
      city: typeof box.cityName === "string" ? box.cityName : "", status: String(box.status || "") };
  } catch { return { id: "", owner: "", city: "", status: "" }; }
});

await page.goto("http://127.0.0.1:14464/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(8000);
const oldPointer = await pointerId();
note(`A_OLD_POINTER id_shape=${oldPointer.id ? "uuid" : "none"} owner_shape=${oldPointer.owner ? "uuid" : "none"} city=${JSON.stringify(oldPointer.city)} status=${JSON.stringify(oldPointer.status)} t=${elapsed()}`);
if (!oldPointer.id) { note("ABORT the device pointer holds no journey to compare against"); await ctx.close(); process.exit(3); }

// Create a journey the way a traveller does, so there is something this identity DOES own.
await page.getByRole("textbox", { name: /想怎么玩/ }).first()
  .fill("2026 年 12 月 8 日到 9 日在广州玩两天，两个人，每段步行不超过 1 公里").catch(() => note("A_FILL_MISS"));
await page.waitForTimeout(600);
await page.getByRole("button", { name: /继续规划/ }).first().click().catch(() => note("A_CONTINUE_MISS"));
await page.waitForTimeout(4000);
const newPointer = await pointerId();
const freshId = newPointer.id && newPointer.id !== oldPointer.id ? newPointer.id : "";
note(`B_NEW_POINTER id_shape=${newPointer.id ? "uuid" : "none"} city=${JSON.stringify(newPointer.city)} same_as_old=${newPointer.id === oldPointer.id} t=${elapsed()}`);
if (!freshId) note("B_NO_FRESH_JOURNEY the create step did not produce a different pointer");

const readAt = async (label, id) => {
  await page.goto("http://127.0.0.1:14464/journeys/" + id, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(6500);
  const seen = await page.evaluate(() => {
    const body = (document.body.innerText || "").replace(/\s+/g, " ");
    return {
      head: body.slice(0, 170),
      bouncedToCreate: /新建行程|三步完成|目的地与时间/.test(body),
      refuses: /无权|没有登录|读不到|找不到|不可访问|不属于|无法打开/.test(body),
      hasJourneyContent: /行程|出发|日程|活动|地图|计划/.test(body) && !/新建行程 三步完成/.test(body),
      articles: Array.from(document.querySelectorAll("article")).length,
      buttons: Array.from(document.querySelectorAll("button")).map((b) => (b.innerText || "").replace(/\s+/g, " ").trim()).filter((t) => t).slice(0, 8),
    };
  });
  const shape = seen.bouncedToCreate ? "REDIRECTED_TO_CREATE"
    : seen.refuses ? "REFUSED_IN_WORDS"
      : seen.hasJourneyContent || seen.articles > 0 ? "READ_CONTENT" : "UNKNOWN";
  note(`${label} ${JSON.stringify(seen)} shape=${shape} t=${elapsed()}`);
  await page.screenshot({ path: `${DIR}/390-br139-${label.toLowerCase()}.png` }).catch(() => {});
  return shape;
};

let verdict = "INCONCLUSIVE";
if (freshId) {
  const mine = await readAt("C_OWN_NEW_JOURNEY", freshId);
  const theirs = await readAt("D_OTHERS_OLD_JOURNEY", oldPointer.id);
  if (mine === "READ_CONTENT" && theirs === "REDIRECTED_TO_CREATE") {
    verdict = "DISCRIMINATED_positive_read_and_negative_bounce";
  } else if (mine === "READ_CONTENT" && theirs === "READ_CONTENT") {
    verdict = "A_NEW_IDENTITY_CAN_READ_THE_OLD_JOURNEY";
  } else if (mine !== "READ_CONTENT") {
    verdict = "CONTROL_FAILED_positive_side_did_not_read_" + mine;
  } else verdict = `MIXED mine=${mine} theirs=${theirs}`;
  note(`PAIR own=${mine} other=${theirs}`);
}
note(`VERDICT ${verdict} t=${elapsed()}`);
note("DONE t=" + elapsed());
await ctx.close();
