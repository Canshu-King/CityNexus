import { expect, test } from "@playwright/test";

for (const width of [390, 430, 1566]) test(`TEST_FIXTURE non-Liancheng source media, fallback and day/map focus at ${width}`, async ({ page }, testInfo) => {
  await page.setViewportSize({ width, height: 932 });
  const jid = "00000000-0000-4000-8000-000000000971";
  const tid = "00000000-0000-4000-8000-000000000972";
  const owner = "SOURCE_MEDIA_TEST_OWNER";
  await page.addInitScript(({ jid, tid, owner }) => {
    sessionStorage.setItem("citynexus.traveler.bearer", "SOURCE_MEDIA_TEST_TOKEN");
    sessionStorage.setItem("citynexus.traveler.session-id", owner);
    localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id: jid, ownerTravelerId: owner, cityCode: "CN-TEST", cityName: "上海市", status: "DRAFT",
    }));
    localStorage.setItem(`citynexus.revolution.goal-task.${owner}.${jid}`, tid);
  }, { jid, tid, owner });
  const points = [1, 2, 3, 4].map(index => ({
    id: `photon:W/${12340 + index}`, name: `TEST_FIXTURE 上海地点${index}`, category: "museum", provider: "photon",
    provider_provenance: "LIVE_PROVIDER", coordinate_system: "WGS84", region_status: "MATCHED",
    latitude: 31.2 + index * .01, longitude: 121.4 + index * .01,
    source_url: `https://www.openstreetmap.org/way/${12340 + index}`,
  }));
  const root = `/api/v1/journeys/${jid}`;
  const reads: string[] = []; const writes: string[] = [];
  await page.route("https://upload.wikimedia.org/**", route => route.fulfill({
    status: 200, contentType: "image/png",
    body: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1kAAAAASUVORK5CYII=", "base64"),
  }));
  await page.route("**/api/v1/**", async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    const reply = (body: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    if (req.method() !== "GET") writes.push(path);
    if (path.startsWith(root)) expect(req.headers().authorization).toBe("Bearer SOURCE_MEDIA_TEST_TOKEN");
    if (path === "/api/v1/travelers/session") return reply({ traveler_id: owner });
    if (path === "/api/v1/agent/runtime-status") return reply({ ai_state: "CONFIGURED_UNVERIFIED", hermes_compat_configured: true });
    if (path === root) return reply({ id: jid, status: "DRAFT", timezone: "Asia/Shanghai" });
    if (path === root + "/plans") return reply([]);
    if (path === root + "/map-places") return reply({ journey_id: jid, candidates: points.map(p => ({ ...p,
      candidate_id: p.id, selection_state: "OPENING_UNVERIFIED", observation_expired: false })) });
    if (path === root + "/planning-intent") return reply({ journey_id: jid, intent: null, candidates: [],
      trip: { dates: ["2026-10-21"], party_size: 1, budget: { amount_minor: 50000, currency: "CNY" } } });
    if (path === `${root}/agent/goal-tasks/${tid}`) return reply({
      task_id: tid, journey_id: jid, status: "PARTIAL_READY", goal: "TEST_FIXTURE 上海一天", mode: "GOAL_PLANNING",
      consent: { model: true, online_research: true }, budget: { max_model_turns: 8, max_tool_calls: 16 },
      usage: { model_turns: 2, tool_calls: 1 }, research_places: points, tool_steps: [],
      draft_artifact: { revision: 1, status: "DRAFT", days: [{ date: "2026-10-21", slots: [
        { title: points[0].name, place_id: points[0].id, time_of_day: "morning", notes: "营业待查" },
      ] }] },
    });
    if (path === `${root}/agent/goal-tasks/${tid}/events`) return reply({ task_id: tid, events: [], next_cursor: null });
    if (path === `${root}/agent/goal-tasks/${tid}/place-media`) {
      const id = url.searchParams.get("candidate_id")!; reads.push(id);
      return reply({ candidate_id: id, place_id: id, journey_id: jid, task_id: tid,
        status: id === points[0].id ? "REAL_POI_PHOTO" : "NO_IMAGE",
        media: id !== points[0].id ? null : { place_id: id, can_show: true,
          image_url: "https://upload.wikimedia.org/TEST_FIXTURE-photo.png", thumb_url: null,
          author: "TEST_FIXTURE 作者", license: "CC BY-SA 4.0", identity_status: "BOUND_SOURCE_ENTITY_ID",
          source_url: "https://commons.wikimedia.org/wiki/File:TEST_FIXTURE.jpg",
          terms_url: "https://creativecommons.org/licenses/by-sa/4.0/", captured_at: "2026-10-19T00:00:00Z" } });
    }
    return reply({});
  });
  await page.goto("/revolution");
  const cockpit = page.getByTestId("rev-mission-cockpit");
  await expect.poll(() => reads.length).toBe(3);
  const card = cockpit.locator(`.cn-place-photo[data-place-id="${points[0].id}"]`);
  await expect(card).toHaveAttribute("data-photo-origin", "runtime");
  await expect(card).toContainText("TEST_FIXTURE 作者");
  await expect(card).toContainText("CC BY-SA 4.0");
  await expect(cockpit.locator('.cn-mission-media img')).toHaveAttribute('alt', points[0].name + '实景');
  await cockpit.getByRole("button", { name: /查看更多地点/ }).click();
  await expect(cockpit.locator('.cn-place-photo[data-photo-origin="none"]')).toHaveCount(3);
  await card.getByRole("button", { name: "查看对应安排" }).click();
  await expect(cockpit.locator(`.rev-goal-draft-slot[data-place-id="${points[0].id}"]`)).toHaveAttribute("open", "");
  const dayPhoto = cockpit.locator(`.rev-draft-day-photos figure[data-place-id="${points[0].id}"]`);
  await expect(dayPhoto).toBeVisible();
  await dayPhoto.getByRole("button").click();
  await expect(page.getByTestId("rev-mission-map-pane")).toBeVisible();
  if (width < 1000) {
    for (let i = 0; i < 3; i++) {
      await page.getByTestId("rev-mission-layer-agent").click();
      await page.getByTestId("rev-mission-layer-map").click();
    }
  }
  expect(reads).toHaveLength(3);
  const invitation = cockpit.locator(`.cn-place-photo[data-place-id="${points[3].id}"]`).getByRole("button", { name: "先看看这个地点" });
  await invitation.evaluate((button) => button.scrollIntoView({ block: "center", inline: "center" }));
  await page.evaluate(() => new Promise<void>((done) => requestAnimationFrame(() => requestAnimationFrame(() => done()))));
  const invitationBox = await invitation.boundingBox();
  expect(invitationBox?.height ?? 0).toBeGreaterThanOrEqual(44);
  const invitationHit = await invitation.evaluate((button) => {
    const box = button.getBoundingClientRect();
    return document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2) === button;
  });
  expect(invitationHit).toBe(true);
  await page.screenshot({ path: testInfo.outputPath(`media-invitation-${width}.png`) });
  await page.mouse.click(invitationBox!.x + invitationBox!.width / 2, invitationBox!.y + invitationBox!.height / 2);
  await expect.poll(() => reads.length).toBe(4);
  expect(writes).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
});
