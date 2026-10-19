import { expect, test } from "@playwright/test";
import type { GuardianStream } from "../src/api/citynexus";

const journeyId = "00000000-0000-4000-8000-000000000951";
const ownerA = "GUARDIAN_FIXTURE_OWNER_A";
const ownerB = "GUARDIAN_FIXTURE_OWNER_B";
const bearerA = "GUARDIAN_TEST_FIXTURE_BEARER_A";
const bearerB = "GUARDIAN_TEST_FIXTURE_BEARER_B";

const emptyStream: GuardianStream = {
  tool: "read_guardian_stream",
  journey_id: journeyId,
  mission_id: null,
  status: "WATCH_NOT_RUNNING",
  watch: { configured: false, last_observed_at: null, latest_pulse: null },
  recovery_epoch: null,
  stream: [],
  counts: { events: 0, open_events: 0, impacts: 0, actions: 0 },
};

const observationId = "private-observation-id-fixture";
const eventStream: GuardianStream = {
  tool: "read_guardian_stream",
  journey_id: journeyId,
  mission_id: "private-mission-id-fixture",
  status: "HAS_EVENTS",
  watch: {
    configured: true,
    last_observed_at: "2026-10-19T01:10:00Z",
    latest_pulse: { id: "private-pulse-id-fixture", status: "COMPLETED", started_at: "2026-10-19T01:09:00Z", completed_at: "2026-10-19T01:10:00Z" },
  },
  recovery_epoch: {
    id: "private-epoch-id-fixture",
    generation: 2,
    status: "OPEN",
    triggering_event_ids: [observationId],
    opened_at: "2026-10-19T01:10:00Z",
    active_plan_version_id_at_open: "private-plan-version-id-fixture",
  },
  stream: [{
    observation: {
      id: observationId,
      event_type: "WEATHER",
      severity: "MINOR",
      status: "DETECTED",
      provider: "system",
      provenance: "SYSTEM_DERIVED",
      detected_at: "2026-10-19T01:08:00Z",
      affected_activity_id: null,
    },
    impact: {
      id: "private-impact-id-fixture",
      status: "UNCERTAIN",
      uncertain: true,
      reason_codes: ["WEATHER", "PRIVATE_REASON_CANARY"],
      created_at: "2026-10-19T01:09:00Z",
    },
    proposed_action: {
      id: "private-action-id-fixture",
      decision: "RECOVERY_REQUIRED",
      status: "OPEN",
      action_status: "PROPOSAL_PRESENTED",
      proposal_id: "private-proposal-id-fixture",
      created_at: "2026-10-19T01:10:00Z",
      completed_at: null,
    },
  }],
  counts: { events: 1, open_events: 1, impacts: 1, actions: 1 },
};

