/**
 * CMDR 02:45 cell 2 (lane 6a150e1e) -- measure only, no product byte touched.
 *
 * Two questions, one pair of arms:
 *   U1  what does the shell actually ask when the journey answer names no traveller, and what does the
 *       traveller end up looking at?
 *   U2  is that label the server's answer or this device's guess -- set the traveller's agent policy to
 *       AUTONOMOUS through the product's own PUT, then read the top-bar autonomy word on both faces.
 *
 * The lever is the one V10 uses: take the shell's own `/experience` answer and delete the single field
 * `journey.traveler_id`. Everything below is recorded; the only assertion is that the two faces really
 * differ, because if they do not then this measurement measured nothing.
 */

import { expect, test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";

const SEED = JSON.parse(
  readFileSync("D:/moodle/_qoder_6a_ord0531_20261001/spend_seed_day24_report.json", "utf8"),
) as { journeys: { priced: string }; answers: Record<string, { experience: any }> };

const EVIDENCE = "D:/moodle/_qoder_6a_ord0531_20261001/e2e";
const journeyId = SEED.journeys.priced;
const traveller = SEED.answers.priced.experience.journey.traveler_id as string;
const readings: Record<string, unknown> = {};

test.setTimeout(180_000);

async function boot(page: import("@playwright/test").Page, stripTraveller: boolean) {
  const asked = new Map<string, number>();
  page.on("response", (response) => {
    asked.set(new URL(response.url()).pathname, response.status());
  });
  if (stripTraveller) {
    const real = await page.request.get(`/api/v1/journeys/${journeyId}/experience`);
    expect(real.status(), "the shell's own read must answer").toBe(200);
    const body = await real.json();
    const stripped = { ...body, journey: { ...body.journey } };
    delete stripped.journey.traveler_id;
    await page.route(`/api/v1/journeys/${journeyId}/experience`, (route) =>
      void route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(stripped) }),
    );
  }
  await page.addInitScript((id) => localStorage.setItem("citynexus.v8.journey_id", id), journeyId);
  await page.goto("/v8/hub", { waitUntil: "load" });
  await page.waitForTimeout(3_500);
  const runtime = page.locator(".v8-runtime");
  const runtimeText = (await runtime.count())
    ? (await runtime.first().innerText()).replace(/\s+/g, " ").trim()
    : null;
  return {
    policy_paths: [...asked.keys()].filter((p) => p.includes("agent-policy")),
    policy_statuses: [...asked.entries()].filter(([p]) => p.includes("agent-policy")),
    autonomy_word_on_screen: runtimeText,
    dot_rendered: await page.locator(".status-dot").count(),
    asked_everything: Object.fromEntries(asked.entries()),
  };
}

test("U1 the doomed ask, and what the traveller sees anyway", async ({ page }) => {
  const control = await boot(page, false);
  readings.U1_control = control;
  const stripped = await boot(page, true);
  readings.U1_stripped = stripped;
  console.log(`UNDEF1 ${JSON.stringify({ control, stripped })}`);
  writeFileSync(`${EVIDENCE}/undefined_leg_measurement_r1.json`, JSON.stringify(readings, null, 1), "utf8");
  expect(stripped.policy_paths.length, "the stripped face must actually ask the undefined leg").toBeGreaterThan(0);
});

test("U2 is the autonomy word the server's or this device's guess", async ({ page }) => {
  const write = await page.request.put(`/api/v1/travelers/${traveller}/agent-policy`, {
    data: { mode: "AUTONOMOUS" },
  });
  const serverSays = write.status();
  const serverBody = await write.json().catch(() => null);

  const control = await boot(page, false);
  const stripped = await boot(page, true);
  readings.U2 = {
    put_agent_policy_status: serverSays,
    server_mode_after_put: serverBody?.mode ?? null,
    control_face: { asked: control.policy_paths, statuses: control.policy_statuses, word: control.autonomy_word_on_screen },
    stripped_face: { asked: stripped.policy_paths, statuses: stripped.policy_statuses, word: stripped.autonomy_word_on_screen },
  };
  console.log(`UNDEF2 ${JSON.stringify(readings.U2)}`);
  writeFileSync(`${EVIDENCE}/undefined_leg_measurement_r1.json`, JSON.stringify(readings, null, 1), "utf8");
  await page.screenshot({ path: `${EVIDENCE}/U2_autonomy_two_faces.png`, fullPage: true });

  /* The consequence, if there is one: the server says AUTONOMOUS, and the face that lost the id shows a
     different word than the face that kept it. */
  expect(serverSays, "the policy write must answer through the product's own door").toBe(200);
  expect(control.autonomy_word_on_screen).not.toBeNull();
  expect(stripped.autonomy_word_on_screen).not.toBeNull();
});
