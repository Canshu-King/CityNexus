import { expect, test, type Route } from "@playwright/test";
import { CLIENT_WRITE_DEADLINE_MS, CLIENT_WRITE_DEADLINE_SECONDS } from "../src/lib/writeDeadline";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, serviceWorkers: "block" });

const travelerId = "00000000-0000-4000-8000-000000000239";
const journeyId = "00000000-0000-4000-8000-000000000241";
const existingBearer = "TEST_FIXTURE_SIGNED_BEARER";

function deferred() {
  let release!: () => void;
  const promise = new Promise<void>((resolve) => { release = resolve; });
  return { promise, release };
}

async function json(route: Route, value: object, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(value) });
}

async function runtimeStatus(route: Route) {
  await json(route, {
    runtime_identity: "HERMES_COMPAT_ENDPOINT",
    hermes_compat_configured: true,
    ai_state: "CONFIGURED_UNVERIFIED",
  });
}

test("TEST_FIXTURE keeps a timed-out POST /travelers unknown and allows only a manual receipt check", async ({ page }) => {
  await page.clock.install({ time: new Date("2026-10-18T00:00:00Z") });
  const travelerGate = deferred();
  const travelerRequestSeen = deferred();
  let travelerCalls = 0;
  let receiptCalls = 0;
  let postedReceiptKey: string | undefined;

  await page.addInitScript(() => {
    window.localStorage.setItem("citynexus.locale", "zh-CN");
  });

  await page.context().route("**/api/v1/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (request.method() === "GET" && pathname === "/api/v1/agent/runtime-status") {
      await runtimeStatus(route);
      return;
    }
    if (request.method() === "POST" && pathname === "/api/v1/travelers") {
      travelerCalls += 1;
      postedReceiptKey = request.headers()["idempotency-key"];
      expect(request.headers()["authorization"]).toBeUndefined();
      travelerRequestSeen.release();
      await travelerGate.promise;
      try {
        await json(route, {
          id: travelerId,
          access_token: "TEST_FIXTURE_NEW_BEARER",
        }, 201);
      } catch {
        // The fixture keeps the origin unanswered until the browser deadline fires.
      }
      return;
    }
    if (request.method() === "GET" && pathname === "/api/v1/start-write-receipts/traveler") {
      receiptCalls += 1;
      expect(request.headers()["x-citynexus-write-receipt-key"]).toBe(postedReceiptKey);
      await json(route, { operation: "traveler", state: "committed" });
      return;
    }
    await route.abort();
  });

  await page.goto("/revolution");
  await page.getByTestId("rev-firstlook-city").fill("厦门");
  await page.getByTestId("rev-firstlook-start").click();
  await travelerRequestSeen.promise;

  try {
    expect(travelerCalls).toBe(1);
    await page.clock.fastForward(CLIENT_WRITE_DEADLINE_MS);
    await expect(page.getByTestId("rev-start-write-status")).toContainText(
      `登录会话等待 ${CLIENT_WRITE_DEADLINE_SECONDS} 秒后停止，服务器结果未知`,
    );
    await expect(page.getByTestId("rev-firstlook-start")).toBeDisabled();
    expect(receiptCalls).toBe(0);

    await page.locator("form").evaluate((form) => (form as HTMLFormElement).requestSubmit());
    expect(travelerCalls).toBe(1);

    const state = await page.evaluate(() => ({
      input: (document.querySelector("#rev-firstlook-city") as HTMLInputElement | null)?.value,
      bearer: window.sessionStorage.getItem("citynexus.traveler.bearer"),
      marker: JSON.parse(window.localStorage.getItem("citynexus.revolution.firstlook.start-write") ?? "null"),
    }));
    expect(state.input).toBe("厦门");
    expect(state.bearer).toBeNull();
    expect(postedReceiptKey).toMatch(/^[0-9a-f]{64}$/);
    expect(state.marker).toMatchObject({
      phase: "traveler",
      state: "unknown",
      reason: "client-deadline",
      receiptKey: postedReceiptKey,
      cityName: "厦门",
    });

    await page.reload();
    await expect(page.getByTestId("rev-firstlook-city")).toHaveValue("厦门");
    await expect(page.getByTestId("rev-start-write-status")).toContainText("服务器结果未知");
    expect(travelerCalls).toBe(1);
    expect(receiptCalls).toBe(0);

    await page.getByTestId("rev-firstlook-query-write-receipt").click();
    await expect(page.getByTestId("rev-start-write-receipt-result")).toContainText(
      "服务器回执确认登录会话已创建",
    );
    await expect(page.getByTestId("rev-firstlook-start")).toBeDisabled();
    expect(receiptCalls).toBe(1);
    expect(travelerCalls).toBe(1);
  } finally {
    travelerGate.release();
  }
});