test("TEST_FIXTURE Guardian panel reads on open, shows linked progress, and clears on identity change", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => {
    const detail = error.stack ?? error.message;
    pageErrors.push(detail);
    test.info().annotations.push({ type: "pageerror", description: detail });
  });
  await page.addInitScript(({ journeyId, owner, bearer }) => {
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
    sessionStorage.setItem("citynexus.traveler.session-id", owner);
    localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id: journeyId, ownerTravelerId: owner, cityCode: "TEST_FIXTURE", cityName: "TEST_FIXTURE 行程", status: "DRAFT",
    }));
  }, { journeyId, owner: ownerA, bearer: bearerA });

  let guardianCalls = 0;
  let releaseBearerB: (() => void) | null = null;
  let bearerBRequestStarted = false;

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const reply = (value: unknown, status = 200) => route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(value),
    });

    if (path.startsWith(`/api/v1/journeys/${journeyId}`)) {
      expect([`Bearer ${bearerA}`, `Bearer ${bearerB}`]).toContain(request.headers().authorization);
    }
    if (path === "/api/v1/agent/runtime-status") {
      return reply({ runtime_identity: "HERMES_COMPAT_ENDPOINT", hermes_compat_configured: false, ai_state: "DISABLED" });
    }
    if (path === "/api/v1/travelers/session") {
      const token = request.headers().authorization;
      return reply({ traveler_id: token === `Bearer ${bearerB}` ? ownerB : ownerA });
    }
    if (path === `/api/v1/journeys/${journeyId}/guardian/stream`) {
      guardianCalls += 1;
      const authorization = request.headers().authorization;
      if (authorization === `Bearer ${bearerB}`) {
        bearerBRequestStarted = true;
        await new Promise<void>((resolve) => { releaseBearerB = resolve; });
        return reply(emptyStream);
      }
      return reply(guardianCalls === 1 ? emptyStream : eventStream);
    }
    if (path === `/api/v1/journeys/${journeyId}`) return reply({ id: journeyId, title: "TEST_FIXTURE", status: "DRAFT", timezone: "Asia/Shanghai" });
    if (path === `/api/v1/journeys/${journeyId}/plans`) return reply([]);
    if (path === `/api/v1/journeys/${journeyId}/map-places`) return reply({ journey_id: journeyId, candidates: [] });
    if (path === `/api/v1/journeys/${journeyId}/planning-intent`) return reply({
      journey_id: journeyId,
      intent: null,
      trip: { dates: ["2026-10-19", "2026-10-20"], party_size: 2, budget: { amount_minor: 100000, currency: "CNY" } },
      candidates: [],
    });
    if (path === `/api/v1/journeys/${journeyId}/bootstrap-shortlist`) return reply({ journey_id: journeyId, pocket_walk: null });
    if (path === `/api/v1/journeys/${journeyId}/bootstrap-discovery/current`) return reply({ journey_id: journeyId, receipt_id: null, candidates: [] });
    return reply({});
  });

  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  await page.getByTestId("rev-mission-layer-agent").click();
  const cockpit = page.getByTestId("rev-mission-cockpit");
  await expect(cockpit).toBeVisible();
  expect(pageErrors, pageErrors.join("\n")).toEqual([]);
  await cockpit.getByTestId("rev-mission-layer-timeline").click();
  const toggle = cockpit.getByRole("button", { name: "行程守护", exact: true });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(cockpit.getByTestId("rev-guardian-reality-panel")).toHaveCount(0);
  expect(guardianCalls).toBe(0);

  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  let panel = cockpit.getByTestId("rev-guardian-reality-panel");
  await expect(panel).toContainText("行程守护还没有检查记录");
  expect(guardianCalls).toBe(1);

  await toggle.click();
  await expect(panel).toHaveCount(0);
  expect(guardianCalls).toBe(1);
  await toggle.click();
  await expect(panel).toContainText("天气情况发生变化");
  await expect(panel).toContainText("影响待核实");
  await expect(panel).toContainText("需要调整行程");
  await expect(panel).toContainText("调整方案已生成，等待查看");
  await expect(panel).toContainText("当前恢复第 2 轮");
  await expect(panel).toContainText("触发记录");
  await expect(panel).toContainText("守护规则已设置");
  await expect(panel).not.toContainText("正在检查");
  await expect(panel).not.toContainText("PRIVATE_REASON_CANARY");
  for (const privateValue of [observationId, "private-mission-id-fixture", "private-impact-id-fixture", "private-action-id-fixture", "private-proposal-id-fixture"]) {
    await expect(panel).not.toContainText(privateValue);
  }
  expect(guardianCalls).toBe(2);

  await page.evaluate(({ owner, bearer }) => {
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
    sessionStorage.setItem("citynexus.traveler.session-id", owner);
    const selected = localStorage.getItem("citynexus.revolution.firstlook.journey");
    if (selected) {
      const journey = JSON.parse(selected);
      localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({ ...journey, ownerTravelerId: owner }));
    }
    window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
  }, { owner: ownerB, bearer: bearerB });
  await expect.poll(() => bearerBRequestStarted).toBe(true);
  await expect(panel).toContainText("正在读取守护记录…");
  await expect(panel).not.toContainText("天气情况发生变化");
  releaseBearerB?.();
  await expect(panel).toContainText("行程守护还没有检查记录");
  await expect(panel).not.toContainText("天气情况发生变化");
  expect(guardianCalls).toBe(3);
});
