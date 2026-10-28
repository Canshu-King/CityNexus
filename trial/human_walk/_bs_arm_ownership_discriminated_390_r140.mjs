import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// The discriminating version of r139.  r139 reported that visiting /journeys/<id> bounced to the create
// wizard -- for the older journey AND for the one the current identity had just made.  That reading is
// worth less than it looks: if the route bounces everyone, "the stranger was bounced" proves nothing
// about ownership.  This arm therefore creates BOTH journeys itself, in two separate browser sessions, so
// the same code path is walked against a journey this identity owns and a journey an earlier identity
// owned:
//
//   session 1 (identity X) -- create 广州, record its id, close the browser (close the tab: the bearer
//                              lives in sessionStorage, so it goes away exactly as it does for a
//                              traveller who reopens the site)
//   session 2 (identity Y) -- the app mints a new traveller; create 上海, record its id
//   read A -- visit /journeys/<Y's own 上海 id>   -> the positive control; must READ_CONTENT
//   read B -- visit /journeys/<X's 广州 id>       -> the ownership case under test
//
// If A reads and B does not, the difference is ownership and nothing else.  If A also bounces, the route
// itself is the finding and the ownership question stays open -- which is exactly what r139 hinted at.
// Real Chrome at 390x844, isolated canary stack (vite :14464 / backend :60364, E:/_cmdr_tip_113 at
// dea0328e0b, zero dirty, nothing carried forward).  No seeded storage, no direct API call, no DOM
// injection; ids are read out of the app's own localStorage pointer, and no credential value is printed.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/bs140-ownership-discriminated-390.txt`;
const PROFILE = "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bs140";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const pointerId = (page) => page.evaluate(() => {
  const raw = window.localStorage.getItem("citynexus.revolution.firstlook.journey") || "";
  try {
    const box = JSON.parse(raw || "{}");
    return { id: typeof box.id === "string" ? box.id : "",
      owner: typeof box.ownerTravelerId === "string" ? box.ownerTravelerId : "",
      city: typeof box.cityName === "string" ? box.cityName : "" };
  } catch { return { id: "", owner: "", city: "" }; }
});

async function session(label, sentence) {
  const box = await chromium.launchPersistentContext(PROFILE, {
    channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
  });
  const page = box.pages()[0] ?? await box.newPage();
  page.on("pageerror", (e) => note(`${label}_PAGEERROR ` + String(e).replace(/\s+/g, " ").slice(0, 150)));
  page.on("response", (resp) => {
    const url = resp.url(); const method = resp.request().method();
    if (!/\/api\/v1\/(travelers|journeys)/.test(url)) return;
    if (method !== "POST" && resp.status() < 400) return;
    note(`${label}_HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`);
  });
  await page.goto("http://127.0.0.1:14464/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(8000);
  const before = await pointerId(page);
  await page.getByRole("textbox", { name: /想怎么玩/ }).first().fill(sentence).catch(() => note(`${label}_FILL_MISS`));
  await page.waitForTimeout(600);
  await page.getByRole("button", { name: /继续规划/ }).first().click().catch(() => note(`${label}_CONTINUE_MISS`));
  await page.waitForTimeout(4200);
  const after = await pointerId(page);
  note(`${label}_POINTER before=${JSON.stringify({ city: before.city, same: before.id === after.id })} after_city=${JSON.stringify(after.city)} id_shape=${after.id ? "uuid" : "none"} owner_shape=${after.owner ? "uuid" : "none"} t=${elapsed()}`);
  await box.close();
  return after;
}

const first = await session("S1", "2026 年 12 月 8 日到 9 日在广州玩两天，两个人，每段步行不超过 1 公里");
await new Promise((done) => setTimeout(done, 2000));
const second = await session("S2", "2026 年 12 月 10 日到 11 日在上海玩两天，两个人，每段步行不超过 1 公里");
if (!first.id || !second.id || first.id === second.id) {
  note(`ABORT ids unusable first=${!!first.id} second=${!!second.id} same=${first.id === second.id}`);
  process.exit(3);
}
note(`C_TWO_SESSIONS different_owner=${first.owner !== second.owner} own_id_shape=uuid other_id_shape=uuid t=${elapsed()}`);

const box = await chromium.launchPersistentContext(PROFILE, {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
const page = box.pages()[0] ?? await box.newPage();
async function readAt(label, id) {
  await page.goto("http://127.0.0.1:14464/journeys/" + id, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(6500);
  const seen = await page.evaluate(() => {
    const body = (document.body.innerText || "").replace(/\s+/g, " ");
    return { head: body.slice(0, 150), bouncedToCreate: /新建行程|三步完成/.test(body),
      refuses: /无权|没有登录|读不到|找不到|不可访问|不属于|无法打开/.test(body),
      articles: Array.from(document.querySelectorAll("article")).length,
      hasPlanWords: /出发|日程|活动|地图|计划|行程执行中/.test(body) };
  });
  const shape = seen.bouncedToCreate ? "REDIRECTED_TO_CREATE"
    : seen.refuses ? "REFUSED_IN_WORDS"
      : seen.articles > 0 && seen.hasPlanWords ? "READ_CONTENT" : "UNKNOWN";
  note(`${label} ${JSON.stringify(seen)} shape=${shape} t=${elapsed()}`);
  await page.screenshot({ path: `${DIR}/390-bs140-${label.toLowerCase().replace(/_/g, "-")}.png` }).catch(() => {});
  return shape;
}
const own = await readAt("A_OWN_JOURNEY", second.id);
const other = await readAt("B_OTHER_SESSION_JOURNEY", first.id);
let verdict;
if (own === "READ_CONTENT" && other !== "READ_CONTENT") verdict = "DISCRIMINATED_ownership_is_the_difference";
else if (own === "READ_CONTENT" && other === "READ_CONTENT") verdict = "BOTH_READ_a_stranger_can_open_the_other_journey";
else if (own !== "READ_CONTENT") verdict = "ROUTE_BOUNCES_EVERYONE_control_failed_" + own;
else verdict = "MIXED own=" + own + " other=" + other;
note(`PAIR own=${own} other=${other}`);
note(`VERDICT ${verdict} t=${elapsed()}`);
note("DONE t=" + elapsed());
await box.close();
