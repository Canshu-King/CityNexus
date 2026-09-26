/* Commander's own walk of ORD-0351 on the deployed phone chain: does a pasted link really open THAT trip?

Why: ORD-0351 is landed and its gate is green on a lane's tree, but the promise is a traveller's promise --
"open the link you sent me".  So I open it the way a traveller does: the authenticated proxy surface
(`:4782`, the same one the phone reaches through the tunnel), at phone size, twice:
  A) a journey id the chain's own backend just handed me (`GET /api/v1/demo/scene` -> journey_id);
  B) a well-formed UUID that no journey owns -- this must be named as "that trip is not there", and must NOT
     be laundered into "network unavailable" (the ORD-0263 family) nor into a different trip's data.
What counts as evidence here is not "the page rendered" but: which request the page made, whether that
request carries the id from the address bar, and what the screen says in words.

Credentials are read from the proxy's auth file at run time and never printed.

usage: node cmdr_journey_link_walk_r1.js --base http://127.0.0.1:4782 \
       --auth-file D:/moodle/_qoder_preview_20260920/run/preview_auth.txt --out file.json
*/
const path = require("path");
const fs = require("fs");
const NM = "D:/moodle/CityNexus/frontend/node_modules";
const { chromium, devices } = require(path.join(NM, "playwright"));

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : d; };
const BASE = arg("--base", "http://127.0.0.1:4782");
const AUTH_FILE = arg("--auth-file", "D:/moodle/_qoder_preview_20260920/run/preview_auth.txt");
const OUT = arg("--out", "patrol/journey_link_walk.json");

function creds() {
  const raw = fs.readFileSync(AUTH_FILE, "utf8").trim().split("\t");
  if (raw.length < 2) throw new Error("AUTH_FILE_SHAPE_UNEXPECTED names=" + raw.length);
  return { username: raw[0], password: raw[1] };
}
async function fetchJson(page, url) {
  return page.evaluate(async (u) => {
    const r = await fetch(u, { credentials: "include" });
    const t = await r.text();
    let id = null; try { id = JSON.parse(t).journey_id ?? null; } catch (e) {}
    return { status: r.status, ctype: r.headers.get("content-type"), bytes: t.length, journey_id: id };
  }, url);
}
const clean = s => (s || "").replace(/\s+/g, " ").trim();

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices["Pixel 5"], locale: "zh-CN", httpCredentials: creds() });
  const page = await ctx.newPage();
  const seen = [];
  page.on("request", r => { if (/journey|trips|\/journeys/.test(r.url()) && r.url().includes("/api/")) seen.push(r.url()); });
  const out = { base: BASE, at: new Date().toString() };

  // The chain's own backend names the live journey id -- the id is read from the product, not typed by me.
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 60000 });
  out.scene = await fetchJson(page, BASE + "/api/v1/demo/scene").catch(e => ({ error: String(e).slice(0, 120) }));
  const realId = out.scene && out.scene.journey_id;

  async function walk(label, id) {
    const reqs = [];
    const onReq = r => { if (r.url().includes(id)) reqs.push(r.url().replace(BASE, "")); };
    page.on("request", onReq);
    let t = null;
    try {
      await page.goto(`${BASE}/v8/${id}`, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForTimeout(4000);
      t = { label, id, url_shown: page.url().replace(BASE, ""),
            requests_carrying_this_id: Array.from(new Set(reqs)).slice(0, 6),
            requests_carrying_it_count: new Set(reqs).size,
            screen_head: clean(await page.locator("body").innerText().catch(() => "")).slice(0, 420),
            asset_served: await page.evaluate(() => Array.from(document.querySelectorAll("script[src]"))
              .map(x => x.getAttribute("src")).filter(u => /\/assets\/index-.*\.js/.test(u))) };
    } catch (e) { t = { label, id, error: String(e).slice(0, 160), requests_carrying_this_id: reqs }; }
    page.off("request", onReq);
    return t;
  }

  if (realId) out.A_real_link = await walk("real journey from the chain's own scene read", realId);
  // A syntactically valid UUID the product has never seen.  Same path shape, different truth.
  out.B_unknown_link = await walk("well-formed but unknown journey id", "00000000-0000-4000-8000-000000000000");

  const a = out.A_real_link || {}, b = out.B_unknown_link || {};
  const aAsked = (a.requests_carrying_it_count || 0) > 0;
  const bSaysMissing = /找不到|不存在|没有|无法打开|not found|missing/i.test(b.screen_head || "");
  // My first version matched the bare word "network" and so reported a FALSE POSITIVE on the good screen:
  // the honest copy says "这不是网络问题：服务器刚才答得出来" -- denying the network reading, not claiming it.
  // The predicate has to be the claim, not the topic: look for an availability assertion, and separately
  // record whether the screen explicitly disclaims the network, because that disclaimer is what we want.
  const bSaysNetwork = /网络不可用|无法连接|连接失败|请检查网络|network (?:error|unavailable|failure)/i
    .test(b.screen_head || "");
  const bDisclaimsNetwork = /这不是网络问题/i.test(b.screen_head || "");
  out.verdict = {
    A_the_address_bar_id_was_actually_asked: aAsked,
    B_unknown_id_named_as_missing_on_screen: bSaysMissing,
    B_not_laundered_as_network_failure: !bSaysNetwork,
    B_explicitly_disclaims_the_network_reading: bDisclaimsNetwork,
    same_asset_served_on_both: JSON.stringify(a.asset_served) === JSON.stringify(b.asset_served),
  };
  out.note = "requests_carrying_this_id counts API requests whose URL contains the id from the address bar; " +
             "a green A with zero such requests would mean the link is still decorative, so the count is the load-bearing number.";
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ scene_status: out.scene && out.scene.status, real_id_seen: !!realId,
                               A_asked: aAsked, A_count: a.requests_carrying_it_count,
                               B_missing_named: bSaysMissing, B_network_washed: bSaysNetwork,
                               asset_served: a.asset_served }, null, 1));
  console.log("A screen: " + (a.screen_head || "").slice(0, 260));
  console.log("B screen: " + (b.screen_head || "").slice(0, 260));
  console.log("out = " + OUT);
  await browser.close();
})();
