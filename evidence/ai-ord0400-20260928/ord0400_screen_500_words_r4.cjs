// ORD-0400 follow-up capture: what does the screen SAY about a 500 that this server never sent?
//
// Static-only, read-only, no product bytes touched. The app is pointed at my own private static
// preview (no backend at all), primed with a journey id no server owns, so the read path lands on
// the failure sentence. What is captured is the rendered text plus the attribution the client made.
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = "http://localhost:4833/";
const OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_screen_500_words_r4.json";

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  const rep = { base: BASE, api_responses: [] };

  page.on("response", (r) => {
    if (r.url().includes("/api/v1/")) {
      rep.api_responses.push({
        url: r.url().replace("http://localhost:4833", ""),
        status: r.status(),
        content_type: r.headers()["content-type"] ?? null,
        server_header: r.headers()["server"] ?? null,
      });
    }
  });

  await page.goto(BASE, { waitUntil: "domcontentloaded", timeout: 45000 }).catch((e) => {
    rep.goto_error = String(e).slice(0, 140);
  });
  await page.evaluate(() => localStorage.setItem("citynexus.v8.journey_id", "ord0400-probe-no-such-journey"));
  await page.reload({ waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1500);

  rep.title = await page.title();
  rep.body_text = (await page.locator("body").innerText().catch(() => "")).slice(0, 600);
  rep.has_http_status_word = rep.body_text.includes("http_status=");
  rep.status_value_on_screen = (rep.body_text.match(/http_status=(\d+)/) || [null, null])[1];
  rep.blames_server_words = rep.body_text.includes("服务器刚才答了你") || rep.body_text.includes("它自己报错了");
  rep.says_network_words = rep.body_text.includes("网络不可用") || rep.body_text.includes("网络问题");
  await page.screenshot({ path: "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_screen_500_words_r4.png" }).catch(() => {});

  fs.writeFileSync(OUT, JSON.stringify(rep, null, 1), "utf8");
  console.log("api_responses", JSON.stringify(rep.api_responses).slice(0, 320));
  console.log("status_value_on_screen", rep.status_value_on_screen, "blames_server", rep.blames_server_words, "network_words", rep.says_network_words);
  console.log("body_text:", JSON.stringify(rep.body_text).slice(0, 420));
  console.log("RECEIPT=" + OUT);
  await browser.close();
})();