test("TEST_FIXTURE keeps a timed-out POST /journeys unknown and checks only signed recent drafts", async ({ page }) => {
  await page.clock.install({ time: new Date("2026-10-18T00:00:00Z") });
  const journeyGate = deferred();
  const journeyRequestSeen = deferred();
  let journeyCalls = 0;
  let draftReads = 0;
  let receiptKey: string | undefined;
  let postedCityCode: string | undefined;

  await page.addInitScript(({ bearer, identity }) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", bearer);
    window.sessionStorage.setItem("citynexus.traveler.session-id", identity);
    window.localStorage.setItem("citynexus.locale", "zh-CN");
  }, { bearer: existingBearer, identity: travelerId });

  await page.context().route("**/api/v1/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (request.method() === "GET" && pathname === "/api/v1/agent/runtime-status") {
      await runtimeStatus(route);
      return;
    }
    if (request.method() === "GET" && pathname === "/api/v1/travelers/session") {
      expect(request.headers()["authorization"]).toBe(`Bearer ${existingBearer}`);
      await json(route, { traveler_id: travelerId });
      return;
    }
    if (request.method() === "POST" && pathname === "/api/v1/journeys") {
      journeyCalls += 1;
      receiptKey = request.headers()["idempotency-key"];
      postedCityCode = (request.postDataJSON() as { city_code?: string }).city_code;
      expect(request.headers()["authorization"]).toBe(`Bearer ${existingBearer}`);
      journeyRequestSeen.release();
      await journeyGate.promise;
      try {
        await json(route, { id: journeyId }, 201);
      } catch {
        // The fixture keeps the origin unanswered until the browser deadline fires.
      }
      return;
    }
    if (request.method() === "GET" && pathname === "/api/v1/journeys/session/recent-drafts") {
      draftReads += 1;
      expect(request.headers()["authorization"]).toBe(`Bearer ${existingBearer}`);
      await json(route, [{
        id: journeyId,
        traveler_id: travelerId,
        title: "成都 · Revolution Explore",
        city_code: postedCityCode,
        status: "DRAFT",
      }]);
      return;
    }
    await route.abort();
  });

  await page.goto("/revolution");
  await page.getByTestId("rev-firstlook-city").fill("成都");
  await page.getByTestId("rev-firstlook-start").click();
  await journeyRequestSeen.promise;

  try {
    expect(journeyCalls).toBe(1);
    await page.clock.fastForward(CLIENT_WRITE_DEADLINE_MS);
    await expect(page.getByTestId("rev-start-write-status")).toContainText(
      `行程草稿等待 ${CLIENT_WRITE_DEADLINE_SECONDS} 秒后停止，服务器结果未知`,
    );
    await expect(page.getByTestId("rev-firstlook-start")).toBeDisabled();
    await page.locator("form").evaluate((form) => (form as HTMLFormElement).requestSubmit());
    expect(journeyCalls).toBe(1);

    const state = await page.evaluate(() => ({
      input: (document.querySelector("#rev-firstlook-city") as HTMLInputElement | null)?.value,
      bearer: window.sessionStorage.getItem("citynexus.traveler.bearer"),
      identity: window.sessionStorage.getItem("citynexus.traveler.session-id"),
      pointer: window.localStorage.getItem("citynexus.revolution.firstlook.journey"),
      marker: JSON.parse(window.localStorage.getItem("citynexus.revolution.firstlook.start-write") ?? "null"),
    }));
    expect(state.input).toBe("成都");
    expect(state.bearer).toBe(existingBearer);
    expect(state.identity).toBe(travelerId);
    expect(state.pointer).toBeNull();
    expect(state.marker).toMatchObject({ phase: "journey", state: "unknown", cityName: "成都" });
    expect(receiptKey).toMatch(/^[0-9a-f]{64}$/);
    expect(postedCityCode).toMatch(/^CN-RV-/);

    await page.reload();
    await expect(page.getByTestId("rev-firstlook-city")).toHaveValue("成都");
    await expect(page.getByTestId("rev-start-write-status")).toContainText("服务器结果未知");
    expect(journeyCalls).toBe(1);

    await page.getByTestId("rev-firstlook-check-start-draft").click();
    await expect(page.getByTestId("rev-start-write-draft-result")).toContainText(
      "已找到与本次地区对应的草稿",
    );
    await expect(page.getByTestId("rev-firstlook-start")).toBeDisabled();
    expect(journeyCalls).toBe(1);
    expect(draftReads).toBe(1);

    const afterCheck = await page.evaluate(() => ({
      bearer: window.sessionStorage.getItem("citynexus.traveler.bearer"),
      pointer: window.localStorage.getItem("citynexus.revolution.firstlook.journey"),
      marker: JSON.parse(window.localStorage.getItem("citynexus.revolution.firstlook.start-write") ?? "null"),
    }));
    expect(afterCheck.bearer).toBe(existingBearer);
    expect(afterCheck.pointer).toBeNull();
    expect(afterCheck.marker).toMatchObject({ phase: "journey", state: "unknown" });
  } finally {
    journeyGate.release();
  }
});
