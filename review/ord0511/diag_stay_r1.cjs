/** ORD-0511 diagnostic: what the screen actually asks for after one press on the generate button. */
const { chromium } = require("@playwright/test");

const FRONT = "http://127.0.0.1:4798";
const API = "http://127.0.0.1:8018/api/v1";

async function post(path, body) {
  const response = await fetch(FRONT + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return response.json();
}

(async () => {
  const traveler = await post("/api/v1/travelers", {
    display_name: "ORD-0511 diag",
    locale: "zh-CN",
    timezone: "Asia/Shanghai",
  });
  const journey = await post("/api/v1/journeys", {
    traveler_id: traveler.id,
    title: `CNX-ORD0511 diag ${Date.now()}`,
    city_code: "CN-TIANJIN",
    timezone: "Asia/Shanghai",
    start_at: "2026-12-04T15:00:00+08:00",
    end_at: "2026-12-06T21:00:00+08:00",
    budget: { amount_minor: 200000, currency: "CNY" },
    planning_mode: "balanced",
  });
  console.log("journey", journey.id ? "created" : journey);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, locale: "zh-CN" });
  const seen = [];
  page.on("requestfinished", async (request) => {
    const url = request.url();
    if (!url.includes("/api/v1/")) return;
    let size = null;
    try {
      const response = await request.response();
      const text = await response.text();
      size = text.length;
      if (url.includes("stay-options") || url.includes("experience")) {
        let options = null;
        try {
          options = (JSON.parse(text).options || []).length;
        } catch {}
        seen.push(`${request.method()} ${url.split("/api/v1")[1]} status=${response.status()} bytes=${size} options=${options}`);
      }
    } catch {}
  });

  await page.addInitScript((id) => localStorage.setItem("citynexus.v8.journey_id", id), journey.id);
  await page.goto(`${FRONT}/v8/stay`, { waitUntil: "load" });
  await page.getByTestId("v8-stay-explorer").waitFor({ timeout: 30_000 });
  console.log("cards before", await page.getByTestId("stay-offer-card").count());
  await page.getByTestId("stay-generate").click();
  await page.getByTestId("stay-generation-outcome").waitFor({ timeout: 180_000 });
  console.log("outcome:", (await page.getByTestId("stay-generation-outcome").innerText()).trim());
  await page.waitForTimeout(12_000);
  console.log("cards after", await page.getByTestId("stay-offer-card").count());
  console.log("section text head:", (await page.getByTestId("v8-stay-explorer").innerText()).replace(/\s+/g, " ").slice(0, 220));
  console.log("--- api calls this page made ---");
  seen.forEach((line) => console.log("   ", line));
  await browser.close();
})();
